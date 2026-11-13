"""Strict production allowlist; no model weights, runtimes, accounts or environment files."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

PACK=Path(__file__).parent;ROOT=PACK.parents[3];OUT=ROOT/'.data/short-drama-53/v4';PRE=PACK.parent/'v3'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    proof=json.loads((PACK/'validation.json').read_text(encoding='utf-8'));assert proof['status']=='technical_checks_passed' and proof['edit_sha256']==sha(PACK/'edit.json')
    files=[p for p in PACK.rglob('*') if p.is_file() and p.suffix in {'.py','.json','.md','.mjs','.txt','.jpg','.png'}
        and '__pycache__' not in p.parts and p.name not in {'bundle-receipt.json','download-validation.json'}]
    files.extend(p for p in (PRE/'assets').iterdir() if p.suffix=='.png')
    files.extend(PRE.glob('*-prompt.txt'))
    files.extend(PRE/name for name in ['imagegen-provenance.json','reference-hashes.json','production.json','剧本与连续性.md','分镜表.md','superresolve.py','notices/Real-ESRGAN-LICENSE.txt'])
    for role in ['chen','lin']:
        for version in [1,2]:
            files.extend(OUT/'voices'/(role+f'-master-v{version}'+suffix) for suffix in ['.wav','.json','-asr.json'])
    for record in json.loads((PACK/'audio-lock.json').read_text(encoding='utf-8')):
        p=ROOT/record['path'];assert p.resolve().is_relative_to((OUT/'voices').resolve());files.append(p)
    for name in ['S01-audio-driven-v1','S04-audio-driven-v1','LIN-part1-audio-driven-v2','LIN-part2-audio-driven-v2']:
        files.extend(OUT/'takes'/(name+suffix) for suffix in ['.webm','.mp4','.json','-history.json'])
    files.extend(OUT/'takes'/('LIN-audio-driven-v1'+suffix) for suffix in ['.json','-history.json'])
    edit=json.loads((PACK/'edit.json').read_text(encoding='utf-8'))
    for shot in edit['segments']:
        if shot['id'] in ('S07','END'):continue
        for folder,name in [('prepared',shot.get('picture_take',shot['id']+'-picture-v4-cut2')),('sr',shot.get('sr_take',shot['id']+'-x2-v4'))]:
            files.extend([OUT/folder/(name+'.mp4'),OUT/folder/(name+'.json')])
    files.extend(OUT/name for name in ['你来试试-v4-超分成片.mp4','你来试试-v4-超分前对照.mp4','你来试试-v4.srt','film-v4.ass','mix-v4.wav','voice-and-room-v4.wav','end-v4.png'])
    files.extend(OUT/name for name in ['old-male-mouth.json','S04-mouth.json','S04-mouth-24fps.json','LIN1-mouth.json','LIN2-mouth.json'])
    files.extend([ROOT/'.data/short-drama-53/takes/s03-hands-v3.webm',ROOT/'.data/short-drama-53/takes/s03-hands-v3-receipt.json',
        ROOT/'examples/short-drama/dont-say-we/assets/youzhao-project-note-v8.mp4',ROOT/'examples/short-drama/dont-say-we/capture-evidence.json',
        ROOT/'docs/implementation/AUDIO_DRIVEN_DRAMA_VALIDATION.md',ROOT/'.data/short-drama-53/s2v/model-metadata.json',ROOT/'.data/short-drama-53/s2v/official-workflow.json'])
    files=sorted(set(files),key=lambda p:p.as_posix());entries=[]
    forbidden=re.compile(rb'(sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
    for p in files:
        assert p.is_file() and p.resolve().is_relative_to(ROOT),str(p)
        assert p.name!='.env' and not any(x in p.parts for x in ['models','node_modules','site-packages','product-profile','product-data'])
        if p.suffix in {'.py','.json','.md','.mjs','.txt','.srt','.ass'}:assert not forbidden.search(p.read_bytes()),'Credential-shaped text'
        entries.append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
    target=OUT/'你来试试-v4-制作包.zip';temp=target.with_suffix('.partial')
    with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED,compresslevel=5) as z:
        for p,e in zip(files,entries):z.write(p,'project/'+e['path'])
        z.writestr('package-manifest.json',json.dumps({'files':entries,'human_art_approval':False,'model_weights_included':False},ensure_ascii=False,indent=2))
    with zipfile.ZipFile(temp) as z:assert z.testzip() is None
    temp.replace(target)
    receipt={'path':target.relative_to(ROOT).as_posix(),'bytes':target.stat().st_size,'sha256':sha(target),'files':len(files),'crc_check':'passed','credential_pattern_scan':'passed','model_weights_included':False,'human_art_approval':False}
    (PACK/'bundle-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':main()
