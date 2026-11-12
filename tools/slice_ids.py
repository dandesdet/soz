"""Slice a 5x5 sheet of user-added words (soz_words) into gen/u<id>.webp.
Usage: python3 tools/slice_ids.py SHEET.png "id1,id2,...,id25"   (soz_words ids, row by row)
Prints the SQL to store the file names in soz_words.img."""
import sys
from PIL import Image
sheet, ids = sys.argv[1], [i.strip() for i in sys.argv[2].split(',') if i.strip()]
assert len(ids) <= 25
im = Image.open(sheet).convert('RGB'); c = im.size[0] / 5; inset = round(c * 0.04)
sql = []
for i, wid in enumerate(ids):
    r, k = divmod(i, 5)
    name = f'u{int(wid)}.webp'
    im.crop((round(k*c)+inset, round(r*c)+inset, round((k+1)*c)-inset, round((r+1)*c)-inset)).save('gen/' + name, 'WEBP', quality=88)
    sql.append(f"update soz_words set img = '{name}' where id = {int(wid)};")
print('\n'.join(sql))
