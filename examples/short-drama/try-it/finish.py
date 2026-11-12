"""Local shot assembly; no app approval, upload or database mutation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import soundfile as sf

ROOT=Path(__file__).resolve().parents[3]
PACK=Path(__file__).parent
OUT=ROOT/'.data/short-drama-51'
FPS=30

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def run(args):subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-threads','4',*args],check=True,cwd=OUT)
def stamp(t,sep=','):
    ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02}{sep}{ms%1000:03}'
def ass(t):
    cs=round(t*100);return f'{cs//360000}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}'

def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    edit=json.loads((PACK/'edit.json').read_text(encoding='utf-8'))
    script=json.loads((PACK/'production.json').read_text(encoding='utf-8'))
    records=json.loads((OUT/'voices/receipts.json').read_text(encoding='utf-8'))
    by_id={r['id']:r for r in records};cues=[];frame=0
    for segment in edit['segments']:
        length=segment['frames']/FPS
        shot=np.zeros((round(length*24000),),dtype=np.float32)
        for name,offset in segment.get('speech',[]):
            r=by_id[name];path=OUT/'voices'/(name+'.wav')
            assert sha(path)==r['sha256'] and next(c['text'] for c in script['cues'] if c['id']==name)==r['text']
            wav,sr=sf.read(path);assert sr==24000 and wav.ndim==1
            start=round(offset*sr);assert start>=0 and start+len(wav)<=len(shot)
            shot[start:start+len(wav)]+=wav
            cues.append({**r,'shot_id':segment['id'],'start':frame/FPS+offset,'end':frame/FPS+offset+r['duration_sec']})
        if segment.get('sync_bbox'):
            sf.write(OUT/'voices'/segment.get('timed_audio',segment['id']+'-timed.wav'),shot,24000,subtype='PCM_16')
        frame+=segment['frames']
    duration=frame/FPS;assert len(cues)==len(script['cues'])==7
    # Original quiet room texture, keyboard/phone Foley and sparse plucked notes.
    sr=48000;n=round(duration*sr);t=np.arange(n)/sr;rng=np.random.default_rng(51)
    noise=rng.normal(size=(n,2)).astype(np.float32)
    room=np.stack([np.convolve(noise[:,ch],np.ones(31)/31,mode='same') for ch in range(2)],axis=1)*.005
    for start in [7.65,7.89,8.10,8.41,8.72,9.02,11.86,12.23]:
        m=round(.075*sr);x=np.arange(m)/sr;k=round(start*sr)
        click=(rng.normal(size=m)*.025+np.sin(x*2*np.pi*880)*.012)*np.exp(-x*70)
        room[k:k+m,0]+=click*.7;room[k:k+m,1]+=click
    for start,freq in [(3.65,220),(7.35,293.66),(13.1,329.63),(17.1,392),(20.7,293.66),(22.6,220)]:
        if start>=duration:continue
        m=min(round(2.2*sr),n-round(start*sr));x=np.arange(m)/sr;k=round(start*sr)
        tone=sum(np.sin(2*np.pi*freq*h*x)*np.exp(-x*(1.4+h*.2))/h**2 for h in range(1,5))
        tone*=.012*(1-np.exp(-x*100))*np.minimum(1,(m/sr-x)/.25)
        room[k:k+m,0]+=tone;room[k:k+m,1]+=tone*.85
    fade=np.minimum(1,t/.2)*np.minimum(1,(duration-t)/.7)
    sf.write(OUT/'original-bed.wav',room*fade[:,None],sr,subtype='PCM_24')
    inputs=['-i',str(OUT/'original-bed.wav')];filters=['[0:a]highpass=f=90,lowpass=f=9500[bed]'];labels=['[bed]']
    for i,cue in enumerate(cues,1):
        inputs+=['-i',str(OUT/'voices'/(cue['id']+'.wav'))]
        delay=round(cue['start']*1000)
        filters.append(f'[{i}:a]highpass=f=85,lowpass=f=11500,loudnorm=I=-19:TP=-3:LRA=9,adelay={delay}|{delay}[v{i}]');labels.append(f'[v{i}]')
    filters.append(''.join(labels)+f'amix=inputs={len(labels)}:normalize=0:duration=longest,atrim=duration={duration},loudnorm=I=-16:TP=-1.5:LRA=9[a]')
    run([*inputs,'-filter_complex',';'.join(filters),'-map','[a]','-ar','48000','-c:a','pcm_s24le',str(OUT/'mix.wav')])
    header='''[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Dialogue,Microsoft YaHei,44,&H00FFFFFF,&H00FFFFFF,&H00181818,&H70181818,0,0,0,0,100,100,0,0,3,2,0,2,80,80,54,1
Style: Note,Microsoft YaHei,26,&H10F1EFE7,&H00FFFFFF,&H70282828,&H60282828,0,0,0,0,100,100,0,0,1,1,0,7,64,64,48,1
Style: AI,Microsoft YaHei,22,&H40F1EFE7,&H00FFFFFF,&H70282828,&H60282828,0,0,0,0,100,100,0,0,1,1,0,9,64,64,48,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    lines=[f'Dialogue: 0,0:00:00.00,{ass(duration-2)},AI,,0,0,0,,AI 剧情演绎',
        'Dialogue: 0,0:00:00.00,0:00:02.20,Note,,0,0,0,,一次试用']
    srt=[]
    for i,c in enumerate(cues,1):
        lines.append(f"Dialogue: 1,{ass(c['start'])},{ass(c['end'])},Dialogue,,0,0,0,,{c['text']}")
        srt.append(f"{i}\n{stamp(c['start'])} --> {stamp(c['end'])}\n{c['text']}\n")
    ui_start=sum(s['frames'] for s in edit['segments'][:-2])/FPS
    lines.append(f'Dialogue: 0,{ass(ui_start)},{ass(duration-2)},Note,,0,0,0,,{{\\an1\\pos(64,1020)}}当天的项目记录 · 虚构练习')
    (OUT/'film.ass').write_text(header+'\n'.join(lines)+'\n',encoding='utf-8')
    (OUT/'你来试试.srt').write_text('\n'.join(srt),encoding='utf-8');save(OUT/'cue-sheet.json',cues)
    card=Image.new('RGB',(1920,1080),'#20251f');d=ImageDraw.Draw(card)
    for y,text,size,color in [(420,'你来试试',76,'#efece1'),(535,'有招 · 记下做过的选择',34,'#c1c6af'),(912,'AI 剧情演绎 · 合成声音 · 虚构项目',22,'#89917e')]:
        d.text((960,y),text,font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',size),fill=color,anchor='mm')
    card.save(OUT/'end-card.png')
    save(OUT/'prepared.json',{'frames':frame,'duration_sec':duration,'cues':len(cues),'edit_sha256':sha(PACK/'edit.json')})
    print('Prepared',frame,duration,flush=True)

def finish(take):
    edit=json.loads((PACK/'edit.json').read_text(encoding='utf-8'))
    assert edit['status']=='takes_inspected_for_edit'
    target=OUT/f'你来试试-{take}.mp4'
    if target.exists():raise RuntimeError('Preserve existing film; choose explicit new edit version')
    sources=[];nframes=0;segment_files=[]
    for i,s in enumerate(edit['segments']):
        duration=s['frames']/FPS;destination=OUT/f'edit-{take}-{i:02}.mp4'
        if s['id']=='END':
            source=OUT/'end-card.png';inputs=['-loop','1','-i',str(source)];filters=f'fps=30,trim=end_frame={s["frames"]},setpts=PTS-STARTPTS,fade=t=in:d=0.18,fade=t=out:st=1.65:d=0.35'
        else:
            if s.get('sync_bbox'):
                source=OUT/'sync'/(s.get('sync_take',s['id']+'-timed-'+take)+'.mp4')
                sync=json.loads(source.with_suffix('.json').read_text(encoding='utf-8'))
                assert sync['status']=='complete' and sha(source)==sync['sha256']
            else:source=ROOT/s['source'] if s.get('source') else OUT/'takes'/(s['take']+'.webm')
            assert source.exists()
            inputs=['-ss',str(s.get('in_sec',0)),'-i',str(source)]
            crop=s['crop'];assert crop and len(crop)==4
            tail=f'tpad=stop_mode=clone:stop_duration=0.10,minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,scale=1920:1080:flags=lanczos,setsar=1,trim=end_frame={s["frames"]},setpts=PTS-STARTPTS'
            if s.get('source'):tail=f'fps=30,scale=1920:1080:flags=lanczos,setsar=1,trim=end_frame={s["frames"]},setpts=PTS-STARTPTS'
            filters=f'crop={crop[0]}:{crop[1]}:{crop[2]}:{crop[3]},'+tail
            if s.get('crop_switch_sec'):
                c=s['second_crop'];switch=s['crop_switch_sec']
                count=round(switch*FPS)
                motion='tpad=stop_mode=clone:stop_duration=0.10,minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1'
                complex_filter=f'[0:v]split=2[wide][close];[wide]trim=end={switch},setpts=PTS-STARTPTS,crop={crop[0]}:{crop[1]}:{crop[2]}:{crop[3]},scale=1280:720,setsar=1,{motion},trim=end_frame={count},setpts=PTS-STARTPTS[w];[close]trim=start={switch},setpts=PTS-STARTPTS,crop={c[0]}:{c[1]}:{c[2]}:{c[3]},scale=1280:720,setsar=1,{motion},trim=end_frame={s["frames"]-count},setpts=PTS-STARTPTS[c];[w][c]concat=n=2:v=1:a=0,scale=1920:1080:flags=lanczos,setsar=1[v]'
            sources.append({'shot_id':s['id'],'file':str(source.relative_to(ROOT)),'sha256':sha(source),'start_frame':nframes,**s})
        filtering=['-filter_complex',complex_filter,'-map','[v]'] if s.get('crop_switch_sec') else ['-vf',filters]
        run([*inputs,*filtering,'-an','-frames:v',str(s['frames']),'-c:v','libx264','-crf','17','-preset','medium','-pix_fmt','yuv420p',str(destination)])
        segment_files.append(destination);nframes+=s['frames'];print('Edited',s['id'],flush=True)
    (OUT/'concat.txt').write_text('\n'.join("file '"+p.name+"'" for p in segment_files),encoding='utf-8')
    run(['-f','concat','-safe','0','-i',str(OUT/'concat.txt'),'-i',str(OUT/'mix.wav'),'-vf','ass=film.ass',
        '-map','0:v:0','-map','1:a:0','-frames:v',str(nframes),'-t',str(nframes/FPS),'-c:v','libx264','-crf','17','-preset','medium','-pix_fmt','yuv420p',
        '-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',str(target)])
    save(OUT/f'edit-{take}.json',{'version':edit['version'],'film':str(target.relative_to(ROOT)),'sha256':sha(target),'bytes':target.stat().st_size,
        'frames':nframes,'fps':FPS,'duration_sec':nframes/FPS,'segments':sources,'human_art_approval':False,'production_deployed':False})
    print('Film created',str(target),nframes,flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--prepare-only',action='store_true');ap.add_argument('--take',default='v1');args=ap.parse_args()
    prepare()
    if not args.prepare_only:finish(args.take)
