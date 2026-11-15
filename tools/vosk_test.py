import re, json, wave, subprocess, random, os, collections
from vosk import Model, KaldiRecognizer, SetLogLevel
SetLogLevel(-1)
m = Model('vosk-model-small-uz-0.22')
vocab = set(open('vosk-model-small-uz-0.22/graph/words.txt' if os.path.exists('vosk-model-small-uz-0.22/graph/words.txt') else os.devnull).read().split()[::2]) if False else None
aud = json.loads(re.search(r'window\.SOZ_AUDIO = (\{.*\});', open('audio.js').read(), re.S).group(1))['uz']
def norm(w): return re.sub(r"[^a-zʻ'’ \-]", '', w.lower().replace('’', "'").replace('ʻ', "'").replace('ʼ', "'").replace('…','')).strip()
def wav(f):
    out = '/tmp/' + f + '.wav'
    if not os.path.exists(out): subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', 'audio/' + f, '-ar', '16000', '-ac', '1', out], check=True)
    return out
def rec(path, grammar):
    r = KaldiRecognizer(m, 16000, json.dumps(grammar)); wf = wave.open(path, 'rb')
    while True:
        d = wf.readframes(4000)
        if not d: break
        r.AcceptWaveform(d)
    return json.loads(r.FinalResult()).get('text', '')
def free(path):
    r = KaldiRecognizer(m, 16000); wf = wave.open(path, 'rb')
    while True:
        d = wf.readframes(4000)
        if not d: break
        r.AcceptWaveform(d)
    return json.loads(r.FinalResult()).get('text', '')
random.seed(1); words = [w for w in aud]; sample = random.sample(words, 120)
ok = fa = 0; miss = []; falses = []
for w in sample:
    g = [norm(w), '[unk]']
    t = rec(wav(aud[w]), g)
    if t.strip() == norm(w): ok += 1
    else: miss.append((w, t))
    other = random.choice([x for x in words if x != w])
    t2 = rec(wav(aud[other]), g)
    if t2.strip() == norm(w): fa += 1; falses.append((w, other))
print(f'CORRECT accepted {ok}/120; WRONG word accepted {fa}/120')
print('missed:', miss[:40]); print('false accepts:', falses)
print('free recognition samples:', [(w, free(wav(aud[w]))) for w in sample[:15]])
