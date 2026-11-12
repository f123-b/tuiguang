"""One explicitly named local acting take, durable before the only submit."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'services/api'))
from dotenv import load_dotenv
from filelock import FileLock
from creator import wan_comfy

PACK = Path(__file__).parent
OUT = ROOT/'.data/short-drama-51/takes'

def save(path, value):
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    temp.replace(path)

def run(shot, name):
    OUT.mkdir(parents=True,exist_ok=True)
    target=OUT/(name+'.webm'); receipt_path=OUT/(name+'-receipt.json')
    client=wan_comfy.Client()
    try:
        if receipt_path.exists():
            receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
            if receipt['status']=='complete':
                assert hashlib.sha256(target.read_bytes()).hexdigest()==receipt['sha256']
                print('Existing take verified',name,flush=True);return
            if not receipt.get('prompt_id'):
                raise RuntimeError('Unknown submission: inspect queue/history; never resubmit automatically')
            if receipt['status']=='error': raise RuntimeError('Preserve failed take; use explicit new take name')
        else:
            source=PACK/'assets'/shot['reference']
            identifier=uuid.uuid4().hex
            data=dict(style='realistic',prompt=shot['prompt'],seed=5101,width=1280,height=704,frames=shot['frames'])
            assert data['frames'] in (49,73,97,121)
            image=client.upload(identifier,source.read_bytes())
            graph=wan_comfy.workflow(data,image,identifier)
            graph['model']['inputs']['weight_dtype']='fp8_e4m3fn'
            graph['decode']={'class_type':'VAEDecodeTiled','inputs':{'samples':['sample',0],'vae':['vae',0],
                'tile_size':512,'overlap':64,'temporal_size':32,'temporal_overlap':8}}
            graph['negative']['inputs']['text']+=', third person, extra phone, floating objects, face morphing, background deformation, slow motion, camera cut'
            receipt=dict(trace_id=uuid.uuid4().hex,creator_run_id=None,content_id=None,video_project_id=None,
                shot_id=shot['id'],render_job_id=None,job_id=identifier,provider_request_id=None,
                status='prepared',source=str(source.relative_to(ROOT)),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                input=data,model=wan_comfy.snapshot(),workflow_version='action_drama_fp8_tiled@1',graph=graph,
                started_at=time.time(),metrics_before=client.metrics())
            save(receipt_path,receipt)
            receipt['status']='submission_pending';save(receipt_path,receipt)
            receipt['prompt_id']=client.submit(graph,identifier)
            receipt['provider_request_id']=receipt['prompt_id'];receipt['status']='submitted';save(receipt_path,receipt)
            print('Submitted',name,receipt['prompt_id'],flush=True)
        while True:
            history=client.history(receipt['prompt_id'])
            if history:
                save(OUT/(name+'-history.json'),history)
                if history.get('status',{}).get('status_str')=='error':
                    receipt['status']='error';save(receipt_path,receipt);raise RuntimeError('Known failed take preserved')
                if history.get('status',{}).get('completed'):
                    client.download(history['outputs']['save']['images'][0],target,receipt['job_id'])
                    receipt.update(status='complete',elapsed_sec=time.time()-receipt['started_at'],
                        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),metrics_after=client.metrics())
                    save(receipt_path,receipt)
                    print('Complete',name,round(receipt['elapsed_sec'],1),flush=True);return
            time.sleep(10)
    finally:
        client.free_models();client.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('shot');parser.add_argument('name');args=parser.parse_args()
    script=json.loads((PACK/'production.json').read_text(encoding='utf-8'))
    shot=next(s for s in script['shots'] if s['id']==args.shot)
    load_dotenv(ROOT/'.env')
    with FileLock(str(ROOT/'.data/qwen-model/.inference.lock'),timeout=7200):run(shot,args.name)
