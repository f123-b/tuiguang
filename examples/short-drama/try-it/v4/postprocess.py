"""Wait for known local receipts, then finish without resubmitting any generation."""
import json
from pathlib import Path
import subprocess
import sys
import time

PACK=Path(__file__).parent;ROOT=PACK.parents[3];OUT=ROOT/'.data/short-drama-53/v4'
if __name__=='__main__':
    edit=json.loads((PACK/'edit.json').read_text(encoding='utf-8'))
    for shot in edit['segments']:
        if shot['id'] in ('S07','END'):continue
        source=ROOT/shot['source']
        if source.parent==OUT/'takes':
            receipt=source.with_suffix('.json');announced=False
            while True:
                if receipt.exists():
                    r=json.loads(receipt.read_text(encoding='utf-8'))
                    if r['status']=='error':raise RuntimeError('Known failed performance; do not silently retry')
                    if r['status']=='complete' and source.exists():break
                if not announced:print('Waiting for explicitly queued performance',shot['id'],flush=True);announced=True
                time.sleep(10)
        subprocess.run([sys.executable,str(PACK/'prepare-picture.py'),shot['id']],check=True)
    for shot in edit['segments']:
        if shot['id'] in ('S07','END'):continue
        subprocess.run([str(ROOT/'.data/video-gen-runtime/Scripts/python.exe'),str(PACK/'neural-sr.py'),shot['id']],check=True)
    subprocess.run([str(ROOT/'.data/qwen-clean-runtime/Scripts/python.exe'),str(PACK/'finish.py')],check=True)
    print('New films exist, pending technical and artistic inspection',flush=True)
