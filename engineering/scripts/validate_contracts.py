#!/usr/bin/env python3
"""Basic local structural check for the sample engineering kit; not a full CI gate."""
import json
from pathlib import Path
BASE=Path(__file__).resolve().parents[2]
def check():
    needed=['AGENTS.md','PROJECT_STATUS.md','docs/architecture/MODULE_MAP.md','docs/architecture/CONTRACTS.md','engineering/contracts/error_codes.json']
    for p in needed:
        assert (BASE/p).exists(), f"Missing {p}"
    contracts=BASE/'engineering/contracts'
    for path in sorted(contracts.glob('*.json')):
        obj=json.loads(path.read_text(encoding='utf-8'))
        assert isinstance(obj,dict) and obj, path
        if path.name.endswith('.schema.json'):
            assert obj.get('$schema') and obj.get('required'),path
    catalog=json.loads((contracts/'error_codes.json').read_text(encoding='utf-8'))
    for code,v in catalog['codes'].items():
        assert code.upper()==code and 'owner' in v and 'retryable' in v and 'user_message' in v,code
    print('工程包基础结构检查通过：这不代表真实产品的 CI、运行、兼容或安全已通过')
if __name__=='__main__':check()
