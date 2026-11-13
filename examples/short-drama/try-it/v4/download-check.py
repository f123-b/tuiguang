"""Verify actual downloaded attachment bytes, byte ranges and private path denial."""
import hashlib
import json
from pathlib import Path
import httpx
PACK=Path(__file__).parent;ROOT=PACK.parents[3];OUT=ROOT/'.data/short-drama-53/v4'
def main():
    checks=[]
    with httpx.Client(base_url='http://127.0.0.1:8792',trust_env=False,timeout=60) as c:
        assert c.get('/watch').status_code==200
        for route,name in [('film.mp4','你来试试-v4-超分成片.mp4'),('baseline.mp4','你来试试-v4-超分前对照.mp4'),('subtitles.srt','你来试试-v4.srt'),('production.zip','你来试试-v4-制作包.zip')]:
            expected=hashlib.sha256((OUT/name).read_bytes()).hexdigest();digest=hashlib.sha256()
            with c.stream('GET','/'+route+'?download=1') as r:
                assert r.status_code==200 and r.headers['Content-Disposition'].startswith('attachment;')
                for block in r.iter_bytes():digest.update(block)
            assert digest.hexdigest()==expected;checks.append({'route':route,'status':200,'sha256':expected,'attachment':True})
        data=(OUT/'你来试试-v4-超分成片.mp4').read_bytes()
        for header,expected in [('bytes=100-199',data[100:200]),('bytes=-100',data[-100:])]:
            r=c.get('/film.mp4',headers={'Range':header});assert r.status_code==206 and r.content==expected
        for header in ['bytes=999999999999-','bytes=5-2','bytes=-0','bytes=x-y']:assert c.get('/film.mp4',headers={'Range':header}).status_code==416
        assert c.post('/film.mp4').status_code==405 and c.get('/.env').status_code==404 and c.get('/../.env').status_code==404
        for name in ['lin-three-view-v1','chen-three-view-v1','scene-empty-v1','s02-close-v3','s03-hands-v3','s04-close-v3','s06-close-v3']:
            r=c.head('/'+name+'.png');assert r.status_code==200 and int(r.headers['Content-Length'])==(PACK.parent/'v3/assets'/(name+'.png')).stat().st_size
    result={'status':'passed','attachments':checks,'range':206,'suffix_range':206,'invalid_range':416,'post':405,'private_routes':404,'reference_routes':7,'browser_save_dialog':'not automated'}
    (PACK/'download-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print('PASS four attachment SHAs / seven references / byte and suffix ranges / deny rules')
if __name__=='__main__':main()
