"""One durable, audio-conditioned Wan S2V take. No independent lipsync overlay."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
ROOT=Path(__file__).resolve().parents[4];PACK=Path(__file__).parent;OUT=ROOT/'.data/short-drama-53/v4/takes'
sys.path.insert(0,str(ROOT/'services/api'))
from creator import wan_comfy
from dotenv import load_dotenv
from filelock import FileLock
from contracts import validate_actor_sources,validate_audio_graph

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024**2),b''):h.update(block)
    return h.hexdigest()
def save(path,data):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)
SHOTS={
 'S01':('s04-close-v3.png','The young man in an olive overshirt is mildly puzzled and speaks naturally in sync with the audio. He glances from the black smartphone in his right hand toward screen right, briefly raising the phone a little. He keeps holding the same phone. One man only, stable face, fixed camera, warm daylight.'),
 'S02':('s02-close-v3.png','The seated woman in a charcoal cardigan speaks naturally in sync with the audio, gently lowers her raised right hand, and looks slightly up to screen left. She calmly acknowledges her mistake, relaxed ordinary conversation. Only one woman, same face and hair, stable camera, warm daylight.'),
 'S04':('s04-close-v3.png','The young man in an olive overshirt speaks naturally in sync with the audio, with a friendly small smile. His right hand holds one black smartphone steadily at chest height. He looks to screen right and slightly downward. Head and shoulders move only subtly, no repeated nodding. Only one man, same face and hair, fixed camera, warm daylight.'),
 'S06':('s06-close-v3.png','The seated woman in a charcoal cardigan listens then speaks briefly in sync with the audio and smiles gently. Her eyes look up to screen left. Her head stays nearly still, no repeated head shaking. Only one woman, same bob haircut, fixed camera, warm daylight.'),
 'LIN':('s02-close-v3.png','The seated woman in a charcoal cardigan speaks conversationally in sync with the audio. At first she gently lowers her raised right palm, then keeps both hands relaxed below frame. She looks slightly up to screen left throughout. Her expression is calm and apologetic, then she gives a small warm self-deprecating smile at the very end. Natural minimal head and shoulder motion, no repeated nodding or shaking, no exaggerated face. Only one woman, same bob haircut and wardrobe, stable warm daylight, fixed camera.')}

def run(sid,name):
    OUT.mkdir(parents=True,exist_ok=True);receipt_path=OUT/(name+'.json');client=wan_comfy.Client()
    try:
        if receipt_path.exists():
            r=json.loads(receipt_path.read_text(encoding='utf-8'))
            if r['status']=='complete':assert sha(OUT/(name+'.webm'))==r['sha256'];print('Existing S2V verified');return
            if r['status']=='error' or not r.get('prompt_id'):raise RuntimeError('Preserve failed/unknown take; never resubmit automatically')
        else:
            ref,prompt=SHOTS[sid];source=PACK.parent/'v3/assets'/ref
            locks=json.loads((PACK/'audio-lock.json').read_text(encoding='utf-8'))
            validate_actor_sources([x for x in locks if x.get('role')])
            lock=next(x for x in locks if x.get('shot_id')==sid);audio=ROOT/lock['path'];frames=round(lock['duration_sec']*16)
            assert sha(audio)==lock['sha256'] and (frames-1)%4==0
            if frames>77:raise ValueError('Measured 8GB profile: split audio before generating over77 frames')
            models=json.loads((PACK/'s2v-models.json').read_text(encoding='utf-8'))
            for f in models['files']:assert sha(ROOT/f['path'])==f['sha256']
            identifier=uuid.uuid4().hex;image=client.upload(identifier,source.read_bytes())
            audio_name='creator_audio_'+identifier+'.wav';audio_input=ROOT/'.data/comfy-wan-input'/audio_name
            assert not audio_input.exists();shutil.copy2(audio,audio_input);assert sha(audio_input)==sha(audio)
            graph={
              'model':{'class_type':'UNETLoader','inputs':{'unet_name':'wan2.2_s2v_14B_fp8_scaled.safetensors','weight_dtype':'default'}},
              'shift':{'class_type':'ModelSamplingSD3','inputs':{'model':['model',0],'shift':8}},
              'clip':{'class_type':'CLIPLoader','inputs':{'clip_name':'umt5_xxl_fp8_e4m3fn_scaled.safetensors','type':'wan','device':'cpu'}},
              'vae':{'class_type':'VAELoader','inputs':{'vae_name':'wan_2.1_vae.safetensors'}},
              'image':{'class_type':'LoadImage','inputs':{'image':image}},
              'audio':{'class_type':'LoadAudio','inputs':{'audio':audio_name}},
              'audio_model':{'class_type':'AudioEncoderLoader','inputs':{'audio_encoder_name':'wav2vec2_large_english_fp16.safetensors'}},
              'audio_features':{'class_type':'AudioEncoderEncode','inputs':{'audio_encoder':['audio_model',0],'audio':['audio',0]}},
              'positive':{'class_type':'CLIPTextEncode','inputs':{'clip':['clip',0],'text':prompt}},
              'negative':{'class_type':'CLIPTextEncode','inputs':{'clip':['clip',0],'text':'blurred face, deformed mouth, extra person, duplicated phone, extra fingers, exaggerated gestures, repeated head shaking, camera cut, subtitles, text, watermark'}},
              'condition':{'class_type':'WanSoundImageToVideo','inputs':{'positive':['positive',0],'negative':['negative',0],'vae':['vae',0],
                'width':832,'height':480,'length':frames,'batch_size':1,'audio_encoder_output':['audio_features',0],'ref_image':['image',0]}},
              'sample':{'class_type':'KSampler','inputs':{'model':['shift',0],'seed':5402 if sid.startswith('LIN') else 5404+int(sid[1:]),'steps':20,'cfg':6,
                'sampler_name':'uni_pc','scheduler':'simple','positive':['condition',0],'negative':['condition',1],'latent_image':['condition',2],'denoise':1}},
              'decode':{'class_type':'VAEDecodeTiled','inputs':{'samples':['sample',0],'vae':['vae',0],'tile_size':512,'overlap':64,'temporal_size':32,'temporal_overlap':8}},
              'save':{'class_type':'SaveWEBM','inputs':{'images':['decode',0],'filename_prefix':'creator_jobs/'+identifier,'codec':'vp9','fps':16,'crf':16}}
            }
            validate_audio_graph(graph,frames/16)
            r={'status':'prepared','trace_id':uuid.uuid4().hex,'creator_run_id':None,'content_id':None,'video_project_id':None,'shot_id':sid,'render_job_id':None,
                'job_id':identifier,'workflow_version':'audio_drama_s2v@1','source':source.relative_to(ROOT).as_posix(),'source_sha256':sha(source),
                'audio':audio.relative_to(ROOT).as_posix(),'audio_sha256':sha(audio),'models':models,'engine_revision':'0decb39ee5b5e17c200334589fc317dbbe98310e',
                'graph':graph,'fps':16,'native_canvas':[832,480],'native_frames':frames,'started_at':time.time(),'human_art_approval':False,'metrics_before':client.metrics()}
            save(receipt_path,r);r['status']='submission_pending';save(receipt_path,r)
            r['prompt_id']=client.submit(graph,identifier);r['status']='submitted';save(receipt_path,r);print('Submitted S2V',sid,r['prompt_id'],flush=True)
        while True:
            h=client.history(r['prompt_id'])
            if h:
                save(OUT/(name+'-history.json'),h)
                if h.get('status',{}).get('status_str')=='error':
                    r['status']='error';save(receipt_path,r);raise RuntimeError('S2V failed, preserved history')
                if h.get('status',{}).get('completed'):
                    target=OUT/(name+'.webm');client.download(h['outputs']['save']['images'][0],target,r['job_id'])
                    r.update(status='complete',sha256=sha(target),elapsed_sec=time.time()-r['started_at'],metrics_after=client.metrics());save(receipt_path,r)
                    film=OUT/(name+'.mp4')
                    subprocess.run(['ffmpeg','-v','error','-nostdin','-n','-i',str(target),'-i',str(ROOT/r['audio']),'-map','0:v:0','-map','1:a:0',
                        '-t',str(r['native_frames']/16),'-c:v','libx264','-crf','16','-c:a','aac','-b:a','192k','-movflags','+faststart',str(film)],check=True)
                    print('S2V complete',sid,round(r['elapsed_sec'],1),flush=True);return
            time.sleep(10)
    finally:client.free_models();client.close()

SHOTS['LIN1']=SHOTS['LIN']
SHOTS['LIN2']=('s06-close-v3.png','The seated woman in a charcoal cardigan speaks calmly and briefly in sync with the audio while looking slightly up to screen left. Her hands stay below frame and shoulders relaxed. She gives a small warm self-deprecating smile near the end after speaking. Minimal natural head motion, no repeated shaking or nodding, one woman only, same bob haircut and wardrobe, stable daylight, fixed camera.')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('shot',choices=SHOTS);ap.add_argument('name');args=ap.parse_args();load_dotenv(ROOT/'.env')
    with FileLock(str(ROOT/'.data/qwen-model/.inference.lock'),timeout=7200):run(args.shot,args.name)
