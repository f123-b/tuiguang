"""Verify the actual local review server attachments and byte-range behavior."""
import hashlib
import json
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'.data/short-drama-51'

def main():
    checks=[]
    with httpx.Client(base_url='http://127.0.0.1:8790',trust_env=False,timeout=60) as client:
        for route,name in [('film.mp4','你来试试-v2.mp4'),('subtitles.srt','你来试试.srt'),('production.zip','你来试试-制作包-v2.zip')]:
            file=OUT/name;actual=hashlib.sha256(file.read_bytes()).hexdigest()
            r=client.get('/'+route+'?download=1');assert r.status_code==200 and r.headers['Content-Disposition'].startswith('attachment;')
            assert hashlib.sha256(r.content).hexdigest()==actual
            checks.append({'route':route,'status':r.status_code,'sha256':actual,'attachment':True})
        r=client.get('/film.mp4',headers={'Range':'bytes=100-199'})
        assert r.status_code==206 and r.content==(OUT/'你来试试-v2.mp4').read_bytes()[100:200]
        checks.append({'range':'100-199','status':206,'bytes':100})
        for header in ['bytes=999999999999-','bytes=5-2','bytes=-0','bytes=x-y']:
            assert client.get('/film.mp4',headers={'Range':header}).status_code==416
        assert client.post('/film.mp4').status_code==405 and client.get('/.env').status_code==404
    receipt={'status':'passed','checks':checks,'invalid_ranges':416,'post':405,'env_route':404,'browser_save_dialog':'not_automated'}
    (OUT/'download-validation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
