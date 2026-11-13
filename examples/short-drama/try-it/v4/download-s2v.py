"""Pinned official, resumable free model downloads; never invokes remote code."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import time
os.environ.update(HF_HUB_DISABLE_TELEMETRY='1',HF_HUB_DISABLE_XET='1')
from huggingface_hub import hf_hub_download

PACK=Path(__file__).parent;ROOT=PACK.parents[3]
REVISION='ee6f4a40737a995bf5818954cfce6d59443b0f04'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(8*1024**2),b''):h.update(block)
    return h.hexdigest()
def download(item):
    name=item['rfilename'];expected=item['lfs']['sha256']
    target=ROOT/'.data/wan22-models'/name.removeprefix('split_files/')
    if target.exists():assert sha(target)==expected;return {'file':name,'path':target.relative_to(ROOT).as_posix(),'sha256':expected,'bytes':target.stat().st_size,'status':'verified_existing'}
    started=time.monotonic()
    for attempt in range(3):
        try:
            cached=Path(hf_hub_download('Comfy-Org/Wan_2.2_ComfyUI_Repackaged',name,revision=REVISION,
                local_dir=str(ROOT/'.data/s2v-download'),etag_timeout=60))
            break
        except Exception:
            if attempt==2:raise
    assert cached.stat().st_size==item['size'] and sha(cached)==expected
    target.parent.mkdir(parents=True,exist_ok=True);os.link(cached,target)
    print('Verified',target.name,item['size'],flush=True)
    return {'file':name,'path':target.relative_to(ROOT).as_posix(),'sha256':expected,'bytes':item['size'],'elapsed_sec':time.monotonic()-started,'status':'verified'}
if __name__=='__main__':
    metadata=json.loads((ROOT/'.data/short-drama-53/s2v/model-metadata.json').read_text(encoding='utf-8-sig'))
    assert metadata['revision']==REVISION and len(metadata['files'])==3
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:records=list(pool.map(download,metadata['files']))
    (PACK/'s2v-models.json').write_text(json.dumps({'revision':REVISION,'model_card_license':metadata['license'],'files':records},ensure_ascii=False,indent=2),encoding='utf-8')
