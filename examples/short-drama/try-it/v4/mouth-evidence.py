"""Measure mouth motion against the EXACT audio; diagnostics are not a lip-sync rating."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import vision

PACK=Path(__file__).parent;ROOT=PACK.parents[3]
MODEL=ROOT/'.data/face-qa-models/face_landmarker.task'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(video,audio,target):
    assert sha(MODEL)=='64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_streams','-of','json',str(video)],text=True))['streams'][0]
    n,d=info['r_frame_rate'].split('/');fps=float(n)/float(d);w=832;h=round(info['height']/info['width']*w)
    raw=subprocess.check_output(['ffmpeg','-v','error','-nostdin','-i',str(audio),'-ac','1','-ar','16000','-f','f32le','pipe:1'])
    waveform=np.frombuffer(raw,np.float32)
    decoder=subprocess.Popen(['ffmpeg','-v','error','-nostdin','-i',str(video),'-vf',f'scale={w}:{h}','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],stdout=subprocess.PIPE)
    options=vision.FaceLandmarkerOptions(base_options=mp.tasks.BaseOptions(model_asset_buffer=MODEL.read_bytes(),delegate=mp.tasks.BaseOptions.Delegate.CPU),
        running_mode=vision.RunningMode.VIDEO,num_faces=1,output_face_blendshapes=True)
    records=[];missing=0
    with vision.FaceLandmarker.create_from_options(options) as detector:
        i=0
        while True:
            raw=decoder.stdout.read(w*h*3)
            if not raw:break
            assert len(raw)==w*h*3
            frame=np.frombuffer(raw,np.uint8).reshape(h,w,3).copy()
            result=detector.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB,data=frame),round(i/fps*1000))
            begin=round(i/fps*16000);end=round((i+1)/fps*16000);slice=waveform[begin:end]
            rms=float(np.sqrt(np.mean(slice**2))) if len(slice) else 0
            if result.face_landmarks:
                pts=result.face_landmarks[0]
                point=lambda k:np.array([pts[k].x*w,pts[k].y*h])
                opening=float(np.linalg.norm(point(13)-point(14))/max(np.linalg.norm(point(61)-point(291)),1))
                shapes={s.category_name:s.score for s in result.face_blendshapes[0]}
                jaw=float(shapes['jawOpen'])
            else:opening=jaw=None;missing+=1
            records.append({'frame':i,'time_sec':i/fps,'audio_rms':rms,'mouth_open_ratio':opening,'jaw_open':jaw});i+=1
    decoder.stdout.close();assert decoder.wait()==0
    eligible=[r for r in records if r['jaw_open'] is not None]
    leading=[r for r in eligible if r['audio_rms']<.00001]
    proof={'video':str(video),'video_sha256':sha(video),'audio':str(audio),'audio_sha256':sha(audio),'fps':fps,'frames':len(records),
        'missing_faces':missing,'silent_frames':len(leading),'silent_mean_jaw_open':float(np.mean([r['jaw_open'] for r in leading])) if leading else None,
        'model':'MediaPipe FaceLandmarker float16 v1','model_sha256':sha(MODEL),'mediapipe':'0.10.31','delegate':'CPU',
        'interpretation':'Mouth openness is not phoneme accuracy. A smile can be open-mouthed during silence. No automatic artistic pass.',
        'human_art_approval':False,'records':records}
    target.write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8');print('Measured frames',len(records),'missing',missing,flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('video',type=Path);ap.add_argument('audio',type=Path);ap.add_argument('output',type=Path);a=ap.parse_args();run(a.video,a.audio,a.output)
