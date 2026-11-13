"""Freeze one continuous female performance plus a short opening male track."""
import hashlib
import json
from pathlib import Path
import subprocess
PACK=Path(__file__).parent;ROOT=PACK.parents[3];OUT=ROOT/'.data/short-drama-53/v4/voices'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if __name__=='__main__':
    target=OUT/'LIN-audio-v4.wav';assert not target.exists()
    source=OUT/'lin-master-v2.wav';source_record=json.loads(source.with_suffix('.json').read_text(encoding='utf-8'))
    assert sha(source)==source_record['sha256']
    subprocess.run(['ffmpeg','-v','error','-nostdin','-n','-i',str(source),'-af','atempo=0.95,adelay=150,apad=whole_dur=9.0625,atrim=duration=9.0625',
        '-ar','24000','-c:a','pcm_s16le',str(target)],check=True)
    locks=json.loads((PACK/'audio-lock.json').read_text(encoding='utf-8'))
    locks.append({'shot_id':'LIN','cast_role':'lin','duration_sec':145/16,'path':target.relative_to(ROOT).as_posix(),'sha256':sha(target),
        'master_source':source.relative_to(ROOT).as_posix(),'master_sha256':sha(source),'atempo':.95,'lead_sec':.15,'fixed_before_video':True})
    target=OUT/'S01-audio-short-v4.wav';assert not target.exists()
    old=next(r for r in locks if r.get('shot_id')=='S01')
    subprocess.run(['ffmpeg','-v','error','-nostdin','-n','-i',str(ROOT/old['path']),'-t',str(37/16),'-c:a','pcm_s16le',str(target)],check=True)
    old.update(path=target.relative_to(ROOT).as_posix(),sha256=sha(target),duration_sec=37/16,previous_audio_preserved='S01-audio-v4.wav')
    (PACK/'audio-lock.json').write_text(json.dumps(locks,ensure_ascii=False,indent=2),encoding='utf-8');print('Locked LIN145 frames, S01 37 frames')
