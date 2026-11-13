"""Fail closed on missing artifacts or false HD/SR provenance; never an art rating."""
import hashlib
import json
from pathlib import Path
import subprocess
import struct

PACK=Path(__file__).parent;ROOT=PACK.parents[3];OUT=ROOT/'.data/short-drama-53'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def probe(p):return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)],encoding='utf-8'))

def check():
    from preflight import check as preflight
    preflight();edit=json.loads((PACK/'edit.json').read_text(encoding='utf-8'))
    manifest=json.loads((PACK/'edit-manifest.json').read_text(encoding='utf-8'))
    assert manifest['edit_sha256']==sha(PACK/'edit.json')
    assert not manifest['human_art_approval'] and not manifest['deployed'] and manifest['fps']==24 and manifest['frames']==528
    outputs=[]
    for record in manifest['outputs']:
        path=ROOT/record['path'];assert sha(path)==record['sha256']
        p=probe(path);v=next(s for s in p['streams'] if s['codec_type']=='video');a=next(s for s in p['streams'] if s['codec_type']=='audio')
        expected=(1920,1080) if '1080p' in path.name else (2560,1440)
        assert (v['width'],v['height'])==expected and v['r_frame_rate']=='24/1' and int(v['nb_frames'])==528
        assert abs(float(v['duration'])-22)<.001 and abs(float(a['duration'])-22)<.05 and a['sample_rate']=='48000'
        subprocess.run(['ffmpeg','-v','error','-nostdin','-xerror','-i',str(path),'-f','null','-'],check=True,capture_output=True)
        outputs.append({'file':path.name,'frames':528,'decode':'pass','canvas':expected,'duration_sec':22,'sha256':sha(path)})
    assert len(outputs)==3
    native=[];sr=[]
    for shot in edit['segments']:
        if shot['id'] in ('S07','END'):continue
        receipt_path=OUT/'sr'/(shot.get('sr_take',shot['id']+'-sr-v3')+'.json');r=json.loads(receipt_path.read_text(encoding='utf-8'))
        assert r['status']=='complete' and r['params']['neural_scale']==2 and r['model']=='RealESRGAN_x2plus'
        assert r['frames']==shot['frames'] and sha(ROOT/r['input'])==r['input_sha256']
        assert sha(receipt_path.with_suffix('.mp4'))==r['sha256']
        assert r['source_picture']==[1280,704] and r['neural_picture']==[2560,1408]
        sr.append({'shot_id':shot['id'],'frames':r['frames'],'elapsed_sec':r['elapsed_sec'],'weight_sha256':r['weight_sha256']})
    for f in (OUT/'takes').glob('*-receipt.json'):
        r=json.loads(f.read_text(encoding='utf-8'));name=f.name.replace('-receipt.json','.webm');source=OUT/'takes'/name
        assert r['status']=='complete' and sha(source)==r['sha256'] and sha(ROOT/r['source'])==r['source_sha256']
        p=probe(source);v=next(s for s in p['streams'] if s['codec_type']=='video')
        assert v['width']==1280 and v['height']==704 and v['r_frame_rate']=='24/1'
        assert r['input']['seed'] in (5302,5303,5304,5306)
        native.append({'shot_id':r['shot_id'],'prompt_id':r['prompt_id'],'frames':r['input']['frames'],'elapsed_sec':r['elapsed_sec']})
    assert len(native)==4
    cues=json.loads((OUT/'cue-sheet.json').read_text(encoding='utf-8'));assert len(cues)==7
    for cue in cues:assert 0<=cue['start']<cue['end']<=20
    result={'status':'technical_checks_passed','outputs':outputs,'native_takes':native,'superresolution':sr,'cue_count':len(cues),
        'human_art_approval':False,'commercial_clearance':'unconfirmed','production_deployed':False}
    (PACK/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('PASS three complete films / 528 frames / 22 sec / four native takes / five neural x2 passes / seven cues')

if __name__=='__main__':check()
