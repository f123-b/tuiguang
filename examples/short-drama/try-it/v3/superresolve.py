"""Framewise RRDB x2. Does not inpaint faces, interpolate time or invent an approval.

Works only on local video frames, not the image-generation asset workflow.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import uuid

import numpy as np
import torch
from filelock import FileLock
from spandrel import ModelLoader

PACK=Path(__file__).parent
ROOT=PACK.parents[3]
WEIGHT=ROOT/'.data/sr-models/RealESRGAN_x2plus.pth'
EXPECTED='49fafd45f8fd7aa8d31ab2a22d14d91b536c34494a5cfe31eb5d89c2fa266abb'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,data):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)

def infer(model,frame,tile=384,pad=24):
    h,w=frame.shape[:2]
    tensor=torch.from_numpy(frame.copy()).permute(2,0,1).unsqueeze(0).to('cuda',torch.float16)/255
    result=torch.empty((1,3,h*2,w*2),device='cpu',dtype=torch.float32)
    for y in range(0,h,tile):
        for x in range(0,w,tile):
            y1=max(0,y-pad);x1=max(0,x-pad);y2=min(h,y+tile+pad);x2=min(w,x+tile+pad)
            output=model(tensor[:,:,y1:y2,x1:x2]).float().cpu()
            th=min(tile,h-y);tw=min(tile,w-x)
            result[:,:,y*2:(y+th)*2,x*2:(x+tw)*2]=output[:,:,(y-y1)*2:(y-y1+th)*2,(x-x1)*2:(x-x1+tw)*2]
    return (result[0].permute(1,2,0).clamp(0,1).numpy()*255).round().astype(np.uint8)

def run(source,target,frames,shot_id,limit=None):
    source=source.resolve();target=target.resolve()
    assert source.is_relative_to(ROOT) and target.is_relative_to(ROOT)
    assert source.exists() and sha(WEIGHT)==EXPECTED
    target.parent.mkdir(parents=True,exist_ok=True)
    receipt_path=target.with_suffix('.json')
    if receipt_path.exists():
        old=json.loads(receipt_path.read_text(encoding='utf-8'))
        if old['status']=='complete':
            assert sha(target)==old['sha256'] and sha(source)==old['input_sha256']
            print('Existing neural SR verified',shot_id,flush=True);return
        raise RuntimeError('Incomplete prior SR preserved; choose a new explicit output version')
    assert not target.exists(),'Preserve existing output'
    count=min(frames,limit) if limit else frames
    receipt=dict(status='prepared',workflow='rrdb_x2_tiled@1',trace_id=uuid.uuid4().hex,creator_run_id=None,content_id=None,
        video_project_id=None,shot_id=shot_id,render_job_id=None,input=str(source.relative_to(ROOT)),input_sha256=sha(source),
        model='RealESRGAN_x2plus',weight_sha256=EXPECTED,weight_bytes=WEIGHT.stat().st_size,
        source_url='https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth',
        license='BSD-3-Clause, project declaration; no blanket commercial clearance',spandrel='0.4.2',torch=torch.__version__,
        params={'neural_scale':2,'tile':384,'context_pad':24,'precision':'fp16','face_restore':False,'temporal_model':False,'fps':24,'max_boundary_hold_sec':0.08},
        source_picture=[1280,704],neural_picture=[2560,1408],output_canvas=[2560,1440],requested_frames=count,human_art_approval=False)
    save(receipt_path,receipt)
    started=time.monotonic();torch.set_num_threads(4)
    dec=enc=None
    with FileLock(str(ROOT/'.data/qwen-model/.inference.lock'),timeout=7200),torch.inference_mode():
        state=torch.load(WEIGHT,map_location='cpu',weights_only=True)
        model=ModelLoader().load_from_state_dict(state['params_ema']).eval().half().cuda()
        assert model.scale==2
        info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',str(source)],text=True))
        assert float(info['format']['duration'])+.08>=count/24,'Source cannot cover edit; no long frozen padding'
        dec=subprocess.Popen(['ffmpeg','-v','error','-nostdin','-i',str(source),'-vf','tpad=stop_mode=clone:stop_duration=0.08,fps=24,scale=1280:704:flags=lanczos',
            '-frames:v',str(count),'-f','rawvideo','-pix_fmt','rgb24','pipe:1'],stdout=subprocess.PIPE)
        enc=subprocess.Popen(['ffmpeg','-v','error','-nostdin','-n','-threads','4','-f','rawvideo','-pix_fmt','rgb24',
            '-s','2560x1408','-r','24','-i','pipe:0','-vf','pad=2560:1440:0:16:black,setsar=1','-an',
            '-c:v','libx264','-preset','medium','-crf','14','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],stdin=subprocess.PIPE)
        try:
            for i in range(count):
                raw=dec.stdout.read(1280*704*3)
                assert len(raw)==1280*704*3,f'Source too short at frame {i}; never loop silently'
                result=infer(model,np.frombuffer(raw,np.uint8).reshape(704,1280,3))
                enc.stdin.write(result.tobytes())
                if i%24==0:print('Neural x2',shot_id,i,'/',count,'seconds',round(time.monotonic()-started,1),flush=True)
            dec.stdout.close();enc.stdin.close();assert dec.wait()==0 and enc.wait()==0
        except BaseException as exc:
            for process in (dec,enc):
                if process is not None and process.poll() is None:process.terminate()
            receipt.update(status='error',error_type=type(exc).__name__);save(receipt_path,receipt);raise
        receipt.update(status='complete',sha256=sha(target),frames=count,elapsed_sec=round(time.monotonic()-started,2),
            peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated())
        save(receipt_path,receipt)
        print('SR complete',shot_id,count,flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('source',type=Path);ap.add_argument('target',type=Path)
    ap.add_argument('--frames',type=int,required=True);ap.add_argument('--shot',required=True);ap.add_argument('--limit',type=int);args=ap.parse_args()
    run(args.source,args.target,args.frames,args.shot,args.limit)
