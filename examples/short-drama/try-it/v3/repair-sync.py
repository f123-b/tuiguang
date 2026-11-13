"""Explicit tighter face windows after comparing rejected v3 sync against native."""
import hashlib
import json
from pathlib import Path
import subprocess

PACK=Path(__file__).parent;ROOT=PACK.parents[3]
jobs=[('S04','s04-close-v3','521,171,785,471',0,[521,171,264,264]),
      ('S02','s02-close-v3','570,107,854,427',0,[570,107,284,284]),
      ('S06','s06-close-v3','581,111,867,437',1.3,[581,111,286,286])]
records=[]
for sid,take,box,start,detected in jobs:
    source=ROOT/'.data/short-drama-53/takes'/(take+'.webm')
    records.append({'shot_id':sid,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'detector':'OpenCV 4.10 Haar frontalface_default; first frame; scaleFactor1.1/minNeighbors5/minSize120',
        'detected_xywh':detected,'crop_xyxy':[int(x) for x in box.split(',')],'bottom_extension_px':int(box.split(',')[3])-int(box.split(',')[1])-detected[3],
        'selection':'manual lower-face coverage after detector; not automatic artistic approval'})
(PACK/'roi-lock.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
python=str(ROOT/'.data/musetalk-runtime/Scripts/python.exe')
for sid,take,box,start,detected in jobs:
    subprocess.run([python,str(PACK/'sync.py'),sid+'-lips-v4',str(ROOT/'.data/short-drama-53/takes'/(take+'.webm')),
        str(ROOT/'.data/short-drama-53/voices'/(sid+'-timed.wav')),'--bbox',box,'--start-sec',str(start)],check=True)
    subprocess.run([python,str(PACK/'preserve-detail.py'),sid+'-lips-v4',sid+'-detail-v4'],check=True)
