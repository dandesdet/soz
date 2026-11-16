import re, json, os, subprocess, random, asyncio
import numpy as np, librosa, edge_tts
from difflib import SequenceMatcher
from vosk import Model, KaldiRecognizer, SetLogLevel
SetLogLevel(-1); vm = Model('vosk-model-small-uz-0.22')
aud = json.loads(re.search(r'window\.SOZ_AUDIO = (\{.*\});', open('audio.js').read(), re.S).group(1))['uz']
def norm(s): return re.sub(r'\s+',' ',re.sub(r"[^a-z' \-]",' ',re.sub(r'\(.*?\)','',s.lower().replace('…','')).translate(str.maketrans({c:"'" for c in "ʻʼ’`‘"})))).strip()
def mutate(e):
    w=e.split(' '); x=w[-1]
    for i in range(len(x)-1,0,-1):
        if x[i] in 'aeiou': x=x[:i]+('a' if x[i]!='a' else 'o')+x[i+1:]; break
    else: x+='a'
    w[-1]=x; return ' '.join(w)
random.seed(3); words=[w for w in aud if len(norm(w))>=3]; sample=random.sample(words,70)
async def say(text, f):
    if not os.path.exists(f): await edge_tts.Communicate(text.replace("'","ʻ"),'uz-UZ-SardorNeural').save(f)
async def main():
    for w in sample:
        await say(norm(w), f'/tmp/s_ok_{hash(w)}.mp3'); await say(mutate(norm(w)), f'/tmp/s_bad_{hash(w)}.mp3')
asyncio.run(main())
def load(f):
    y,sr = librosa.load(f, sr=16000); y,_ = librosa.effects.trim(y, top_db=30); return y
def feat(y):
    m = librosa.feature.mfcc(y=y, sr=16000, n_mfcc=13)[1:]          # drop energy
    return (m - m.mean(1, keepdims=True)) / (m.std(1, keepdims=True)+1e-6)   # per-utterance normalisation (speaker/channel)
def dtw(a,b):
    D,wp = librosa.sequence.dtw(X=a, Y=b, metric='cosine'); return D[-1,-1]/len(wp)
def vosk(y):
    r=KaldiRecognizer(vm,16000); r.AcceptWaveform((np.clip(y,-1,1)*32767).astype(np.int16).tobytes()); return json.loads(r.FinalResult()).get('text','')
ok_d=[]; bad_d=[]; vok=vbad=0
for w in sample:
    ref = feat(load('audio/'+aud[w])); a = load(f'/tmp/s_ok_{hash(w)}.mp3'); b = load(f'/tmp/s_bad_{hash(w)}.mp3')
    ok_d.append(dtw(ref,feat(a))); bad_d.append(dtw(ref,feat(b)))
    e=norm(w); s=lambda t:t.replace(' ','').replace('-','')
    vok += s(vosk(a))==s(e); vbad += s(vosk(b))==s(e)
ok_d=np.array(ok_d); bad_d=np.array(bad_d)
pairs = np.mean(ok_d < bad_d)
best = max(((np.mean(ok_d<=t)+np.mean(bad_d>t))/2, t) for t in np.concatenate([ok_d,bad_d]))
print(f'DTW to Madina reference: same word closer than its wrong-ending twin in {pairs:.0%} of pairs')
print(f'DTW best single threshold: balanced accuracy {best[0]:.0%} (correct accepted {np.mean(ok_d<=best[1]):.0%}, wrong ending rejected {np.mean(bad_d>best[1]):.0%})')
print(f'VOSK on male voice: correct accepted {vok}/70, wrong ending accepted {vbad}/70')
