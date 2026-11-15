import re, json, wave, subprocess, random, os
from vosk import Model, KaldiRecognizer, SetLogLevel
SetLogLevel(-1)
m = Model('vosk-model-small-uz-0.22')
aud = json.loads(re.search(r'window\.SOZ_AUDIO = (\{.*\});', open('audio.js').read(), re.S).group(1))['uz']
def norm(s): return re.sub(r'\s+', ' ', re.sub(r"[^a-z' \-]", ' ', re.sub(r'\(.*?\)', '', s.lower().replace('…','')).translate(str.maketrans({c:"'" for c in "ʻʼ’`‘"})))).strip()
def wav(f, frac=1.0):
    full = f'/tmp/{f}.wav'
    if not os.path.exists(full): subprocess.run(['ffmpeg','-loglevel','error','-y','-i','audio/'+f,'-ar','16000','-ac','1','-af','silenceremove=start_periods=1:start_threshold=-45dB:stop_periods=1:stop_threshold=-45dB:stop_duration=0.2',full], check=True)
    if frac == 1.0: return full
    out = f'/tmp/{f}.{frac}.wav'
    w = wave.open(full); d = w.readframes(w.getnframes()); p = w.getparams(); w.close()
    o = wave.open(out,'wb'); o.setparams(p); o.writeframes(d[:int(len(d)*frac)//2*2] + b'\x00\x00'*8000); o.close()
    return out
def run(path, grammar, partial_mode=False):
    r = KaldiRecognizer(m, 16000, json.dumps(grammar)); r.SetWords(True)
    wf = wave.open(path,'rb'); seen = set()
    while True:
        d = wf.readframes(2000)
        if not d: break
        if not r.AcceptWaveform(d): seen.add(json.loads(r.PartialResult()).get('partial',''))
    res = json.loads(r.FinalResult())
    return res.get('text',''), [w.get('conf',0) for w in res.get('result',[])], seen
words = list(aud); deck = sorted({norm(w) for w in words if norm(w)})
random.seed(2); sample = random.sample(words, 80)
def test(name, g, thr=0, use_partial=False):
    acc=trunc=other=tn=0
    for w in sample:
        e = norm(w)
        def ok(path):
            t,c,seen = run(path, g(e))
            return (e in seen) if use_partial else (t==e and min(c or [0])>=thr)
        acc += ok(wav(aud[w]))
        if len(e) >= 5: tn += 1; trunc += ok(wav(aud[w],0.6))
        other += ok(wav(aud[random.choice([x for x in words if x!=w])]))
    print(f'{name}: correct accepted {acc}/80 | first 60% only, wrongly accepted {trunc}/{tn} | other word wrongly accepted {other}/80', flush=True)

from difflib import SequenceMatcher
def runfree(path):
    r = KaldiRecognizer(m, 16000); wf = wave.open(path,'rb')
    while True:
        d = wf.readframes(2000)
        if not d: break
        r.AcceptWaveform(d)
    return json.loads(r.FinalResult()).get('text','')
def testfree(thr):
    acc=trunc=other=tn=0; misses=[]; fa=[]
    for w in sample:
        e = norm(w); sim = lambda t: SequenceMatcher(None, t, e).ratio()
        t = runfree(wav(aud[w])); a = sim(t) >= thr; acc += a
        if not a: misses.append((e,t))
        if len(e) >= 5:
            tn += 1; t = runfree(wav(aud[w],0.6)); b = sim(t) >= thr; trunc += b
            if b: fa.append((e,t))
        other += sim(runfree(wav(aud[random.choice([x for x in words if x!=w])]))) >= thr
    print(f'FREE similarity>={thr}: correct accepted {acc}/80 | first 60% only, wrongly accepted {trunc}/{tn} | other word wrongly accepted {other}/80', flush=True)
    if thr==1.0: print(' misses', misses[:12]); print(' truncated heard as', [(e, runfree(wav(aud[w],0.6))) for w in sample[:12] for e in [norm(w)]])

import asyncio, edge_tts
V='aeiou'
def mutate(e):
    w = e.split(' '); x = w[-1]
    for i in range(len(x)-1, 0, -1):          # change the last vowel of the last word
        if x[i] in V: x = x[:i] + ('a' if x[i]!='a' else 'o') + x[i+1:]; break
    else: x = x + 'a'
    w[-1] = x; return ' '.join(w)
bad = [(norm(w), mutate(norm(w))) for w in sample if len(norm(w)) >= 3]
async def synth():
    for e, b in bad:
        f = '/tmp/bad_' + re.sub(r'\W','_',b) + '.mp3'
        if not os.path.exists(f): await edge_tts.Communicate(b.replace("'", "ʻ"), 'uz-UZ-MadinaNeural', rate='-10%').save(f)
asyncio.run(synth())
def badwav(b):
    f = '/tmp/bad_' + re.sub(r'\W','_',b); subprocess.run(['ffmpeg','-loglevel','error','-y','-i',f+'.mp3','-ar','16000','-ac','1',f+'.wav'],check=True); return f+'.wav'
res = {k:0 for k in ['free exact','free sim>=0.9','one-word grammar final','one-word grammar partial (NOW)','deck grammar final']}
ex=[]
for e,b in bad:
    p = badwav(b); t = runfree(p)
    res['free exact'] += t==e; res['free sim>=0.9'] += SequenceMatcher(None,t,e).ratio()>=0.9
    t2,c,seen = run(p,[e,'[unk]']); res['one-word grammar final'] += t2==e; res['one-word grammar partial (NOW)'] += e in seen
    t3,c,_ = run(p, deck+['[unk]']); res['deck grammar final'] += t3==e
    ex.append((e,b,t))
print('WRONG ENDING wrongly accepted, out of', len(bad), res)
print('examples (word, said, heard free):', ex[:20])
