"""Explicit face ROI measurements for S06, not an automatic failure fallback."""
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'.data/short-drama-51'
source=OUT/'takes/s06-smile-v1.webm'
cascade=Path(cv2.data.haarcascades)/'haarcascade_frontalface_alt2.xml'
# OpenCV FileStorage on Windows cannot read the Unicode workspace path directly.
storage=cv2.FileStorage(cascade.read_text(),cv2.FILE_STORAGE_READ|cv2.FILE_STORAGE_MEMORY)
detector=cv2.CascadeClassifier();assert detector.read(storage.getFirstTopLevelNode())
cap=cv2.VideoCapture(str(source));measured=[];i=0;known=[]
while True:
    ok,frame=cap.read()
    if not ok:break
    candidates=detector.detectMultiScale(cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY),1.1,5,minSize=(120,120),maxSize=(240,240))
    candidates=[r for r in candidates if abs(r[0]+r[2]/2-770)<160 and 10<r[1]<230]
    if candidates:
        x,y,w,h=min(candidates,key=lambda r:abs(r[0]+r[2]/2-770))
        measured.append([float(x)-.10*w,float(y)-.25*h,float(x)+1.10*w,float(y)+1.15*h]);known.append(i)
    else:measured.append(None)
    i+=1
cap.release();assert len(known)>=len(measured)*.8
points=np.array([measured[j] for j in known])
filled=np.stack([np.interp(np.arange(len(measured)),known,points[:,j]) for j in range(4)],axis=1)
smooth=np.stack([np.median(filled[max(0,j-2):min(len(filled),j+3)],axis=0) for j in range(len(filled))])
boxes=np.round(smooth).astype(int);assert (boxes>=0).all() and (boxes[:,2]<=1280).all() and (boxes[:,3]<=704).all()
target=OUT/'s06-measured-roi-v1.json'
assert not target.exists(),'Preserve measurements'
receipt={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'method':'opencv_Haar_actor_region+5frame_median@1',
    'detector_sha256':hashlib.sha256(cascade.read_bytes()).hexdigest(),'opencv_version':cv2.__version__,
    'frames':len(measured),'detected_frames':len(known),'missing_detection_frames':[j for j in range(len(measured)) if j not in known],
    'max_coordinate_step':int(np.abs(np.diff(boxes,axis=0)).max()),'boxes':boxes.tolist(),'user_review':False}
target.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print({k:v for k,v in receipt.items() if k!='boxes'},flush=True)
