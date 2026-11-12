"""Short, conversational stock-voice takes; no narration or voice clone."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import time
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1')
import soundfile as sf
import torch
from filelock import FileLock
from qwen_tts import Qwen3TTSModel

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'.data/short-drama-51/voices'
MODEL=ROOT/'.data/qwen-model'

def main(only=None):
    OUT.mkdir(parents=True,exist_ok=True)
    script=json.loads(Path(__file__).with_name('production.json').read_text(encoding='utf-8'))
    torch.set_num_threads(4)
    with FileLock(str(MODEL/'.inference.lock'),timeout=7200):
        model=Qwen3TTSModel.from_pretrained(str(MODEL),device_map='cuda:0',dtype=torch.bfloat16,
            attn_implementation='sdpa',local_files_only=True)
        records=[]
        for i,cue in enumerate(script['cues']):
            path=OUT/(cue['id']+'.wav');receipt=OUT/(cue['id']+'.json')
            if receipt.exists():
                record=json.loads(receipt.read_text(encoding='utf-8'))
                assert record['text']==cue['text'] and hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256']
            else:
                if only and cue['id']!=only:raise RuntimeError('Missing required earlier voice take')
                if path.exists(): raise RuntimeError('Unacknowledged output: preserve it; use explicit new directory')
                seed=5101+i;torch.manual_seed(seed);started=time.monotonic()
                waves,sr=model.generate_custom_voice(text=cue['text'],language='Chinese',speaker=cue['speaker'],
                    instruct=cue['direction'],do_sample=True,temperature=.75,top_p=.9,max_new_tokens=512)
                sf.write(path,waves[0],sr,subtype='PCM_16')
                record={**cue,'seed':seed,'sample_rate':sr,'samples':len(waves[0]),'duration_sec':len(waves[0])/sr,
                    'elapsed_sec':round(time.monotonic()-started,2),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                    'model':'Qwen3-TTS-12Hz-1.7B-CustomVoice','model_revision':'0c0e3051f131929182e2c023b9537f8b1c68adfe'}
                receipt.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
            records.append(record)
            (OUT/'receipts.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
            print(cue['id'],record['duration_sec'],flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--only');main(ap.parse_args().only)
