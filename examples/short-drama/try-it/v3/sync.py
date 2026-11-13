"""Explicit new fictional-actor sync takes; keeps original bodies and all failed takes."""
import argparse
import importlib.util
from pathlib import Path

PACK=Path(__file__).parent
spec=importlib.util.spec_from_file_location('sync_runner',PACK.parent/'sync.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
runner.OUT=runner.ROOT/'.data/short-drama-53/sync'
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('name');ap.add_argument('video');ap.add_argument('audio')
    ap.add_argument('--bbox',required=True,type=lambda x:[int(z) for z in x.split(',')]);ap.add_argument('--boxes');ap.add_argument('--start-sec',type=float,default=0)
    args=ap.parse_args()
    try:runner.run(args)
    except Exception as exc:
        receipt=runner.OUT/(args.name+'.json')
        if receipt.exists():
            data=runner.json.loads(receipt.read_text(encoding='utf-8'))
            if data.get('status')=='prepared':
                data.update(status='error',error_type=type(exc).__name__);receipt.write_text(runner.json.dumps(data,indent=2),encoding='utf-8')
        raise
