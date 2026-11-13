"""Cut stock-voice masters once; all actor timing is frozen before video sampling."""
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np
import soundfile as sf

PACK=Path(__file__).parent;ROOT=PACK.parents[3];OUT=ROOT/'.data/short-drama-53/v4/voices'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if __name__=='__main__':
    cuts=[('01-give-up','chen',0,1.2,.8),('02-wait','lin',0,1.12,.95),('03-fault','lin',1.3,4.45,.95),
        ('04-change','lin',4.6,6.2,.95),('04-again','lin',6.2,7.28,.95),('05-found','chen',1.3,3.28,.8),('06-answer','lin',7.28,8.16,.95)]
    records=[]
    for name,role,start,end,tempo in cuts:
        source=OUT/(role+'-master-v2.wav');r=json.loads(source.with_suffix('.json').read_text(encoding='utf-8'))
        assert sha(source)==r['sha256'] and r['status']=='duration_checked'
        target=OUT/(name+'-v4.wav');assert not target.exists()
        subprocess.run(['ffmpeg','-v','error','-nostdin','-n','-ss',str(start),'-t',str(end-start),'-i',str(source),
            '-af',f'atempo={tempo}','-ar','24000','-c:a','pcm_s16le',str(target)],check=True)
        wave,sr=sf.read(target);assert sr==24000
        records.append({'id':name,'role':role,'speaker':r['speaker'],'source':source.relative_to(ROOT).as_posix(),
            'source_sha256':r['sha256'],'source_in_sec':start,'source_out_sec':end,'atempo':tempo,'pitch_shift':False,
            'duration_sec':len(wave)/sr,'path':target.relative_to(ROOT).as_posix(),'sha256':sha(target),'human_listening_review':False})
    by_id={r['id']:r for r in records}
    timings={'S01':[(.18,'01-give-up')],'S02':[(.08,'02-wait'),(1.38,'03-fault')],
        'S04':[(.28,'05-found')],'S06':[(.25,'06-answer')]}
    for sid,cues in timings.items():
        wave=np.zeros(round(77/16*24000),np.float32)
        for start,name in cues:
            cue,_=sf.read(ROOT/by_id[name]['path']);at=round(start*24000)
            assert at+len(cue)<=len(wave),(sid,name)
            wave[at:at+len(cue)]+=cue
        target=OUT/(sid+'-audio-v4.wav');assert not target.exists();sf.write(target,wave,24000,subtype='PCM_16')
        records.append({'shot_id':sid,'duration_sec':77/16,'path':target.relative_to(ROOT).as_posix(),'sha256':sha(target),'cues':cues,'fixed_before_video':True})
    (PACK/'audio-lock.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8');print('Locked seven cuts from two actor masters and four timed audio tracks')
