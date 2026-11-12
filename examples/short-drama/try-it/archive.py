"""Portable film package from a strict source/media allowlist. No model/runtime."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT=Path(__file__).resolve().parents[3]
PACK=Path(__file__).parent
OUT=ROOT/'.data/short-drama-51'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    result=json.loads((OUT/'validation-v2.json').read_text(encoding='utf-8'))
    assert result['status']=='technical_checks_passed'
    files=[p for p in PACK.rglob('*') if p.is_file() and p.suffix in {'.json','.py','.md','.mjs','.png','.jpg','.txt'} and '__pycache__' not in p.parts]
    edit=json.loads((PACK/'edit.json').read_text(encoding='utf-8'))
    for i,s in enumerate(edit['segments']):
        files.append(OUT/f'edit-v2-{i:02}.mp4')
        if s.get('take'):
            prefix=OUT/'takes'/s['take']
            files.extend([prefix.with_suffix('.webm'),prefix.with_name(prefix.name+'-receipt.json'),prefix.with_name(prefix.name+'-history.json')])
        if s.get('sync_bbox'):
            prefix=OUT/'sync'/s.get('sync_take',s['id']+'-timed-v1')
            files.extend([prefix.with_suffix('.mp4'),prefix.with_suffix('.json'),OUT/'voices'/s.get('timed_audio',s['id']+'-timed.wav')])
    for file in ['你来试试-v2.mp4','你来试试.srt','film.ass','mix.wav','original-bed.wav','end-card.png','edit-v2.json','cue-sheet.json','prepared.json','validation-v2.json','video-project-ir.json','sync-models.json','resnet-conversion.json','browser-playback-v2.json','s06-measured-roi-v1.json']:
        files.append(OUT/file)
    voices=json.loads((OUT/'voices/receipts.json').read_text(encoding='utf-8'))
    for r in voices:files.extend([OUT/'voices'/(r['id']+'.wav'),OUT/'voices'/(r['id']+'.json')])
    files.append(OUT/'voices/receipts.json')
    files.extend([ROOT/'examples/short-drama/dont-say-we/assets/youzhao-project-note-v8.mp4',ROOT/'examples/short-drama/dont-say-we/capture-evidence.json',ROOT/'examples/short-drama/dont-say-we/build-provenance.json',ROOT/'docs/implementation/TRY_IT_DRAMA_VALIDATION.md'])
    files=sorted(set(files),key=lambda p:p.as_posix())
    forbidden=re.compile(rb'(sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
    entries=[]
    for p in files:
        assert p.is_file() and p.is_relative_to(ROOT)
        assert p.name not in {'.env','cookies.json'} and not any(x in p.parts for x in ['models','node_modules','site-packages','product-profile','product-data'])
        if p.suffix in {'.json','.py','.md','.mjs','.txt','.srt','.ass'}:assert not forbidden.search(p.read_bytes()),'Credential-shaped text blocked'
        entries.append({'path':str(p.relative_to(ROOT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha(p)})
    target=OUT/'你来试试-制作包-v2.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=5) as bundle:
        for p,entry in zip(files,entries):bundle.write(p,'project/'+entry['path'])
        bundle.writestr('package-manifest.json',json.dumps({'files':entries,'technical_validation':result['film_sha256'],'human_art_approval':False},ensure_ascii=False,indent=2))
    with zipfile.ZipFile(target) as bundle:assert bundle.testzip() is None
    receipt={'file':str(target.relative_to(ROOT)),'bytes':target.stat().st_size,'sha256':sha(target),'source_file_count':len(files),'crc_check':'passed','credential_pattern_scan':'passed','model_weights_included':False,'human_art_approval':False}
    (OUT/'bundle-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
