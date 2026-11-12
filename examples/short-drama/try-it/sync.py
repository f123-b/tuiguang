"""Offline fictional-actor lip-sync experiment, using pinned upstream MuseTalk.

Explicit manually selected face ROI + optical flow replace upstream DWpose/S3FD.
No claim of identical upstream end-to-end behavior. Never applies to real people.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'.data/musetalk-source'
OUT=ROOT/'.data/short-drama-51/sync'
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1')
sys.path.insert(0,str(SOURCE))
import cv2
import numpy as np
import torch
from filelock import FileLock
from transformers import WhisperModel
from musetalk.models.vae import VAE
from musetalk.models.unet import UNet, PositionalEncoding
from musetalk.utils.audio_processor import AudioProcessor
from musetalk.utils.blending import get_image
from musetalk.utils.face_parsing import FaceParsing
from musetalk.utils.face_parsing.model import BiSeNet

class LocalFaceParsing(FaceParsing):
    def model_init(self):
        directory=SOURCE/'models/face-parse-bisent'
        proof=json.loads((ROOT/'.data/short-drama-51/resnet-conversion.json').read_text(encoding='utf-8'))
        weights=directory/'resnet18-weights-only.pth'
        assert sha(weights)==proof['converted_sha256'] and proof['all_tensor_values_equal']
        net=BiSeNet(str(weights)).cuda()
        net.load_state_dict(torch.load(directory/'79999_iter.pth',map_location='cuda:0',weights_only=True))
        return net.eval()

def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(8*1024**2),b''):digest.update(chunk)
    return digest.hexdigest()

def run(args):
    OUT.mkdir(parents=True,exist_ok=True)
    target=OUT/(args.name+'.mp4');receipt_path=OUT/(args.name+'.json')
    if target.exists() or receipt_path.exists():raise RuntimeError('Preserve existing experiment; use explicit new take name')
    assert subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD'],text=True).strip()=='0a89dec45a0192b824e3cf4daf96c239440c5ed8'
    records=json.loads((ROOT/'.data/short-drama-51/sync-models.json').read_text(encoding='utf-8'))
    for record in records:
        for f in record['files']:
            assert f['status']=='verified' and sha(ROOT/f['path'])==f['sha256']
    video=Path(args.video).resolve();audio=Path(args.audio).resolve()
    assert video.is_relative_to(ROOT) and audio.is_relative_to(ROOT)
    receipt={'status':'prepared','source':str(video.relative_to(ROOT)),'source_sha256':sha(video),
        'audio':str(audio.relative_to(ROOT)),'audio_sha256':sha(audio),'source_revision':'0a89dec45a0192b824e3cf4daf96c239440c5ed8',
        'models':records,'initial_bbox':args.bbox,'tracking':'manual_ROI_optical_flow@1','fps':25,'seed':5101,
        'fictional_actor':True,'human_review':'pending','workflow_version':'offline_musetalk_trial@1','source_in_sec':args.start_sec}
    receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    os.chdir(SOURCE)
    torch.set_num_threads(4);torch.manual_seed(5101)
    cap=cv2.VideoCapture(str(video));source_fps=cap.get(cv2.CAP_PROP_FPS)
    frames=[]
    while True:
        ok,frame=cap.read()
        if not ok:break
        frames.append(frame)
    cap.release();assert frames
    w,h=frames[0].shape[1],frames[0].shape[0]
    x1,y1,x2,y2=args.bbox;assert 0<=x1<x2<=w and 0<=y1<y2<=h
    boxes=[];last=cv2.cvtColor(frames[0],cv2.COLOR_BGR2GRAY);bbox=np.array(args.bbox,dtype=float)
    if args.boxes:
        sequence=(ROOT/args.boxes).resolve();assert sequence.is_relative_to(ROOT)
        measured=json.loads(sequence.read_text(encoding='utf-8'))
        assert measured['source_sha256']==sha(video) and measured['frames']==len(frames)
        boxes=[tuple(box) for box in measured['boxes']]
        assert len(boxes)==len(frames)
        assert all(0<=a<c<=w and 0<=b<d<=h for a,b,c,d in boxes)
        receipt.update(tracking='explicit_measured_ROI_sequence@1',roi_file=str(sequence.relative_to(ROOT)),roi_sha256=sha(sequence))
        receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    for i,frame in enumerate([] if args.boxes else frames):
        grey=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        if i:
            mask=np.zeros_like(last);a,b,c,d=np.round(bbox).astype(int)
            mask[b:max(b+1,b+(d-b)*2//3),a:c]=255
            points=cv2.goodFeaturesToTrack(last,80,.02,5,mask=mask)
            if points is None or len(points)<8:raise RuntimeError('Face tracking lost; inspect source')
            following,status,error=cv2.calcOpticalFlowPyrLK(last,grey,points,None,winSize=(31,31),maxLevel=3)
            valid=(status.reshape(-1)>0)&(error.reshape(-1)<25)
            if valid.sum()<8:raise RuntimeError('Face tracking lost; inspect source')
            delta=np.median((following-points).reshape(-1,2)[valid],axis=0)
            if np.max(np.abs(delta))>12:raise RuntimeError(f'Unexpected face jump at frame {i}, delta={delta.tolist()}; inspect source and ROI')
            bbox+=np.tile(delta,2)
        box=tuple(np.round(bbox).astype(int));assert box[0]>=0 and box[1]>=0 and box[2]<=w and box[3]<=h
        boxes.append(box);last=grey
    with FileLock(str(ROOT/'.data/qwen-model/.inference.lock'),timeout=7200),torch.inference_mode():
        print('Loading verified MuseTalk models',flush=True)
        started=time.monotonic();device='cuda:0';dtype=torch.float16
        vae=VAE(model_path='models/sd-vae',use_float16=True)
        unet=UNet(unet_config='models/musetalkV15/musetalk.json',model_path='models/musetalkV15/unet.pth',use_float16=True,device=device)
        pe=PositionalEncoding().half().to(device)
        processor=AudioProcessor(feature_extractor_path='models/whisper')
        whisper=WhisperModel.from_pretrained('models/whisper',local_files_only=True).to(device=device,dtype=dtype).eval()
        features,length=processor.get_audio_feature(str(audio),weight_dtype=dtype)
        chunks=processor.get_whisper_chunk(features,device,dtype,whisper,length,fps=25)
        del whisper;torch.cuda.empty_cache()
        parser=LocalFaceParsing(left_cheek_width=90,right_cheek_width=90)
        writer=cv2.VideoWriter(str(OUT/(args.name+'-silent.mp4')),cv2.VideoWriter_fourcc(*'mp4v'),25,(w,h))
        assert writer.isOpened()
        frame_indices=[];crop_boxes=[]
        for index in range(len(chunks)):
            source_index=round((index/25+args.start_sec)*source_fps)
            if source_index>=len(frames):
                raise RuntimeError('Audio longer than source; do not loop performance silently')
            frame=frames[source_index];box=boxes[source_index];a,b,c,d=box
            crop=cv2.resize(frame[b:d,a:c],(256,256),interpolation=cv2.INTER_LANCZOS4)
            latent=vae.get_latents_for_unet(crop).to(device=device,dtype=dtype)
            conditioning=pe(chunks[index:index+1].to(device=device,dtype=dtype))
            predicted=unet.model(latent,torch.tensor([0],device=device),encoder_hidden_states=conditioning).sample
            decoded=vae.decode_latents(predicted)[0]
            face=cv2.resize(decoded,(c-a,d-b),interpolation=cv2.INTER_LANCZOS4)
            writer.write(get_image(frame,face,box,mode='jaw',fp=parser))
            frame_indices.append(source_index);crop_boxes.append([int(z) for z in box])
            if index%25==0:print('Lip frames',index,'/',len(chunks),flush=True)
        writer.release()
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-n','-i',str(OUT/(args.name+'-silent.mp4')),
            '-i',str(audio),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-crf','17','-preset','medium','-pix_fmt','yuv420p',
            '-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart',str(target)],check=True)
        receipt.update(status='complete',frames=len(chunks),frame_indices=frame_indices,crop_boxes=crop_boxes,
            elapsed_sec=round(time.monotonic()-started,2),sha256=sha(target),output=str(target.relative_to(ROOT)),
            peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated())
        receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
        print('Lip-sync experiment complete',len(chunks),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('name');ap.add_argument('video');ap.add_argument('audio')
    ap.add_argument('--bbox',required=True,type=lambda s:[int(x) for x in s.split(',')]);ap.add_argument('--boxes');ap.add_argument('--start-sec',type=float,default=0);args=ap.parse_args()
    try:run(args)
    except Exception as exc:
        receipt=OUT/(args.name+'.json')
        if receipt.exists():
            data=json.loads(receipt.read_text(encoding='utf-8'))
            if data.get('status')=='prepared':
                data.update(status='error',error_type=type(exc).__name__)
                receipt.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        raise
