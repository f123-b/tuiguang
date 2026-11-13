"""Only versioned production files and explicitly selected local media; no models/keys."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

PACK=Path(__file__).parent;ROOT=PACK.parents[3];OUT=ROOT/'.data/short-drama-53'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    result=json.loads((PACK/'validation.json').read_text(encoding='utf-8'));assert result['status']=='technical_checks_passed'
    files=[p for p in PACK.rglob('*') if p.is_file() and p.suffix in {'.py','.json','.md','.mjs','.txt','.png','.jpg'}
        and '__pycache__' not in p.parts and p.name not in {'bundle-receipt.json','download-validation.json'}]
    for folder,suffixes in [('takes',{'.webm','.json'}),('sync',{'.json','.mp4'}),('sr',{'.json','.mp4'})]:
        files.extend(p for p in (OUT/folder).iterdir() if p.is_file() and p.suffix in suffixes and '-silent' not in p.name)
    for name in ['你来试试-v3-2K超分.mp4','你来试试-v3-1080p.mp4','你来试试-v3-原片对照.mp4','你来试试.srt','film.ass','mix.wav','original-bed.wav','end-card.png','cue-sheet.json','prepared.json']:
        files.append(OUT/name)
    cues=json.loads((OUT/'cue-sheet.json').read_text(encoding='utf-8'))
    for cue in cues:
        files.extend([OUT/'voices'/(cue['id']+'.wav'),OUT/'voices'/(cue['id']+'.json')])
    files.append(OUT/'voices/receipts.json')
    for sid in ['S02','S04','S06']:files.append(OUT/'voices'/(sid+'-timed.wav'))
    files.extend([PACK.parent/'assets/s01-two-shot-v1.png',PACK.parent/'generate.py',PACK.parent/'sync.py',PACK.parent/'finish.py',PACK.parent/'production.json',
        PACK.parent/'sync-models.json',PACK.parent/'resnet-conversion.json',PACK.parent/'notices/MuseTalk-LICENSE.txt',
        ROOT/'.data/short-drama-51/sync/S01-timed-v1.mp4',ROOT/'.data/short-drama-51/sync/S01-timed-v1.json',
        ROOT/'.data/short-drama-51/takes/s01-handoff-v1.webm',ROOT/'.data/short-drama-51/takes/s01-handoff-v1-receipt.json',
        ROOT/'examples/short-drama/dont-say-we/assets/youzhao-project-note-v8.mp4',ROOT/'examples/short-drama/dont-say-we/capture-evidence.json',
        ROOT/'docs/implementation/DRAMA_MASTERING_VALIDATION.md'])
    files=sorted(set(files),key=lambda p:p.as_posix())
    forbidden=re.compile(rb'(sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
    entries=[]
    for p in files:
        assert p.is_file() and p.resolve().is_relative_to(ROOT)
        assert p.name!='.env' and not any(x in p.parts for x in ['models','node_modules','site-packages','product-profile','product-data'])
        if p.suffix in {'.json','.py','.md','.mjs','.txt','.srt','.ass'}:assert not forbidden.search(p.read_bytes()),'Credential-shaped text'
        entries.append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
    target=OUT/'你来试试-v3-制作包.zip';temp=target.with_suffix('.partial')
    with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED,compresslevel=5) as bundle:
        for p,e in zip(files,entries):bundle.write(p,'project/'+e['path'])
        bundle.writestr('package-manifest.json',json.dumps({'files':entries,'human_art_approval':False,'model_weights_included':False},ensure_ascii=False,indent=2))
    with zipfile.ZipFile(temp) as bundle:assert bundle.testzip() is None
    temp.replace(target)
    proof={'file':target.relative_to(ROOT).as_posix(),'bytes':target.stat().st_size,'sha256':sha(target),'files':len(files),
        'crc_check':'passed','credential_pattern_scan':'passed','model_weights_included':False,'human_art_approval':False}
    (PACK/'bundle-receipt.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(proof,ensure_ascii=False))
if __name__=='__main__':main()
