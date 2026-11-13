"""Local ASR evidence, not a claim of human listening or word-perfect narration."""
import json
import os
from pathlib import Path
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
import soundfile as sf
import torch
import scipy.signal
from transformers import WhisperForConditionalGeneration,WhisperProcessor

PACK=Path(__file__).parent;ROOT=PACK.parents[3];OUT=ROOT/'.data/short-drama-53/v4/voices'
if __name__=='__main__':
    torch.set_num_threads(4)
    model_path=ROOT/'.data/musetalk-source/models/whisper'
    processor=WhisperProcessor.from_pretrained(model_path,local_files_only=True)
    model=WhisperForConditionalGeneration.from_pretrained(model_path,local_files_only=True,attn_implementation='eager').eval()
    for path in sorted(OUT.glob('*-master-v2.wav')):
        wav,sr=sf.read(path);wav=scipy.signal.resample_poly(wav,16000,sr)
        data=processor(wav,sampling_rate=16000,return_tensors='pt',return_attention_mask=True)
        with torch.inference_mode():
            output=model.generate(data.input_features,attention_mask=data.attention_mask,language='zh',task='transcribe',forced_decoder_ids=None,return_timestamps=True,
                return_token_timestamps=True,return_dict_in_generate=True,num_frames=min(3000,len(wav)//160),max_new_tokens=256)
        result=processor.tokenizer.decode(output.sequences[0],skip_special_tokens=True,output_offsets=True)
        result.update(token_ids=output.sequences[0].tolist(),token_timestamps=output.token_timestamps[0].tolist(),
            model='openai/whisper-tiny',revision='169d4a4341b33bc18d8881c4b69c2e104e1cc0af',
            warning='Tiny ASR may misrecognize Mandarin; no human listening approval')
        target=path.with_name(path.stem+'-asr.json');target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(path.stem,str(result['text']).encode('ascii','backslashreplace').decode(),flush=True)
