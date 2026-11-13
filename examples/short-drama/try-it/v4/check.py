"""Verify source-locked performance, final media and actual mix timing; not art approval."""
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np
from scipy.signal import correlate,correlation_lags
import soundfile as sf
from contracts import validate_actor_sources,validate_audio_graph

PACK=Path(__file__).parent;ROOT=PACK.parents[3];OUT=ROOT/'.data/short-drama-53/v4'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def probe(p):return json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(p)],encoding='utf-8'))
def decode(p):subprocess.run(['ffmpeg','-v','error','-nostdin','-xerror','-i',str(p),'-f','null','-'],check=True,capture_output=True)
def main():
    edit=json.loads((PACK/'edit.json').read_text(encoding='utf-8'));m=json.loads((PACK/'edit-manifest.json').read_text(encoding='utf-8'))
    assert m['edit_sha256']==sha(PACK/'edit.json') and not m['human_art_approval']
    count=sum(s['frames'] for s in edit['segments']);assert count==438
    records=[]
    for item in m['outputs']:
        p=ROOT/item['path'];assert sha(p)==item['sha256'];streams=probe(p)['streams']
        v=next(s for s in streams if s['codec_type']=='video');a=next(s for s in streams if s['codec_type']=='audio')
        assert (v['width'],v['height'],v['r_frame_rate'],int(v['nb_frames']))==(1920,1080,'24/1',438)
        assert abs(float(v['duration'])-18.25)<.001 and abs(float(a['duration'])-18.25)<.05 and a['sample_rate']=='48000'
        decode(p);records.append({'file':p.name,'frames':438,'duration_sec':18.25,'decode':'pass','sha256':sha(p)})
    assert len(records)==2
    locks=json.loads((PACK/'audio-lock.json').read_text(encoding='utf-8'));cuts=[r for r in locks if r.get('role')];validate_actor_sources(cuts)
    for r in locks:assert sha(ROOT/r['path'])==r['sha256']
    for role in ['chen','lin']:
        p=OUT/'voices'/(role+'-master-v2.wav');r=json.loads(p.with_suffix('.json').read_text(encoding='utf-8'));assert sha(p)==r['sha256'] and r['status']=='duration_checked'
    performance=[]
    names=['S01-audio-driven-v1','S04-audio-driven-v1','LIN-part1-audio-driven-v2','LIN-part2-audio-driven-v2']
    for name in names:
        source=OUT/'takes'/(name+'.webm');r=json.loads(source.with_suffix('.json').read_text(encoding='utf-8'))
        assert r['status']=='complete' and sha(source)==r['sha256'] and sha(ROOT/r['source'])==r['source_sha256'] and sha(ROOT/r['audio'])==r['audio_sha256']
        validate_audio_graph(r['graph'],r['native_frames']/16);v=next(s for s in probe(source)['streams'] if s['codec_type']=='video')
        assert (v['width'],v['height'],v['r_frame_rate'],int(v['nb_read_frames']))==(832,480,'16/1',r['native_frames']);decode(source)
        performance.append({'name':name,'prompt_id':r['prompt_id'],'native_frames':r['native_frames'],'elapsed_sec':r['elapsed_sec'],'audio_sha256':r['audio_sha256']})
    # Compare sample values, not just filenames: rendered female chunks must use the exact master interval heard in the edit.
    whole,sr=sf.read(OUT/'voices/LIN-audio-v4.wav',dtype='int16');assert sr==24000
    mappings=[]
    for name,offset in [('LIN1-audio-v4.wav',0),('LIN2-audio-v4.wav',4.75)]:
        chunk,sr=sf.read(OUT/'voices'/name,dtype='int16');start=round(offset*sr)
        assert np.array_equal(chunk,whole[start:start+len(chunk)])
        mappings.append({'file':name,'whole_source_start_sec':offset,'samples_equal':True})
    for s in edit['segments']:
        if s['id'] in ('S07','END'):continue
        prep=OUT/'prepared'/(s.get('picture_take',s['id']+'-picture-v4-cut2')+'.mp4');p=json.loads(prep.with_suffix('.json').read_text(encoding='utf-8'))
        assert p['frames']==s['frames'] and sha(prep)==p['sha256']
        up=OUT/'sr'/(s.get('sr_take',s['id']+'-x2-v4')+'.mp4');r=json.loads(up.with_suffix('.json').read_text(encoding='utf-8'))
        assert r['status']=='complete' and sha(up)==r['sha256'] and r['source_sha256']==sha(prep)
        assert r['neural_picture']==[x*2 for x in r['native_picture']] and r['frames']==s['frames'] and not r['params']['face_replacement']
    # Check that mastering did not shift the input speech against the already generated picture.
    original,sr=sf.read(OUT/'voice-and-room-v4.wav');mixed,sr2=sf.read(OUT/'mix-v4.wav');assert sr==sr2==48000
    x=original.mean(axis=1);y=mixed.mean(axis=1);corr=correlate(y,x,method='fft');lags=correlation_lags(len(y),len(x));lag=int(lags[int(np.argmax(corr))])
    assert abs(lag)<=2000,f'Postmix moved dialogue by {lag} samples'
    cues=json.loads((PACK/'audio-edit-receipt.json').read_text(encoding='utf-8'))['cues'];assert len(cues)==7
    result={'status':'technical_checks_passed','edit_sha256':sha(PACK/'edit.json'),'mix_sha256':sha(OUT/'mix-v4.wav'),'outputs':records,'performances':performance,'female_master_mapping':mappings,'mix_correlation_lag_samples':lag,
        'mix_correlation_lag_ms':lag/48,'cue_count':7,'neural_frames':342,'human_art_approval':False,'user_rejected_previous_version':'v3',
        'limitations':'Metrics do not certify phoneme accuracy, acting or voice preference. Generated native832×480/16fps, not native1080p.',
        'production_deployed':False}
    (PACK/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print('PASS two films /438 frames / four audio-driven sources / two voice masters / exact female audio map; mix lag samples',lag)
if __name__=='__main__':main()
