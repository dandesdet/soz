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
test('NOW (one-word grammar, partial)', lambda e:[e,'[unk]'], use_partial=True)
test('one-word grammar, final', lambda e:[e,'[unk]'])
for thr in (0, 0.7, 0.85, 0.95): test(f'deck grammar, final, conf>={thr}', lambda e: deck+['[unk]'], thr)
