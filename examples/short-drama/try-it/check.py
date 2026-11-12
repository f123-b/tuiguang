"""Technical media and provenance checks; explicitly NOT an art approval."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import array

ROOT=Path(__file__).resolve().parents[3]
PACK=Path(__file__).parent
OUT=ROOT/'.data/short-drama-51'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def probe(path):return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)],encoding='utf-8'))

def check(take):
    film=OUT/f'你来试试-{take}.mp4'
    assert film.exists(),'Finished film not yet available'
    edit=json.loads((PACK/'edit.json').read_text(encoding='utf-8'))
    receipt=json.loads((OUT/f'edit-{take}.json').read_text(encoding='utf-8'))
    frames=sum(s['frames'] for s in edit['segments']);duration=frames/30
    assert receipt['frames']==frames and receipt['sha256']==sha(film)
    info=probe(film);v=next(s for s in info['streams'] if s['codec_type']=='video');a=next(s for s in info['streams'] if s['codec_type']=='audio')
    assert (v['width'],v['height'],v['r_frame_rate'])==(1920,1080,'30/1')
    assert v['codec_name']=='h264' and a['codec_name']=='aac' and int(a['sample_rate'])==48000
    assert int(v['nb_frames'])==frames and abs(float(v['duration'])-duration)<.001 and abs(float(a['duration'])-duration)<.05
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-xerror','-i',str(film),'-f','null','-'],check=True,capture_output=True)
    source_checks=[]
    for s in edit['segments']:
        if not s.get('take'):continue
        raw=OUT/'takes'/(s['take']+'.webm');r=json.loads(raw.with_name(s['take']+'-receipt.json').read_text(encoding='utf-8'))
        assert r['status']=='complete' and sha(raw)==r['sha256']
        source=ROOT/r['source'];assert sha(source)==r['source_sha256']
        native=probe(raw);nv=next(x for x in native['streams'] if x['codec_type']=='video')
        assert (nv['width'],nv['height'],nv['r_frame_rate'])==(1280,704,'24/1')
        counted=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=nb_read_frames','-of','json',str(raw)],text=True))
        assert int(counted['streams'][0]['nb_read_frames'])==r['input']['frames']
        if s.get('sync_bbox'):
            sync=OUT/'sync'/(s.get('sync_take',s['id']+'-timed-'+take)+'.mp4');sync_r=json.loads(sync.with_suffix('.json').read_text(encoding='utf-8'))
            assert sync_r['status']=='complete' and sha(sync)==sync_r['sha256'] and sync_r['source_sha256']==sha(raw)
            assert sync_r['audio_sha256']==sha(ROOT/sync_r['audio'])
            assert sync_r['frames']==len(sync_r['frame_indices'])==len(sync_r['crop_boxes'])
            if sync_r.get('roi_file'):
                roi=ROOT/sync_r['roi_file'];assert sha(roi)==sync_r['roi_sha256']
                measured=json.loads(roi.read_text(encoding='utf-8'));assert measured['source_sha256']==sha(raw)
                assert all(box==measured['boxes'][index] for index,box in zip(sync_r['frame_indices'],sync_r['crop_boxes']))
        source_checks.append({'shot_id':s['id'],'provider_request_id':r['provider_request_id'],'sha256':r['sha256'],'native_frames':r['input']['frames']})
    cues=json.loads((OUT/'cue-sheet.json').read_text(encoding='utf-8'))
    assert len(cues)==7 and all(0<=c['start']<c['end']<=duration for c in cues)
    assert all(b['start']>=a['end'] for a,b in zip(cues,cues[1:]))
    for c in cues:assert sha(OUT/'voices'/(c['id']+'.wav'))==c['sha256']
    srt=(OUT/'你来试试.srt').read_text(encoding='utf-8');assert len(re.findall('-->',srt))==7 and all(c['text'] in srt for c in cues)
    # Measure original channel samples; mono downmix can add 3 dB.
    pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(film),'-vn','-c:a','pcm_f32le','-f','f32le','-'])
    samples=array.array('f');samples.frombytes(pcm);peak=max(abs(x) for x in samples);rms=(sum(x*x for x in samples)/len(samples))**.5
    assert .005<rms<.4 and peak<.99
    loud=subprocess.run(['ffmpeg','-hide_banner','-i',str(film),'-af','loudnorm=I=-16:TP=-1.5:LRA=9:print_format=json','-f','null','-'],capture_output=True,text=True,check=True)
    measures,_=json.JSONDecoder().raw_decode(loud.stderr[loud.stderr.rfind('{'):]);assert -19<=float(measures['input_i'])<=-13 and float(measures['input_tp'])<-.3
    result={'status':'technical_checks_passed','film_sha256':sha(film),'bytes':film.stat().st_size,'frames':frames,'duration_sec':duration,
        'fully_decoded':True,'native_sources':source_checks,'cues':7,'rms':rms,'sample_peak':peak,'loudness':measures,
        'human_listening':'not_run','user_art_approval':False,'commercial_release_approval':False,'production_deployed':False}
    (OUT/f'validation-{take}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--take',default='v2');check(ap.parse_args().take)
