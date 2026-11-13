"""Plain-text, bounded actor performances; long repeated takes are explicitly rejected."""
import hashlib
import json
import os
from pathlib import Path
import time
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1')
import soundfile as sf
import torch
from filelock import FileLock
from qwen_tts import Qwen3TTSModel

PACK=Path(__file__).parent;ROOT=PACK.parents[3];OUT=ROOT/'.data/short-drama-53/v4/voices'
ROLES=[('chen','dylan',5411,'算了，你来。找到了，你早放这儿不就好了。',12),
       ('lin','serena',5412,'等一下。不是你不会用，是我藏得太深了。欢迎页先拿掉。再试试。对哦。',20)]
if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(4)
    with FileLock(str(ROOT/'.data/qwen-model/.inference.lock'),timeout=7200):
        model=Qwen3TTSModel.from_pretrained(str(ROOT/'.data/qwen-model'),device_map='cuda:0',dtype=torch.bfloat16,attn_implementation='sdpa',local_files_only=True)
        records=[]
        for role,speaker,seed,text,max_seconds in ROLES:
            path=OUT/(role+'-master-v2.wav');assert not path.exists()
            torch.manual_seed(seed);started=time.monotonic()
            direction='普通话，和熟悉朋友面对面自然聊天，清楚、平实、松弛，不急促，不播音，不广告，不夸张。保持一致声线。'
            waves,sr=model.generate_custom_voice(text=text,speaker=speaker,language='Chinese',instruct=direction,
                do_sample=True,temperature=.75,top_p=.9,subtalker_temperature=.9,max_new_tokens=384)
            sf.write(path,waves[0],sr,subtype='PCM_16');seconds=len(waves[0])/sr
            record={'role':role,'speaker':speaker,'seed':seed,'text':text,'direction':direction,'sample_rate':sr,'duration_sec':seconds,
                'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'elapsed_sec':round(time.monotonic()-started,2),
                'model':'Qwen3-TTS-12Hz-1.7B-CustomVoice','model_revision':'0c0e3051f131929182e2c023b9537f8b1c68adfe',
                'generation_params':{'do_sample':True,'temperature':.75,'top_p':.9,'subtalker_temperature':.9,'max_new_tokens':384},
                'status':'duration_checked' if seconds<=max_seconds else 'rejected_duration','human_listening_review':False}
            path.with_suffix('.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
            assert seconds<=max_seconds,'Unusable repeated/overlong voice; preserve take and stop'
            records.append(record);print(role,'seconds',seconds,flush=True)
        (PACK/'voice-masters-v2.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
