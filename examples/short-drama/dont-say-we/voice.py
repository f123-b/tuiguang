"""Record an original fictional dialogue with local stock voices; no voice clone."""
import hashlib
import json
import os
from pathlib import Path
import time

os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",HF_HUB_DISABLE_TELEMETRY="1")
import soundfile as sf
import torch
from filelock import FileLock
from qwen_tts import Qwen3TTSModel

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/".data/short-drama-49/voices"
MODEL=ROOT/".data/qwen-model"
SCRIPT=json.loads(Path(__file__).with_name("production.json").read_text(encoding="utf-8"))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    receipts=[]
    torch.set_num_threads(4)
    with FileLock(str(MODEL/".inference.lock"),timeout=600):
        model=Qwen3TTSModel.from_pretrained(str(MODEL),device_map="cuda:0",dtype=torch.bfloat16,attn_implementation="sdpa",local_files_only=True)
        for index,cue in enumerate(SCRIPT["cues"]):
            path=OUT/(cue["id"]+".wav")
            if path.exists():
                raise RuntimeError("Preserve recorded takes; use an explicit new take directory")
            seed=1201+index
            torch.manual_seed(seed)
            started=time.monotonic()
            waves,sr=model.generate_custom_voice(text=cue["text"],language="Chinese",speaker=cue["speaker"],instruct=cue["direction"],do_sample=True,temperature=.75,top_p=.9,max_new_tokens=512)
            sf.write(path,waves[0],sr,subtype="PCM_16")
            receipts.append({**cue,"seed":seed,"sample_rate":sr,"samples":len(waves[0]),"duration_sec":len(waves[0])/sr,"elapsed_sec":round(time.monotonic()-started,2),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"model":"Qwen3-TTS-12Hz-1.7B-CustomVoice","model_revision":"0c0e3051f131929182e2c023b9537f8b1c68adfe"})
            (OUT/"receipts.json").write_text(json.dumps(receipts,ensure_ascii=False,indent=2),encoding="utf-8")
            print(cue["id"],round(receipts[-1]["duration_sec"],2),flush=True)
    print("Dialogue recorded",len(receipts),flush=True)

if __name__=="__main__":main()
