"""Pre-record Uzbek audio for every word (no phone or browser has an Uzbek voice).
Runs on GitHub (.github/workflows/tts.yml) whenever words.js changes; only missing files are made.
Writes audio/uz-<hash>.mp3 and audio.js (window.SOZ_AUDIO = {uz: {word: file}})."""
import re, json, hashlib, os, asyncio, edge_tts
VOICE, RATE = 'uz-UZ-MadinaNeural', '-10%'
TEACHER = {
    'uz': ('uz-UZ-MadinaNeural', ['Barakalla!', 'Toʻgʻri!', 'Zoʻr!', 'Ajoyib!', 'Juda yaxshi!'], ['Yana bir marta.']),
    'es': ('es-ES-ElviraNeural', ['¡Muy bien!', '¡Correcto!', '¡Perfecto!', '¡Genial!', '¡Eso es!'], ['Otra vez.']),
    'en': ('en-US-AriaNeural', ['Great!', 'Correct!', 'Well done!', 'Perfect!', 'Nice!'], ['Once more.']),
}          # a little slower than normal — easier to hear for a learner
js = open('words.js', encoding='utf8').read()
rows = re.search(r'window\.SOZ_WORDS = `(.*?)`', js, re.S).group(1).strip().split('\n')
words = [r.split('|')[0].strip() for r in rows if '|' in r]
def clean(t): return re.sub(r'\s*\(.*?\)', '', t.replace('…', '')).strip()
old = {}
if os.path.exists('audio.js'):
    m = re.search(r'window\.SOZ_AUDIO = (\{.*\});', open('audio.js', encoding='utf8').read(), re.S)
    if m: old = json.loads(m.group(1)).get('uz', {})
async def main():
    out, made = {}, 0
    for w in words:
        if re.fullmatch(r'[0-9]+', w) or not clean(w): continue
        f = 'uz-' + hashlib.md5((VOICE + RATE + clean(w)).encode()).hexdigest()[:10] + '.mp3'
        if not os.path.exists('audio/' + f):
            await edge_tts.Communicate(clean(w), VOICE, rate=RATE).save('audio/' + f); made += 1
        out[w] = f
    # the teacher's voice: short praise / "once more" in each language
    praise = {}
    for lang, (voice, ok, again) in TEACHER.items():
        files = {'ok': [], 'again': []}
        for kind, phrases in (('ok', ok), ('again', again)):
            for ph in phrases:
                f = f'fx-{lang}-' + hashlib.md5((voice + ph).encode()).hexdigest()[:8] + '.mp3'
                if not os.path.exists('audio/' + f): await edge_tts.Communicate(ph, voice).save('audio/' + f); made += 1
                files[kind].append(f)
        praise[lang] = files
    out = {'uz': out, 'praise': praise}
    open('audio.js', 'w', encoding='utf8').write('// Pre-recorded audio, made by tools/tts.py. Do not edit by hand.\nwindow.SOZ_AUDIO = ' + json.dumps(out, ensure_ascii=False, indent=1) + ';\n')
    print(made, 'new files,', len(out['uz']), 'words have audio')
asyncio.run(main())
