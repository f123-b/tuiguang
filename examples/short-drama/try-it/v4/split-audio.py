"""Preserve failed long performance; split the SAME audio at measured silent boundaries."""
import hashlib
import json
from pathlib import Path
import subprocess
PACK=Path(__file__).parent;ROOT=PACK.parents[3];OUT=ROOT/'.data/short-drama-53/v4/voices'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if __name__=='__main__':
    locks=json.loads((PACK/'audio-lock.json').read_text(encoding='utf-8'));whole=next(r for r in locks if r.get('shot_id')=='LIN')
    source=ROOT/whole['path'];assert sha(source)==whole['sha256']
    for sid,start,frames in [('LIN1',0,77),('LIN2',4.75,69)]:
        target=OUT/(sid+'-audio-v4.wav');assert not target.exists()
        subprocess.run(['ffmpeg','-v','error','-nostdin','-n','-ss',str(start),'-i',str(source),'-t',str(frames/16),'-ar','24000','-c:a','pcm_s16le',str(target)],check=True)
        locks.append({'shot_id':sid,'cast_role':'lin','duration_sec':frames/16,'path':target.relative_to(ROOT).as_posix(),'sha256':sha(target),
            'whole_audio':whole['path'],'whole_audio_sha256':whole['sha256'],'source_in_sec':start,'fixed_before_video':True})
    (PACK/'audio-lock.json').write_text(json.dumps(locks,ensure_ascii=False,indent=2),encoding='utf-8');print('Split same LIN audio:77 frames and69 frames;0.0625 sec overlap')
