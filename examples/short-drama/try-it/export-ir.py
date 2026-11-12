"""Validate an independent clip-level IR; never imports or approves an app project."""
import hashlib
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'services/api'))
from creator.schemas import VideoInput
PACK=Path(__file__).parent
OUT=ROOT/'.data/short-drama-51'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main(take):
    edit=json.loads((PACK/'edit.json').read_text(encoding='utf-8'))
    shots=[];assets={}
    for i,s in enumerate(edit['segments']):
        path=OUT/f'edit-{take}-{i:02}.mp4';digest=sha(path);identifier=digest[:32]
        assets[identifier]={'path':str(path.relative_to(ROOT)),'sha256':digest,'scope':'finished independent edited clip; maps to a real authorized asset only on import'}
        shots.append({'shot_id':s['id'],'provider':'ffmpeg_media','kind':'montage','asset_id':identifier,
            'duration_frames':s['frames'],'design':{'layout':'cinema','motion':'still'}})
    mix=OUT/'mix.wav';digest=sha(mix);mix_id=digest[:32]
    assets[mix_id]={'path':str(mix.relative_to(ROOT)),'sha256':digest}
    cues=json.loads((OUT/'cue-sheet.json').read_text(encoding='utf-8'))
    ir=VideoInput(brand_id='offline-youzhao-51',name='你来试试·独立短剧',width=1920,height=1080,shots=shots,
        audio_tracks=[{'track_id':'final-mix','asset_id':mix_id,'role':'voiceover','start_frame':0,'duration_frames':sum(s['frames'] for s in edit['segments'])}],
        subtitles=[{'cue_id':c['id'],'start_frame':round(c['start']*30),'end_frame':round(c['end']*30),'text':c['text']} for c in cues],preview_required=True).model_dump()
    ir.update(schema_version='1.1',offline_assets=assets,offline_exact_edit_manifest=f'edit-{take}.json',
        offline_scope='Clip-level edit only, body generation and lipsync provenance in takes/sync receipts. Not imported to app. Map real brand/assets then render a new preview and obtain user review.',user_approval=False)
    (OUT/'video-project-ir.json').write_text(json.dumps(ir,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Offline IR1.1 DTO valid',len(shots),'shots; not imported or approved',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--take',default='v2');main(parser.parse_args().take)
