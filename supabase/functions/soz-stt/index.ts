// Speech check for Soz: a short clip (one spoken word, 16 kHz mono LINEAR16, base64) -> Google Speech-to-Text V2 (Chirp 3) -> text.
// The Google service-account key lives only here (secret GOOGLE_SA = the JSON key file). The app never sees it.
// Cost guard: only known app users, clips up to 6 s, at most DAY_CAP checks per user per day.
// Biasing: the app sends the card's word (hint) and the deck words that sound closest to it (deck). Google leans strongly to the card's word
// and lightly to those neighbours, so a near miss is heard as the word — and a wrong deck word still as itself.
// What was heard (text only, never audio) is kept 14 days in soz_stt_log, to tune the checking.
import { createClient } from "npm:@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type, apikey, authorization",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const json = (b: unknown, s = 200) => new Response(JSON.stringify(b), { status: s, headers: { ...CORS, "Content-Type": "application/json" } });
const CODE_RE = /^[A-Z0-9]{16}$/;
const LANGS: Record<string, string> = { uz: "uz-UZ", es: "es-ES", en: "en-US" };
const DAY_CAP = 1500;
const LOCATIONS = ["eu", "us"];                                    // Supabase runs in Frankfurt — Google in Europe answers faster; US as a fallback
const locBy: Record<string, number> = {};                          // per language: not every language is offered in every region
const BOOST_CARD = 15, BOOST_DECK = 4;

let token = "", tokenExp = 0;
const b64url = (b: ArrayBuffer | Uint8Array) => btoa(String.fromCharCode(...new Uint8Array(b))).replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_");
async function googleToken(sa: { client_email: string; private_key: string }) {
  if (token && Date.now() < tokenExp - 60_000) return token;
  const now = Math.floor(Date.now() / 1000);
  const enc = new TextEncoder();
  const head = b64url(enc.encode(JSON.stringify({ alg: "RS256", typ: "JWT" })));
  const claim = b64url(enc.encode(JSON.stringify({ iss: sa.client_email, scope: "https://www.googleapis.com/auth/cloud-platform", aud: "https://oauth2.googleapis.com/token", iat: now, exp: now + 3600 })));
  const pem = sa.private_key.replace(/-----[^-]+-----/g, "").replace(/\s+/g, "");
  const der = Uint8Array.from(atob(pem), (c) => c.charCodeAt(0));
  const key = await crypto.subtle.importKey("pkcs8", der, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", key, enc.encode(head + "." + claim));
  const r = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer", assertion: head + "." + claim + "." + b64url(sig) }),
  });
  const t = await r.json();
  if (!t.access_token) throw new Error("google_auth: " + JSON.stringify(t).slice(0, 200));
  token = t.access_token; tokenExp = Date.now() + (t.expires_in || 3600) * 1000;
  return token;
}
const clean = (a: unknown, max: number) => (Array.isArray(a) ? a : []).map((x) => String(x).replace(/[^\p{L}\p{N}' -]/gu, " ").replace(/\s+/g, " ").trim().slice(0, 60)).filter(Boolean).slice(0, max);

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  const t0 = Date.now();
  if (req.method !== "POST") return json({ error: "method" }, 405);
  const raw = Deno.env.get("GOOGLE_SA");
  if (!raw) return json({ error: "not_configured" }, 503);
  let body: { code?: string; lang?: string; audio?: string; hint?: unknown; deck?: unknown; nobias?: boolean };
  try { body = await req.json(); } catch { return json({ error: "bad_json" }, 400); }
  const code = String(body.code || ""), lang = LANGS[String(body.lang || "")], audio = String(body.audio || "");
  if (!CODE_RE.test(code) || !lang || !audio) return json({ error: "bad_request" }, 400);
  const sec = (audio.length * 3 / 4) / 32000;                         // 16 kHz * 2 bytes
  if (sec > 6) return json({ error: "too_long" }, 413);

  const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
  const guard = (async () => {
    const { data: user } = await db.from("soz_users").select("code").eq("code", code).maybeSingle();
    if (!user) return json({ error: "unknown_user" }, 403);
    const { data: n } = await db.rpc("soz_stt_bump", { p_code: code, p_sec: Math.round(sec * 10) / 10 });
    if (Number(n) > DAY_CAP) return json({ error: "day_limit" }, 429);
    return null;
  })();

  const hint = clean(body.hint, 8), seen = new Set(hint.map((x) => x.toLowerCase()));
  const deck = clean(body.deck, 200).filter((x) => !seen.has(x.toLowerCase()));
  const phrases = body.nobias ? [] : [...hint.map((value) => ({ value, boost: BOOST_CARD })), ...deck.map((value) => ({ value, boost: BOOST_DECK }))];

  const stop = await guard; if (stop) return stop;                  // unknown users never reach Google
  try {
    const sa = JSON.parse(raw);
    const t = await googleToken(sa);
    const url = (l: string) => `https://${l}-speech.googleapis.com/v2/projects/${sa.project_id}/locations/${l}/recognizers/_:recognize`;
    let loc = locBy[lang] || 0;
    const ask = (biased: boolean) => fetch(url(LOCATIONS[loc]), {
      method: "POST", headers: { Authorization: "Bearer " + t, "Content-Type": "application/json" },
      body: JSON.stringify({
        config: {
          model: "chirp_3", languageCodes: [lang], explicitDecodingConfig: { encoding: "LINEAR16", sampleRateHertz: 16000, audioChannelCount: 1 },
          ...(biased ? { adaptation: { phraseSets: [{ inlinePhraseSet: { phrases } }] } } : {}),
        },
        content: audio,
      }),
    });
    let biasErr = "", biased = phrases.length > 0, r = await ask(biased), g = await r.json();
    if (!r.ok && loc < LOCATIONS.length - 1) { loc++; r = await ask(biased); g = await r.json(); if (r.ok) locBy[lang] = loc; }   // model not offered in that region → next one
    if (!r.ok && biased) { biasErr = JSON.stringify(g).slice(0, 300); biased = false; r = await ask(false); g = await r.json(); }   // language without biasing → plain
    if (!r.ok) return json({ error: "google", detail: JSON.stringify(g).slice(0, 300) }, 502);
    const alts: string[] = [];
    for (const x of g.results || []) for (const a of x.alternatives || []) if (a.transcript && !alts.includes(a.transcript.trim())) alts.push(a.transcript.trim());
    const text = (g.results || []).map((x: any) => x.alternatives?.[0]?.transcript || "").join(" ").trim();
    const ms = Date.now() - t0;
    const log = (async () => {                                          // written after the answer is sent
      await db.from("soz_stt_log").insert({ code, lang: body.lang, expected: hint[0] || null, heard: text, alts, biased, region: LOCATIONS[loc], ms });
      if (Math.random() < 0.02) await db.from("soz_stt_log").delete().lt("at", new Date(Date.now() - 14 * 864e5).toISOString());
    })();
    // deno-lint-ignore no-explicit-any
    const rt = (globalThis as any).EdgeRuntime; if (rt?.waitUntil) rt.waitUntil(log); else await log;
    return json({ text, alts, biased, ...(biasErr ? { biasErr } : {}) });
  } catch (e) {
    return json({ error: "google", detail: String(e).slice(0, 300) }, 502);
  }
});
