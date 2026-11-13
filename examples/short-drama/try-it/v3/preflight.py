"""Production contract: references must exist before downstream completion is claimed."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

PACK=Path(__file__).parent

def check():
    data=json.loads((PACK/'production.json').read_text(encoding='utf-8'))
    assert data['human_art_approval'] is False
    refs=[c['reference'] for c in data['characters']]+[data['scene']['reference']]
    for s in data['shots']:
        assert s['purpose'] and s['start'] if 'start' in s else s['purpose']
        if s.get('reference'):
            assert s['prompt'] and s['lens'] and s['eyeline'] and s['focus']
            refs.append(s['reference'])
    for name in refs:
        path=PACK/'assets'/name
        assert path.exists(),f'Missing production reference: {name}'
        raw=path.read_bytes();assert raw[:8]==b'\x89PNG\r\n\x1a\n'
        w,h=struct.unpack('>II',raw[16:24]);assert w>=1280 and h>=704,(name,w,h)
    frozen=PACK/'reference-hashes.json'
    if frozen.exists():
        records=json.loads(frozen.read_text(encoding='utf-8'))
        assert {r['file'] for r in records}==set(refs)
        for r in records:assert hashlib.sha256((PACK/'assets'/r['file']).read_bytes()).hexdigest()==r['sha256']
    print('PASS production references, causal shot coverage, prompts, dimensions:',len(refs))

if __name__=='__main__':check()
