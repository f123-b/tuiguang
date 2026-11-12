"""Reproducible independent short-film edit. Does not approve app review gates."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import uuid

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import soundfile as sf

ROOT=Path(__file__).resolve().parents[3]
PACK=Path(__file__).parent
OUT=ROOT/".data/short-drama-49"
FPS=30
STARTS=[.60,3.45,7.35,9.50,13.40,18.00,19.55,22.50,25.65,30.20,33.30]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")
def run(args):
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y","-threads","4",*args],check=True,cwd=OUT)
def probe(path):return json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)],encoding="utf-8"))
def stamp(t,sep='.'):
    ms=round(t*1000)
    return f"{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02}{sep}{ms%1000:03}"
def ass(t):
    cs=round(t*100)
    return f"{cs//360000}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}"

def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    script=json.loads((PACK/"production.json").read_text(encoding="utf-8"))
    voices=json.loads((OUT/"voices/receipts.json").read_text(encoding="utf-8"))
    assert len(voices)==len(STARTS)==len(script["cues"])
    cues=[]
    for source,start,written in zip(voices,STARTS,script["cues"]):
        file=OUT/"voices"/(source["id"]+".wav")
        assert sha(file)==source["sha256"] and source["text"]==written["text"]
        cue={**source,"start":start,"end":start+source["duration_sec"]}
        cues.append(cue)
    assert all(b["start"]>a["end"]+.2 for a,b in zip(cues,cues[1:]))
    duration=41.0
    # Small, original procedural score and stereo rain; no third-party recordings.
    sr=48000; n=round(duration*sr); t=np.arange(n)/sr
    rng=np.random.default_rng(49)
    noise=rng.normal(0,1,(n,2)).astype(np.float32)
    # Low continuous room/rain texture with a slow, non-rhythmic envelope.
    smooth=np.stack([np.convolve(noise[:,ch],np.ones(17)/17,mode="same") for ch in range(2)],axis=1)
    ambience=.012*smooth*(.83+.17*np.sin(t*.61))[:,None]
    music=np.zeros((n,2),dtype=np.float32)
    notes=[(10.8,246.94),(14.5,329.63),(20.8,392.0),(29.5,369.99),(31.2,329.63),(34.7,220.0),(37.5,293.66)]
    for start,freq in notes:
        length=min(3.8,duration-start); x=np.arange(round(length*sr))/sr
        tone=sum((1/h**1.8)*np.sin(2*np.pi*freq*h*x+.09*h)*np.exp(-x*(1.0+h*.10)) for h in range(1,7))
        env=(1-np.exp(-x*140))*np.minimum(1,(length-x)/.5)
        sound=.018*tone*env
        offset=round(start*sr); music[offset:offset+len(x),0]+=sound*.85;music[offset:offset+len(x),1]+=sound
    fade=np.minimum(1,t/1.2)*np.minimum(1,(duration-t)/1.2)
    sf.write(OUT/"original-bed.wav",(ambience+music)*fade[:,None],sr,subtype="PCM_24")
    inputs=["-i",str(OUT/"original-bed.wav")]
    filters=["[0:a]highpass=f=100,lowpass=f=8500[bed]"]
    labels=["[bed]"]
    for i,cue in enumerate(cues,1):
        inputs.extend(["-i",str(OUT/"voices"/(cue["id"]+".wav"))])
        eq="highpass=f=175,lowpass=f=5600" if cue["role"]=="interviewer" else "highpass=f=95,lowpass=f=10000"
        delay=round(cue["start"]*1000)
        filters.append(f"[{i}:a]{eq},loudnorm=I=-19:TP=-3:LRA=9,afade=t=in:d=0.012,afade=t=out:st={max(0,cue['duration_sec']-.05)}:d=0.05,adelay={delay}|{delay}[v{i}]")
        labels.append(f"[v{i}]")
    filters.append("".join(labels)+f"amix=inputs={len(labels)}:normalize=0:duration=longest,atrim=duration={duration},loudnorm=I=-16:TP=-1.5:LRA=9[a]")
    run([*inputs,"-filter_complex",";".join(filters),"-map","[a]","-ar","48000","-c:a","pcm_s24le",str(OUT/"mix.wav")])
    header="""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Dialogue,Microsoft YaHei,46,&H00FFFFFF,&H00FFFFFF,&H00141818,&H80141818,0,0,0,0,100,100,0,0,3,2,0,2,90,90,62,1
Style: Note,Microsoft YaHei,27,&H00DFE6E1,&H00FFFFFF,&H60101515,&H60101515,0,0,0,0,100,100,0,0,1,1,0,7,70,70,55,1
Style: Brand,Microsoft YaHei,23,&H50DFE6E1,&H00FFFFFF,&H70101515,&H70101515,0,0,0,0,100,100,0,0,1,1,0,9,70,70,55,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines=["Dialogue: 0,0:00:00.00,0:00:02.80,Note,,0,0,0,,面试前 10 分钟\\N{\\fs20}一场脑海里的对话",
           "Dialogue: 0,0:00:00.00,0:00:37.50,Brand,,0,0,0,,AI 剧情演绎"]
    srt=[]
    for i,cue in enumerate(cues,1):
        who="面试官 · 画外" if cue["role"]=="interviewer" else "小林 · 心声"
        text="{\\fs23\\c&HCFD8D3&}"+who+"{\\r}\\N"+cue["text"]
        lines.append(f"Dialogue: 1,{ass(cue['start'])},{ass(cue['end'])},Dialogue,,0,0,0,,{text}")
        srt.append(f"{i}\n{stamp(cue['start'],',')} --> {stamp(cue['end'],',')}\n{who}\n{cue['text']}\n")
    (OUT/"film.ass").write_text(header+"\n".join(lines)+"\n",encoding="utf-8")
    (OUT/"别说我们.srt").write_text("\n".join(srt),encoding="utf-8")
    save(OUT/"cue-sheet.json",cues)
    save(PACK/"voice-receipts.json",voices)
    card=Image.new("RGB",(1920,1080),"#111a19")
    d=ImageDraw.Draw(card)
    def text(y,s,size,color):d.text((960,y),s,font=ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",size),fill=color,anchor="mm")
    text(355,'别说“我们”',84,"#F0F0E5")
    text(485,"从一次选择，开始讲。",43,"#BACCC0")
    text(680,"有招 · 项目经历，记下来。",30,"#96B5A5")
    text(960,"AI 剧情演绎 · 合成声音 · 虚构项目练习",22,"#7C9387")
    card.save(OUT/"end-card.png")
    print("Prepared 11 original dialogue cues, 41 s mix and subtitles",flush=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--prepare-only",action="store_true");parser.add_argument("--take",default="v2");args=parser.parse_args()
    if not args.take.replace('-','').isalnum():raise ValueError("invalid take name")
    target=OUT/("别说我们-"+args.take+".mp4")
    if target.exists() and not args.prepare_only:raise RuntimeError("Preserve existing cut; choose a new take")
    prepare()
    if args.prepare_only:return
    sources={key:OUT/"takes"/(key+".webm") for key in ("s01-opening-v1","s02-side-v1","s03-resolve-v1")}
    for key,file in sources.items():
        receipt=json.loads(file.with_name(key+"-receipt.json").read_text(encoding="utf-8"))
        assert receipt["status"]=="complete" and receipt["sha256"]==sha(file)
        assert json.loads(file.with_name(key+"-history.json").read_text(encoding="utf-8"))["status"]["completed"]
    ui=PACK/"assets/youzhao-project-note-v8.mp4"
    evidence=json.loads((PACK/"capture-evidence.json").read_text(encoding="utf-8"))
    assert sha(ui)==evidence["sha256"]
    ui_events={event["name"]:event["t"]-evidence["first_frame_wall"] for event in evidence["events"]}
    old=ROOT/".data/ai-drama-quality-v2"
    # Select clean parts of earlier legitimate takes; exclude the later foreground intrusion.
    scenes=[
      ("01-listen",sources["s01-opening-v1"],0,84,1.0,""),
      ("02-undervalue",sources["s02-side-v1"],0,132,1.2223,"crop=1152:648:0:0,"),
      ("03-why",sources["s01-opening-v1"],2.65,70,1.08,""),
      ("04-observe",ui,ui_events['recall_line_1']+.05,111,1.0,"crop=832:468:1712:200,"),
      ("05-choice",ui,ui_events['recall_line_2']+.05,114,1.0,"crop=832:468:1712:200,"),
      ("06-after",sources["s02-side-v1"],3.4,54,1.2,"crop=1152:648:0:0,"),
      ("07-result",ui,ui_events['recall_line_3']+.05,92,1.0,"crop=832:468:1712:200,"),
      ("08-missing",old/"closeup.webm",0,112,1.49,""),
      ("09-too-small",old/"native.webm",0,92,1.65,"crop=640:352:80:352,"),
      ("10-offer-and-resolve",sources["s03-resolve-v1"],0,190,1.32,"crop=864:486:72:24,"),
      ("11-remember",ui,float(evidence['probe']['format']['duration'])-2.6,75,1.0,"crop=832:468:1712:200,"),
    ]
    # 1126 picture frames +104 end-card frames = 41 seconds at 30 fps.
    assert sum(s[3] for s in scenes)==1126
    segments=[];manifest=[];cursor=0
    for name,source,start,frames,rate,crop in scenes:
        print("Render segment",name,flush=True)
        segment=OUT/(args.take+"-"+name+".mp4")
        # Interpolate restrained acting at source size before mastering; UI uses measured holds.
        interpolation="minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:vsbmc=1," if source.suffix==".webm" else "fps=30,"
        filters=f"setpts=(PTS-STARTPTS)*{rate},{crop}{interpolation}scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080,setsar=1,format=yuv420p"
        run(["-ss",str(start),"-i",str(source),"-vf",filters,"-frames:v",str(frames),"-an","-c:v","libx264","-crf","17","-preset","medium",str(segment)])
        actual=int(probe(segment)["streams"][0].get("nb_frames",0))
        if actual!=frames:raise RuntimeError(f"Insufficient actual source frames for {name}: {actual}/{frames}; no hidden tail extension")
        segments.append(segment)
        manifest.append(dict(shot_id=name,source=str(source.relative_to(ROOT)),source_sha256=sha(source),source_start=start,start=cursor/FPS,end=(cursor+frames)/FPS,frames=frames,retime_factor=rate,filters=filters))
        cursor+=frames
    end=OUT/(args.take+"-12-end.mp4")
    run(["-loop","1","-i",str(OUT/"end-card.png"),"-vf","fps=30,format=yuv420p","-frames:v",str(1230-cursor),"-an","-c:v","libx264","-crf","17","-preset","medium",str(end)])
    segments.append(end)
    concat=OUT/(args.take+".ffconcat");concat.write_text("ffconcat version 1.0\n"+"\n".join("file '"+s.as_posix()+"'" for s in segments)+"\n",encoding="utf-8")
    run(["-f","concat","-safe","0","-i",str(concat),"-i",str(OUT/"mix.wav"),"-vf","ass=film.ass","-map","0:v","-map","1:a","-c:v","libx264","-crf","17","-preset","medium","-c:a","aac","-b:a","256k","-ar","48000","-movflags","+faststart",str(target)])
    final=probe(target)
    end_row=dict(shot_id="12-end",source=str((OUT/"end-card.png").relative_to(ROOT)),source_sha256=sha(OUT/"end-card.png"),source_start=0,start=cursor/FPS,end=41,frames=1230-cursor,retime_factor=1,filters="native graphic end card, fps=30")
    receipt=dict(version="short_drama_cut@1",task="#49",take=args.take,title='别说“我们”',trace_id=uuid.uuid4().hex,creator_run_id=None,content_id=None,video_project_id=uuid.uuid4().hex,render_job_id=uuid.uuid4().hex,origin="independent local production; app human review untouched",file=target.name,sha256=sha(target),duration=float(final["format"]["duration"]),fps=30,canvas=[1920,1080],native_generation=[1280,704,24],dialogue="Stock synthetic voices, interviewer offscreen and protagonist inner monologue; no lipsync claim",shots=manifest+[end_row],probe=final)
    save(OUT/(args.take+"-edit-manifest.json"),receipt)
    save(PACK/"edit-manifest.json",receipt)
    from creator.schemas import VideoInput
    assets={row["source_sha256"][:32]:dict(path=row["source"],sha256=row["source_sha256"]) for row in manifest}
    shots=[]
    generation={str(file.relative_to(ROOT)):json.loads(file.with_name(key+"-receipt.json").read_text(encoding="utf-8")) for key,file in sources.items()}
    generation[str((old/"native.webm").relative_to(ROOT))]=json.loads((old/"comparison-receipt.json").read_text(encoding="utf-8"))
    generation[str((old/"closeup.webm").relative_to(ROOT))]=json.loads((old/"closeup-receipt.json").read_text(encoding="utf-8"))
    for row in manifest:
        record=generation.get(row["source"])
        shots.append(dict(shot_id=row["shot_id"],provider="comfy_wan" if record else "ffmpeg_media",kind="ai_creative_scene" if record else "screen_demo",asset_id=row["source_sha256"][:32],**({"generation_job_id":record["job_id"]} if record else {}),duration_frames=row["frames"],trim_start_frame=round(row["source_start"]*FPS),speed_percent=round(100/row["retime_factor"]),design=dict(layout="cinema",motion="still")))
    for file,role in ((OUT/"end-card.png","card"),(OUT/"mix.wav","mix")):
        digest=sha(file);assets[digest[:32]]=dict(path=str(file.relative_to(ROOT)),sha256=digest)
        if role=="card":shots.append(dict(shot_id="12-end",provider="ffmpeg_media",kind="montage",asset_id=digest[:32],duration_frames=1230-cursor,design=dict(layout="cinema",motion="still")))
        else:mix_id=digest[:32]
    cues=json.loads((OUT/"cue-sheet.json").read_text(encoding="utf-8"))
    ir=VideoInput(brand_id="offline-youzhao-49",name='别说“我们”·独立短剧',width=1920,height=1080,shots=shots,audio_tracks=[dict(track_id="final-mix",asset_id=mix_id,role="voiceover",start_frame=0,duration_frames=1230)],subtitles=[dict(cue_id=c["id"],start_frame=round(c["start"]*FPS),end_frame=round(c["end"]*FPS),text=c["text"]) for c in cues],preview_required=True).model_dump()
    ir.update(schema_version="1.1",offline_scope="Independent film. Map real brand/assets/jobs and exact editorial filters before app import; DTO validation is not an import or render approval.",offline_assets=assets,offline_exact_edit_manifest=args.take+"-edit-manifest.json",user_approval=False)
    save(OUT/(args.take+"-video-project-ir.json"),ir)
    save(PACK/"video-project-ir.json",ir)
    print(json.dumps({"file":str(target),"sha256":receipt["sha256"],"duration":receipt["duration"]},ensure_ascii=False),flush=True)

if __name__=="__main__":main()
