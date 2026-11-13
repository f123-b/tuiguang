"""One continuous performance per fictional role, cut later without changing identity."""
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
ROLES=[
 {'role':'chen','speaker':'dylan','seed':5401,'text':'算了，你来。……找到了。你早放这儿不就好了。',
  'direction':'普通话青年男性，和熟悉的朋友面对面小声聊天，清楚、松弛、自然，不播音，不广告。保持同一个音色和正常语速，每秒约四个汉字，不急促。第一句话有一点困惑，两组话之间停一秒，后面找到入口后轻轻带笑。不要夸张表演。'},
 {'role':'lin','speaker':'serena','seed':5402,'text':'等一下。……不是你不会用，是我藏得太深了。……欢迎页，先拿掉。……再试试。……对哦。',
  'direction':'普通话年轻成年女性，和熟悉朋友轻声聊天，清楚自然、温和松弛，不播音，不广告，不撒娇。全程保持同一个音色和正常语速，每秒约四个汉字，各句之间停一秒。先叫住对方，再诚恳自嘲承认设计问题，边操作边随口说话，最后短短带笑回应。不要夸张表演。'}]
if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True);torch.set_num_threads(4)
    with FileLock(str(ROOT/'.data/qwen-model/.inference.lock'),timeout=7200):
        model=Qwen3TTSModel.from_pretrained(str(ROOT/'.data/qwen-model'),device_map='cuda:0',dtype=torch.bfloat16,attn_implementation='sdpa',local_files_only=True)
        records=[]
        for role in ROLES:
            path=OUT/(role['role']+'-master-v1.wav');receipt=path.with_suffix('.json')
            assert not path.exists() and not receipt.exists(),'Preserve previous voice master'
            torch.manual_seed(role['seed']);started=time.monotonic()
            waves,sr=model.generate_custom_voice(text=role['text'],speaker=role['speaker'],language='Chinese',instruct=role['direction'],
                do_sample=True,temperature=.55,top_p=.85,subtalker_temperature=.55,max_new_tokens=2048)
            sf.write(path,waves[0],sr,subtype='PCM_16')
            record={**role,'model':'Qwen3-TTS-12Hz-1.7B-CustomVoice','model_revision':'0c0e3051f131929182e2c023b9537f8b1c68adfe',
                'sample_rate':sr,'samples':len(waves[0]),'duration_sec':len(waves[0])/sr,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'elapsed_sec':round(time.monotonic()-started,2),'human_listening_review':False}
            receipt.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8');records.append(record)
            print(role['role'],'master seconds',record['duration_sec'],flush=True)
        (PACK/'voice-masters.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
