"""Mix frozen actor audio once; insert real UI and subtitles only after neural SR."""
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.signal import resample_poly
import soundfile as sf

PACK=Path(__file__).parent;ROOT=PACK.parents[3];OUT=ROOT/'.data/short-drama-53/v4';FPS=24
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ff(args):subprocess.run(['ffmpeg','-v','error','-nostdin','-n','-threads','4',*args],check=True,cwd=OUT)
def stamp(t):
    ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
def ass(t):
    n=round(t*100);return f'{n//360000}:{n//6000%60:02}:{n//100%60:02}.{n%100:02}'
def prepare_audio(edit):
    n=sum(s['frames'] for s in edit['segments'])*2000;voice=np.zeros(n,np.float32);cursor=0;cues=[];sources=[]
    for s in edit['segments']:
        count=s['frames']*2000
        if s.get('audio'):
            source=ROOT/s['audio'];audio,sr=sf.read(source);assert sr==24000 and audio.ndim==1
            start=round(s.get('audio_in_sec',0)*sr);selected=audio[start:start+round(count/2)]
            selected=resample_poly(selected,2,1).astype(np.float32);voice[cursor:cursor+min(count,len(selected))]+=selected[:count]
            sources.append({'shot_id':s['id'],'path':s['audio'],'sha256':sha(source),'source_in_sec':s.get('audio_in_sec',0),
                'timeline_start_sec':cursor/48000,'no_independent_tempo_or_offset_change':True})
        for a,b,text in s.get('cues',[]):
            assert 0<=a<b<=s['frames']/24
            cues.append({'shot_id':s['id'],'text':text,'start':cursor/48000+a,'end':cursor/48000+b})
        cursor+=count
    assert len(cues)==7
    rng=np.random.default_rng(54);room=rng.normal(size=n).astype(np.float32)*.0004
    room=np.convolve(room,np.ones(17)/17,mode='same').astype(np.float32)
    # One restrained original tap timed to the operation insert; no stock song or random effects.
    operation_start=sum(s['frames'] for s in edit['segments'][:2])/24
    at=round((operation_start+1.2)*48000);x=np.arange(2400)/48000
    room[at:at+len(x)]+=rng.normal(size=len(x))*.006*np.exp(-x*100)
    room[-12000:]*=np.linspace(1,0,12000)
    premix=OUT/'voice-and-room-v4.wav';assert not premix.exists();sf.write(premix,np.stack([voice+room,voice+room],axis=1),48000,subtype='PCM_24')
    ff(['-i',str(premix),'-af','highpass=f=75,lowpass=f=12000,loudnorm=I=-16:TP=-1.5:LRA=8','-ar','48000','-c:a','pcm_s24le',str(OUT/'mix-v4.wav')])
    header='''[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Microsoft YaHei,44,&H00FFFFFF,&H00FFFFFF,&H00181818,&H70181818,0,0,0,0,100,100,0,0,3,2,0,2,80,80,54,1
Style: AI,Microsoft YaHei,22,&H40F1EFE7,&H00FFFFFF,&H70282828,&H60282828,0,0,0,0,100,100,0,0,1,1,0,9,64,64,48,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    duration=n/48000
    lines=[f'Dialogue: 0,0:00:00.00,{ass(duration-1.75)},AI,,0,0,0,,AI剧情演绎']
    ui_start=sum(s['frames'] for s in edit['segments'][:-2])/24
    lines.append(f'Dialogue: 0,{ass(ui_start)},{ass(duration-1.75)},AI,,0,0,0,,{{\\an7\\pos(64,48)}}真实界面 · 虚构练习')
    for c in cues:lines.append(f"Dialogue: 1,{ass(c['start'])},{ass(c['end'])},Default,,0,0,0,,{c['text']}")
    (OUT/'film-v4.ass').write_text(header+'\n'.join(lines)+'\n',encoding='utf-8')
    (OUT/'你来试试-v4.srt').write_text('\n'.join(f"{i+1}\n{stamp(c['start'])} --> {stamp(c['end'])}\n{c['text']}\n" for i,c in enumerate(cues)),encoding='utf-8')
    card=Image.new('RGB',(1920,1080),'#20251f');draw=ImageDraw.Draw(card)
    for y,text,size,color in [(435,'你来试试',76,'#efece1'),(550,'有招 · 记下做过的选择',34,'#c1c6af'),(912,'AI剧情演绎 · 合成声音 · 虚构项目',22,'#89917e')]:
        draw.text((960,y),text,font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',size),fill=color,anchor='mm')
    card.save(OUT/'end-v4.png')
    (PACK/'audio-edit-receipt.json').write_text(json.dumps({'frames':n//2000,'duration_sec':duration,'sources':sources,'cues':cues,
        'mix_sha256':sha(OUT/'mix-v4.wav'),'voice_master_count':2,'speaker_changes_within_role':False,'human_listening_review':False},ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    edit=json.loads((PACK/'edit.json').read_text(encoding='utf-8'));assert not edit['human_art_approval']
    manifest_path=PACK/'edit-manifest.json'
    if manifest_path.exists():
        m=json.loads(manifest_path.read_text(encoding='utf-8'));assert m['edit_sha256']==sha(PACK/'edit.json')
        for r in m['outputs']:assert sha(ROOT/r['path'])==r['sha256']
        print('Existing final v4 films verified');return
    for s in edit['segments']:
        if s['id'] not in ('S07','END'):assert (OUT/'sr'/(s.get('sr_take',s['id']+'-x2-v4')+'.mp4')).exists(),'Neural SR not complete'
    prepare_audio(edit);folder=OUT/'master';folder.mkdir(exist_ok=True);outputs=[];shot_records=[]
    fit='scale=1920:1080:force_original_aspect_ratio=decrease:flags=lanczos,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,setsar=1'
    for mode in ['超分成片','超分前对照']:
        pieces=[]
        for s in edit['segments']:
            sid=s['id'];target=folder/(sid+'-'+mode+'.mp4')
            if sid=='END':
                inputs=['-loop','1','-i',str(OUT/'end-v4.png')];filters='fps=24,fade=t=in:d=0.16,fade=t=out:st=1.4:d=0.35'
            elif sid=='S07':
                c=s['crop'];inputs=['-ss',str(s['in_sec']),'-i',str(ROOT/s['source'])]
                filters=f'fps=24,crop={c[0]}:{c[1]}:{c[2]}:{c[3]},'+fit
            else:
                source=OUT/('sr' if mode=='超分成片' else 'prepared')/((s.get('sr_take',sid+'-x2-v4') if mode=='超分成片' else s.get('picture_take',sid+'-picture-v4-cut2'))+'.mp4')
                receipt=json.loads(source.with_suffix('.json').read_text(encoding='utf-8'));assert receipt['status']=='complete' and sha(source)==receipt['sha256']
                inputs=['-i',str(source)];filters=fit
                if mode=='超分成片':shot_records.append({'shot_id':sid,'source':s['source'],'generated_in_sec':s.get('in_sec',0),'source_crop':s.get('source_crop'),'prepared_sha256':sha(OUT/'prepared'/(s.get('picture_take',sid+'-picture-v4-cut2')+'.mp4')),
                    'sr_sha256':sha(source),'frames':s['frames'],'neural_picture':receipt['neural_picture']})
            if not target.exists():ff([*inputs,'-vf',filters,'-frames:v',str(s['frames']),'-an','-c:v','libx264','-crf','15','-preset','medium','-pix_fmt','yuv420p',str(target)])
            pieces.append(target)
        listing=folder/(mode+'.txt');listing.write_text('\n'.join("file '"+p.as_posix()+"'" for p in pieces),encoding='utf-8')
        frames=sum(s['frames'] for s in edit['segments']);target=OUT/('你来试试-v4-'+mode+'.mp4')
        ff(['-f','concat','-safe','0','-i',str(listing),'-i',str(OUT/'mix-v4.wav'),'-vf','ass=film-v4.ass','-map','0:v:0','-map','1:a:0',
            '-frames:v',str(frames),'-t',str(frames/24),'-c:v','libx264','-crf','16','-preset','medium','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',str(target)])
        outputs.append({'path':target.relative_to(ROOT).as_posix(),'sha256':sha(target),'bytes':target.stat().st_size})
    manifest_path.write_text(json.dumps({'version':edit['version'],'edit_sha256':sha(PACK/'edit.json'),'frames':frames,'fps':24,'duration_sec':frames/24,
        'picture':'1920×1080 delivery; generated native832×480, neural1664×960; operation native1280×704/neural2560×1408, fit without facial crop',
        'shots':shot_records,'outputs':outputs,'human_art_approval':False,'production_deployed':False},ensure_ascii=False,indent=2),encoding='utf-8')
    print('v4 final films',frames,'frames',frames/24,'seconds',flush=True)
if __name__=='__main__':main()
