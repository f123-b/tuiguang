"""Reuse the durable, one-submit runner with a separate versioned production pack."""
import argparse
import importlib.util
import json
from pathlib import Path

PACK=Path(__file__).parent
spec=importlib.util.spec_from_file_location('take_runner',PACK.parent/'generate.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
runner.PACK=PACK
runner.OUT=runner.ROOT/'.data/short-drama-53/takes'

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('shot');ap.add_argument('take');args=ap.parse_args()
    production=json.loads((PACK/'production.json').read_text(encoding='utf-8'))
    shot=next(s for s in production['shots'] if s['id']==args.shot)
    runner.load_dotenv(runner.ROOT/'.env')
    with runner.FileLock(str(runner.ROOT/'.data/qwen-model/.inference.lock'),timeout=7200):
        runner.run(shot,args.take)
