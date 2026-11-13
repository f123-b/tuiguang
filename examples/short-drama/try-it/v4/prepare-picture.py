"""Prepare one shot in its native spatial resolution, preserving its audio clock."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

PACK=Path(__file__).parent;ROOT=PACK.parents[3];OUT=ROOT/'.data/short-drama-53/v4/prepared'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(sid):
    edit=json.loads((PACK/'edit.json').read_text(encoding='utf-8'));s=next(s for s in edit['segments'] if s['id']==sid)
    assert not s.get('real_ui') and sid!='END'
    source=ROOT/s['source'];assert source.exists(),'Expected generated performance is still missing'
    OUT.mkdir(parents=True,exist_ok=True);target=OUT/(s.get('picture_take',sid+'-picture-v4-cut2')+'.mp4');receipt=target.with_suffix('.json')
    if receipt.exists():
        r=json.loads(receipt.read_text(encoding='utf-8'));assert r['source_sha256']==sha(source) and sha(target)==r['sha256']
        assert r['frames']==s['frames'] and r['source_in_sec']==s.get('in_sec',0) and r.get('source_crop')==s.get('source_crop')
        print('Prepared shot verified',sid);return
    assert not target.exists()
    interpolation='minterpolate=fps=24:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1' if s['source_fps']==16 else 'fps=24'
    crop=s.get('source_crop');prefix=f'crop={crop[0]}:{crop[1]}:{crop[2]}:{crop[3]},' if crop else ''
    filters=prefix+f'tpad=stop_mode=clone:stop_duration=0.20,{interpolation},trim=end_frame={s["frames"]},setpts=PTS-STARTPTS,setsar=1'
    subprocess.run(['ffmpeg','-v','error','-nostdin','-n','-threads','4','-ss',str(s.get('in_sec',0)),'-i',str(source),
        '-vf',filters,'-frames:v',str(s['frames']),'-an','-c:v','libx264','-crf','14','-preset','medium','-pix_fmt','yuv420p',str(target)],check=True)
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(target)],encoding='utf-8'))['streams'][0]
    assert int(info['nb_frames'])==s['frames'] and info['r_frame_rate']=='24/1'
    receipt.write_text(json.dumps({'status':'complete','source':s['source'],'source_sha256':sha(source),'source_in_sec':s.get('in_sec',0),
        'source_fps':s['source_fps'],'fps':24,'frames':s['frames'],'source_canvas':[info['width'],info['height']],
        'spatial_resize':False,'source_crop':crop,'interpolation':interpolation,'sha256':sha(target),'edit_sha256':sha(PACK/'edit.json'),'human_art_approval':False},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Prepared',sid,s['frames'],'frames, native spatial resolution',flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('shot');a=ap.parse_args();run(a.shot)
