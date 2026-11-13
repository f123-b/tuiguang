"""Reuse original authored voices and audio mix with new 24fps edit timing."""
import importlib.util
import json
from pathlib import Path
import shutil

PACK=Path(__file__).parent
spec=importlib.util.spec_from_file_location('assembly',PACK.parent/'finish.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.PACK=PACK;module.OUT=module.ROOT/'.data/short-drama-53';module.FPS=24
if __name__=='__main__':
    voices=module.OUT/'voices';voices.mkdir(parents=True,exist_ok=True)
    for file in (module.ROOT/'.data/short-drama-51/voices').iterdir():
        if file.suffix in ('.wav','.json'):shutil.copy2(file,voices/file.name)
    # The dialogue is locked to the earlier, fully receipted stock-voice production.
    production=json.loads((PACK/'production.json').read_text(encoding='utf-8'))
    previous=json.loads((PACK.parent/'production.json').read_text(encoding='utf-8'))
    production['cues']=previous['cues']
    (PACK/'production.json').write_text(json.dumps(production,ensure_ascii=False,indent=2),encoding='utf-8')
    module.prepare()
