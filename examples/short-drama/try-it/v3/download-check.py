"""Check real attachment bytes and range/deny behavior of the loopback-only server."""
import hashlib
import json
from pathlib import Path
import httpx

PACK=Path(__file__).parent;ROOT=PACK.parents[3];OUT=ROOT/'.data/short-drama-53'
def main():
    checks=[]
    with httpx.Client(base_url='http://127.0.0.1:8791',trust_env=False,timeout=60) as client:
        for route,name in [('film.mp4','你来试试-v3-1080p.mp4'),('sr.mp4','你来试试-v3-2K超分.mp4'),('native.mp4','你来试试-v3-原片对照.mp4'),('subtitles.srt','你来试试.srt'),('production.zip','你来试试-v3-制作包.zip')]:
            expected=hashlib.sha256((OUT/name).read_bytes()).hexdigest();digest=hashlib.sha256()
            with client.stream('GET','/'+route+'?download=1') as response:
                assert response.status_code==200 and response.headers['Content-Disposition'].startswith('attachment;')
                for block in response.iter_bytes():digest.update(block)
            assert digest.hexdigest()==expected
            checks.append({'route':route,'status':200,'sha256':expected,'attachment':True})
        with (OUT/'你来试试-v3-1080p.mp4').open('rb') as source:source.seek(100);expected=source.read(100)
        r=client.get('/film.mp4',headers={'Range':'bytes=100-199'});assert r.status_code==206 and r.content==expected
        for header in ['bytes=999999999999-','bytes=5-2','bytes=-0','bytes=x-y']:assert client.get('/film.mp4',headers={'Range':header}).status_code==416
        assert client.post('/film.mp4').status_code==405 and client.get('/.env').status_code==404
        for name in ['lin-three-view-v1','chen-three-view-v1','scene-empty-v1','s02-close-v3','s03-hands-v3','s04-close-v3','s06-close-v3']:
            r=client.head('/'+name+'.png');assert r.status_code==200 and int(r.headers['Content-Length'])==(PACK/'assets'/(name+'.png')).stat().st_size
    proof={'status':'passed','attachments':checks,'range':206,'invalid_range':416,'post':405,'env_route':404,'reference_routes':7,'browser_save_dialog':'not automated'}
    (PACK/'download-validation.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8');print('PASS five attachment SHAs / seven reference routes / byte ranges / deny rules')
if __name__=='__main__':main()
