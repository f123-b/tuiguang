"""Keep native eyes/hair/skin outside a soft mouth ellipse after local lipsync."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import cv2
import numpy as np

PACK=Path(__file__).parent;ROOT=PACK.parents[3];OUT=ROOT/'.data/short-drama-53/sync'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def run(name,output):
    source=OUT/(name+'.mp4');receipt=json.loads(source.with_suffix('.json').read_text(encoding='utf-8'))
    assert receipt['status']=='complete' and sha(source)==receipt['sha256']
    native=ROOT/receipt['source'];assert sha(native)==receipt['source_sha256']
    target=OUT/(output+'.mp4');assert not target.exists(),'Preserve prior output'
    cap=cv2.VideoCapture(str(native));frames=[]
    while True:
        ok,frame=cap.read()
        if not ok:break
        frames.append(frame)
    cap.release();assert frames
    cap=cv2.VideoCapture(str(source));h,w=frames[0].shape[:2]
    encoder=subprocess.Popen(['ffmpeg','-v','error','-nostdin','-n','-threads','4','-f','rawvideo','-pix_fmt','bgr24',
        '-s',f'{w}x{h}','-r','25','-i','pipe:0','-an','-c:v','libx264','-crf','14','-preset','medium','-pix_fmt','yuv420p',str(target)],stdin=subprocess.PIPE)
    for i,index in enumerate(receipt['frame_indices']):
        ok,lip=cap.read();assert ok
        native_frame=frames[index]
        a,b,c,d=receipt['crop_boxes'][i];yy,xx=np.mgrid[b:d,a:c]
        # Only the mouth and immediate chin: retain native eyes, eyebrows, hair and shoulders.
        radius=((xx-(a+(c-a)*.50))/((c-a)*.36))**2+((yy-(b+(d-b)*.72))/((d-b)*.21))**2
        mask=np.clip((1-radius)*2,0,1).astype(np.float32)
        mask=cv2.GaussianBlur(mask,(0,0),5)[:,:,None]
        composed=native_frame.copy()
        composed[b:d,a:c]=np.round(native_frame[b:d,a:c]*(1-mask)+lip[b:d,a:c]*mask).astype(np.uint8)
        encoder.stdin.write(composed.tobytes())
    cap.release();encoder.stdin.close();assert encoder.wait()==0
    target.with_suffix('.json').write_text(json.dumps({'status':'complete','workflow':'native_detail_mouth_blend@1',
        'source':str(native.relative_to(ROOT)),'source_sha256':sha(native),'lip_source':str(source.relative_to(ROOT)),
        'lip_sha256':sha(source),'sync_receipt_sha256':sha(source.with_suffix('.json')),'sha256':sha(target),
        'frames':len(receipt['frame_indices']),'fps':25,'human_art_approval':False},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Native detail retained outside mouth',output,flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('name');ap.add_argument('output');args=ap.parse_args();run(args.name,args.output)
