"""Finish after explicit SR and native-detail passes; only local deliverables."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

PACK=Path(__file__).parent;ROOT=PACK.parents[3];OUT=ROOT/'.data/short-drama-53'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args):subprocess.run(['ffmpeg','-v','error','-nostdin','-n','-threads','4',*args],check=True,cwd=OUT)

def superresolve():
    edit=json.loads((PACK/'edit.json').read_text(encoding='utf-8'))
    for shot in edit['segments']:
        if shot['id'] in ('S07','END'):continue
        subprocess.run([str(ROOT/'.data/video-gen-runtime/Scripts/python.exe'),str(PACK/'superresolve.py'),
            str(ROOT/shot['source']),str(OUT/'sr'/(shot.get('sr_take',shot['id']+'-sr-v3')+'.mp4')),'--frames',str(shot['frames']),'--shot',shot['id']],check=True)

def finish():
    edit=json.loads((PACK/'edit.json').read_text(encoding='utf-8'))
    assert edit['human_art_approval'] is False
    manifest_path=PACK/'edit-manifest.json'
    if manifest_path.exists():
        previous=json.loads(manifest_path.read_text(encoding='utf-8'))
        assert previous['edit_sha256']==sha(PACK/'edit.json'),'Edit changed; use a new explicit mastering version'
        for record in previous['outputs']:assert sha(ROOT/record['path'])==record['sha256']
        print('Existing final films verified; preserved',flush=True);return
    total=sum(s['frames'] for s in edit['segments']);assert total==528
    folder=OUT/'master';folder.mkdir(exist_ok=True)
    records=[];native_files=[];sr_files=[]
    for shot in edit['segments']:
        sid=shot['id'];frames=shot['frames'];dest=folder/(sid+'-sr.mp4');native=folder/(sid+'-native.mp4')
        if sid not in ('S07','END'):
            sr=OUT/'sr'/(shot.get('sr_take',sid+'-sr-v3')+'.mp4');receipt=json.loads(sr.with_suffix('.json').read_text(encoding='utf-8'))
            assert receipt['status']=='complete' and sha(sr)==receipt['sha256'] and receipt['frames']==frames
            source=ROOT/shot['source'];assert sha(source)==receipt['input_sha256']
            # Native baseline uses the identical source, framing and time samples, only Lanczos scaling.
            if not native.exists():run(['-i',str(source),'-vf',f'tpad=stop_mode=clone:stop_duration=0.08,fps=24,scale=1280:704:flags=lanczos,pad=1280:720:0:8:black,scale=2560:1440:flags=lanczos,setsar=1,trim=end_frame={frames},setpts=PTS-STARTPTS',
                '-frames:v',str(frames),'-an','-c:v','libx264','-crf','14','-preset','medium','-pix_fmt','yuv420p',str(native)])
            sr=sr.resolve();records.append({'shot_id':sid,'frames':frames,'source':shot['source'],'source_sha256':sha(source),'sr':str(sr.relative_to(ROOT)),'sr_sha256':sha(sr),'spatial_crop':None})
        elif sid=='S07':
            source=ROOT/shot['source'];c=shot['crop']
            if not dest.exists():run(['-ss',str(shot['in_sec']),'-i',str(source),'-vf',f'fps=24,crop={c[0]}:{c[1]}:{c[2]}:{c[3]},scale=2560:1440:flags=lanczos,setsar=1',
                '-frames:v',str(frames),'-an','-c:v','libx264','-crf','14','-preset','medium','-pix_fmt','yuv420p',str(dest)])
            sr=native=dest;records.append({'shot_id':sid,'source':shot['source'],'source_sha256':sha(source),'frames':frames,'ai_sr':False,'real_ui':True,'notice':'真实界面虚构数据，UI文字不经神经重绘；原录屏裁切832×468，非原生2K文字'})
        else:
            if not dest.exists():run(['-loop','1','-i',str(OUT/'end-card.png'),'-vf','fps=24,scale=2560:1440:flags=lanczos,setsar=1,fade=t=in:d=0.18,fade=t=out:st=1.65:d=0.35',
                '-frames:v',str(frames),'-an','-c:v','libx264','-crf','14','-preset','medium','-pix_fmt','yuv420p',str(dest)])
            sr=native=dest
        sr_files.append(sr);native_files.append(native)
    for mode,files in [('2K超分',sr_files),('原片对照',native_files)]:
        listing=folder/(mode+'.txt');listing.write_text('\n'.join("file '"+p.as_posix()+"'" for p in files),encoding='utf-8')
        target=OUT/('你来试试-v3-'+mode+'.mp4')
        if not target.exists():run(['-f','concat','-safe','0','-i',str(listing),'-i',str(OUT/'mix.wav'),'-vf','ass=film.ass',
            '-map','0:v:0','-map','1:a:0','-frames:v',str(total),'-t','22','-c:v','libx264','-crf','16','-preset','medium','-pix_fmt','yuv420p',
            '-af','apad=whole_dur=22,atrim=duration=22','-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',str(target)])
    target=OUT/'你来试试-v3-1080p.mp4'
    if not target.exists():run(['-i',str(OUT/'你来试试-v3-2K超分.mp4'),'-vf','scale=1920:1080:flags=lanczos','-c:v','libx264','-crf','17','-preset','medium','-pix_fmt','yuv420p',
        '-c:a','copy','-movflags','+faststart',str(target)])
    outputs=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in OUT.glob('你来试试-v3-*.mp4')]
    (PACK/'edit-manifest.json').write_text(json.dumps({'version':'try_it_edit@3','edit_sha256':sha(PACK/'edit.json'),'frames':528,'fps':24,'duration_sec':22,'shots':records,'outputs':outputs,
        'human_art_approval':False,'deployed':False,'motion_interpolation':False,'boundary_hold_max_sec':.08},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Finished native baseline, 2K SR master and 1080p delivery',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--sr',action='store_true');args=ap.parse_args()
    superresolve() if args.sr else finish()
