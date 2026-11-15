"""Slice a 5x5 sheet into 25 tiles and register them in words.js.
Usage: python3 tools/slice.py SHEET.png "word1,word2,...,word25" [--lang es|en]
  words = uz words, row by row; an empty name skips that cell.
  Without --lang the tile is the shared picture (SOZ_GEN, used by every language).
  With --lang es/en the tile is used only in that language's deck (SOZ_GEN_L) —
  for pictures drawn in that culture's setting (Spanish people, food, streets…)."""
import sys, json, re, hashlib
from PIL import Image
args = sys.argv[1:]; lang = None
if '--lang' in args: i = args.index('--lang'); lang = args[i + 1]; del args[i:i + 2]
assert lang in (None, 'es', 'en')
sheet, words = args[0], [w.strip() for w in args[1].split(',')]
assert len(words) <= 25
raw = open(sheet, 'rb').read(); ver = hashlib.md5(raw).hexdigest()[:4]   # new file name per sheet → no stale cache after a redraw
im = Image.open(sheet).convert('RGB'); c = im.size[0] / 5; inset = round(c * 0.04)
js = open('words.js', encoding='utf8').read()
if lang:
    if 'window.SOZ_GEN_L' not in js: js += '\nwindow.SOZ_GEN_L = {};\n'
    m = re.search(r'window\.SOZ_GEN_L = (\{.*?\});\n', js, re.S); allg = json.loads(m.group(1)); gen = allg.setdefault(lang, {})
else:
    m = re.search(r'window\.SOZ_GEN = (\{.*?\});', js, re.S); gen = json.loads(m.group(1))
n = 0
for i, uz in enumerate(words):
    if not uz: continue
    r, k = divmod(i, 5)
    name = (lang or 'g') + hashlib.md5(uz.encode()).hexdigest()[:8] + ver + '.webp'
    im.crop((round(k*c)+inset, round(r*c)+inset, round((k+1)*c)-inset, round((r+1)*c)-inset)).save('gen/' + name, 'WEBP', quality=88)
    gen[uz] = name; n += 1
out = json.dumps(allg if lang else gen, ensure_ascii=False, indent=1)
js = js[:m.start(1)] + out + js[m.end(1):]
open('words.js', 'w', encoding='utf8').write(js); print(n, 'tiles saved' + (f' for {lang}' if lang else '') + ';', len(gen), 'words have illustrations')
