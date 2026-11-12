"""Convert only a byte-identical official PyTorch checkpoint from legacy tar.

The upstream parser uses this old ResNet. Current torch cannot weights-only load
legacy tar. Download the official release independently, compare full SHA256,
then explicitly deserialize that trusted release once into a weights-only zip.
No pickle from a user/upload or arbitrary path is accepted.
"""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen
import torch

ROOT=Path(__file__).resolve().parents[3]
DIRECTORY=ROOT/'.data/musetalk-source/models/face-parse-bisent'
URL='https://download.pytorch.org/models/resnet18-5c106cde.pth'

def main():
    receipt=json.loads((ROOT/'.data/short-drama-51/sync-models.json').read_text(encoding='utf-8'))
    item=next(f for r in receipt for f in r['files'] if f['name']=='resnet18-5c106cde.pth')
    original=DIRECTORY/'resnet18-5c106cde.pth'
    assert hashlib.sha256(original.read_bytes()).hexdigest()==item['sha256']
    official=DIRECTORY/'resnet18-official.pth'
    if not official.exists():
        with urlopen(URL,timeout=60) as response, official.with_suffix('.part').open('wb') as stream:
            while chunk:=response.read(1024**2):stream.write(chunk)
        official.with_suffix('.part').replace(official)
    digest=hashlib.sha256(official.read_bytes()).hexdigest()
    assert digest==item['sha256'] and digest.startswith('5c106cde')
    target=DIRECTORY/'resnet18-weights-only.pth'
    if target.exists():raise RuntimeError('Preserve existing conversion')
    state=torch.load(official,map_location='cpu',weights_only=False)
    assert isinstance(state,dict) and all(isinstance(k,str) and torch.is_tensor(v) for k,v in state.items())
    torch.save(state,target)
    verified=torch.load(target,map_location='cpu',weights_only=True)
    assert state.keys()==verified.keys() and all(torch.equal(v,verified[k]) for k,v in state.items())
    proof={'official_url':URL,'sha256':digest,'converted_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'tensor_count':len(state),'all_tensor_values_equal':True,'reason':'legacy tar cannot weights-only load in torch2.9'}
    (ROOT/'.data/short-drama-51/resnet-conversion.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    print('Official ResNet verified; exact tensor conversion complete',len(state),flush=True)

if __name__=='__main__':main()
