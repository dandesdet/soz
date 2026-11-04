"""Regenerate sw.js so every file is cached for offline use. Run after adding words or images."""
import os, json, time
files = ['./', 'index.html', 'words.js', 'manifest.json', 'icon-192.png', 'icon-512.png', 'apple-touch-icon.png']
for d in ('img', 'gen'):
    files += [f'{d}/{f}' for f in sorted(os.listdir(d)) if f.endswith('.webp')]
v = 'soz-' + time.strftime('%Y%m%d%H%M')
open('sw.js', 'w').write(f"""// Offline cache: everything the app needs is stored on the phone after the first open.
const V='{v}', FILES={json.dumps(files)};
self.addEventListener('install',e=>e.waitUntil(caches.open(V).then(c=>c.addAll(FILES)).then(()=>self.skipWaiting())));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==V).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{{ if(e.request.method!=='GET')return;
  e.respondWith(fetch(e.request).then(r=>{{const c=r.clone();caches.open(V).then(x=>x.put(e.request,c));return r}}).catch(()=>caches.match(e.request,{{ignoreSearch:true}})));}});
""")
print(len(files), 'files in offline cache, version', v)
