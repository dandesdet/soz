"""Slice a 5x5 sheet into 25 tiles and register them in words.js.
Usage: python3 tools/slice.py SHEET.png "word1,word2,...,word25"   (uz words, row by row)"""
import sys, json, re, hashlib
from PIL import Image
sheet, words = sys.argv[1], [w.strip() for w in sys.argv[2].split(',')]
assert len(words) <= 25
im = Image.open(sheet).convert('RGB'); c = im.size[0] / 5; inset = round(c * 0.04)
js = open('words.js', encoding='utf8').read()
m = re.search(r'window\.SOZ_GEN = (\{.*?\});', js, re.S); gen = json.loads(m.group(1))
for i, uz in enumerate(words):
    r, k = divmod(i, 5)
    name = 'g' + hashlib.md5(uz.encode()).hexdigest()[:8] + '.webp'
    im.crop((round(k*c)+inset, round(r*c)+inset, round((k+1)*c)-inset, round((r+1)*c)-inset)).save('gen/' + name, 'WEBP', quality=88)
    gen[uz] = name
js = js[:m.start(1)] + json.dumps(gen, ensure_ascii=False, indent=1) + js[m.end(1):]
open('words.js', 'w', encoding='utf8').write(js); print(len(words), 'tiles saved;', len(gen), 'words have illustrations')
