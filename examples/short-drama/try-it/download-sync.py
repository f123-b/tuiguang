"""Download only the official MuseTalk inference subset, freeze revisions and hashes.

No source scripts, test media, face detector or training packages are executed.
Weights stay ignored locally. This is an independent film experiment.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import time
from huggingface_hub import HfApi, hf_hub_download

ROOT = Path(__file__).resolve().parents[3]
DEST = ROOT / '.data/musetalk-source/models'
OUT = ROOT / '.data/short-drama-51'
SOURCES = [
    ('TMElyralab/MuseTalk', '', ['musetalkV15/musetalk.json','musetalkV15/unet.pth']),
    ('stabilityai/sd-vae-ft-mse', 'sd-vae', ['config.json','diffusion_pytorch_model.bin']),
    ('openai/whisper-tiny', 'whisper', ['config.json','pytorch_model.bin','preprocessor_config.json']),
    ('ManyOtherFunctions/face-parse-bisent', 'face-parse-bisent', ['79999_iter.pth','resnet18-5c106cde.pth']),
]

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    api = HfApi()
    receipt = OUT / 'sync-models.json'
    records = json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else []
    jobs = []
    if not records:
        for repo, subdir, names in SOURCES:
            info = api.model_info(repo, files_metadata=True)
            files = {f.rfilename:f for f in info.siblings}
            record = {'repo':repo,'revision':info.sha,'files':[],
                      'license':getattr(info.card_data,'license',None)}
            records.append(record)
            for name in names:
                entry = files[name]
                lfs = entry.lfs
                record['files'].append({'name':name,'bytes':entry.size,'expected_sha256':lfs.sha256 if lfs else None})
    for record, (repo, subdir, names) in zip(records,SOURCES):
        assert repo == record['repo'] and names == [f['name'] for f in record['files']]
        for item in record['files']:
            jobs.append((repo,record['revision'],subdir,item['name'],item))
    receipt.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    def download(job):
        repo, revision, subdir, name, item = job
        for attempt in range(3):
            try:
                path = Path(hf_hub_download(repo, name, revision=revision, local_dir=DEST/subdir))
                break
            except Exception as exc:
                print('Download interrupted',repo,name,type(exc).__name__,attempt+1,flush=True)
                if attempt == 2: raise
                time.sleep(2)
        hasher=hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda:stream.read(8*1024**2),b''):hasher.update(chunk)
        digest=hasher.hexdigest()
        assert path.stat().st_size == item['bytes']
        if item['expected_sha256']: assert digest == item['expected_sha256']
        item.update(sha256=digest,path=str(path.relative_to(ROOT)),status='verified')
        print('Verified',repo,name,flush=True)
    with ThreadPoolExecutor(max_workers=3) as executor:
        list(executor.map(download,jobs))
    receipt.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    print('All lip-sync inputs verified',flush=True)

if __name__ == '__main__': main()
