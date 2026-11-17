import json, subprocess, base64, asyncio, urllib.request, edge_tts, time
URL='https://vhkzkqacljuvnepbcywg.supabase.co/functions/v1/soz-stt'; KEY='sb_publishable_wkZ5YttQxR6B0S-uhOEP5w_SLDqsL4k'; CODE='CPA8UYUY7GT3973E'
words=[('qancha turadi','qancha turadi'),('sakkiz','sakkiz'),('rahmat','rahmat'),('kasalxona','kasalxona'),
       ('sakkiz','sakkaz'),('rahmat','rahmot'),('kasalxona','kasalxono'),('yurak','yurok')]
async def tts():
    for i,(_,s) in enumerate(words): await edge_tts.Communicate(s,'uz-UZ-MadinaNeural',rate='-10%').save(f'/tmp/{i}.mp3')
asyncio.run(tts())
for i,(want,said) in enumerate(words):
    subprocess.run(['ffmpeg','-loglevel','error','-y','-i',f'/tmp/{i}.mp3','-af','silenceremove=start_periods=1:start_threshold=-45dB','-ar','16000','-ac','1','-f','s16le',f'/tmp/{i}.raw'],check=True)
    b=base64.b64encode(open(f'/tmp/{i}.raw','rb').read()).decode()
    req=urllib.request.Request(URL,data=json.dumps({'code':CODE,'lang':'uz','audio':b}).encode(),headers={'apikey':KEY,'Content-Type':'application/json'})
    t=time.time()
    try: r=urllib.request.urlopen(req,timeout=30); out=r.read().decode()
    except urllib.error.HTTPError as e: out=f'{e.code} '+e.read().decode()
    print(f'want={want!r} said={said!r} -> {out} ({time.time()-t:.1f}s)', flush=True)
