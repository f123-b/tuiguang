"""Native-size neural x2 after the final time edit, before UI and subtitles."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import time
import numpy as np
import torch
from filelock import FileLock
from spandrel import ModelLoader

PACK=Path(__file__).parent;ROOT=PACK.parents[3];OUT=ROOT/'.data/short-drama-53/v4'
spec=importlib.util.spec_from_file_location('sr_infer',PACK.parent/'v3/superresolve.py')
sr=importlib.util.module_from_spec(spec);spec.loader.exec_module(sr)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(sid):
    s=next(s for s in json.loads((PACK/'edit.json').read_text(encoding='utf-8'))['segments'] if s['id']==sid)
    source=OUT/'prepared'/(s.get('picture_take',sid+'-picture-v4-cut2')+'.mp4');prep=json.loads(source.with_suffix('.json').read_text(encoding='utf-8'))
    assert prep['status']=='complete' and sha(source)==prep['sha256']
    folder=OUT/'sr';folder.mkdir(exist_ok=True);target=folder/(s.get('sr_take',sid+'-x2-v4')+'.mp4');receipt=target.with_suffix('.json')
    if receipt.exists():
        r=json.loads(receipt.read_text(encoding='utf-8'));assert r['status']=='complete' and r['source_sha256']==sha(source) and sha(target)==r['sha256']
        print('SR verified',sid,flush=True);return
    assert not target.exists()
    assert sha(sr.WEIGHT)==sr.EXPECTED
    w,h=prep['source_canvas'];count=prep['frames']
    r={'status':'prepared','shot_id':sid,'workflow':'native_size_rrdb_x2@2','source':source.relative_to(ROOT).as_posix(),'source_sha256':sha(source),
        'native_picture':[w,h],'neural_picture':[w*2,h*2],'frames':count,'fps':24,'weight_sha256':sr.EXPECTED,
        'params':{'tile':384,'context_pad':24,'precision':'fp16','face_replacement':False},'human_art_approval':False}
    sr.save(receipt,r)
    with FileLock(str(ROOT/'.data/qwen-model/.inference.lock'),timeout=14400),torch.inference_mode():
        started=time.monotonic();torch.set_num_threads(4)
        model=ModelLoader().load_from_state_dict(torch.load(sr.WEIGHT,map_location='cpu',weights_only=True)['params_ema']).eval().half().cuda()
        dec=subprocess.Popen(['ffmpeg','-v','error','-nostdin','-i',str(source),'-frames:v',str(count),'-pix_fmt','rgb24','-f','rawvideo','pipe:1'],stdout=subprocess.PIPE)
        enc=subprocess.Popen(['ffmpeg','-v','error','-nostdin','-n','-threads','4','-f','rawvideo','-pix_fmt','rgb24','-s',f'{w*2}x{h*2}',
            '-r','24','-i','pipe:0','-an','-c:v','libx264','-crf','14','-preset','medium','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],stdin=subprocess.PIPE)
        try:
            for i in range(count):
                raw=dec.stdout.read(w*h*3);assert len(raw)==w*h*3
                enc.stdin.write(sr.infer(model,np.frombuffer(raw,np.uint8).reshape(h,w,3)).tobytes())
                if i%48==0:print('Neural x2',sid,i,'/',count,flush=True)
            dec.stdout.close();enc.stdin.close();assert dec.wait()==0 and enc.wait()==0
        except BaseException as exc:
            for p in (dec,enc):
                if p.poll() is None:p.terminate()
            r.update(status='error',error_type=type(exc).__name__);sr.save(receipt,r);raise
        r.update(status='complete',sha256=sha(target),elapsed_sec=round(time.monotonic()-started,2));sr.save(receipt,r)
        print('Neural x2 complete',sid,flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('shot');a=ap.parse_args();run(a.shot)
