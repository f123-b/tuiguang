"""Normalize the real variable-rate screencast; retain unchanged UI frames."""
import hashlib
import bisect
import json
import math
from pathlib import Path
import subprocess
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/".data/short-drama-49/ui-v8"
data=json.loads((OUT/"capture.json").read_text(encoding="utf-8"))
frames=data["frames"]
assert len(frames)>50
assert all(b["timestamp"]>a["timestamp"] for a,b in zip(frames,frames[1:]))
lines=["ffconcat version 1.0"]
for i,f in enumerate(frames):
    duration=frames[i+1]["timestamp"]-f["timestamp"] if i+1<len(frames) else max(.04,data["duration"]-f["wall"])
    lines.extend(["file '"+Path(f["file"]).as_posix()+"'", "option framerate 1000", "duration "+str(duration)])
lines.extend(["file '"+Path(frames[-1]["file"]).as_posix()+"'", "option framerate 1000"])
concat=OUT/"capture.ffconcat"
concat.write_text("\n".join(lines)+"\n",encoding="utf-8")
target=ROOT/"examples/short-drama/dont-say-we/assets/youzhao-project-note-v8.mp4"
if target.exists():raise RuntimeError("Preserve existing capture")
size=Image.open(frames[0]["file"]).size
assert all(Image.open(f["file"]).size==size for f in frames)
assert size[0]>=1920, ("Recapture at a larger actual window size",size)
duration=data["duration"]-frames[0]["wall"]
count=math.ceil(duration*30)
times=[f["timestamp"]-frames[0]["timestamp"] for f in frames]
process=subprocess.Popen(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-f","rawvideo","-pixel_format","rgb24","-video_size",f"{size[0]}x{size[1]}","-framerate","30","-i","pipe:0","-an","-c:v","libx264","-crf","16","-preset","medium","-pix_fmt","yuv420p","-movflags","+faststart",str(target)],stdin=subprocess.PIPE)
previous=-1
for i in range(count):
    selected=max(0,bisect.bisect_right(times,i/30)-1)
    if selected!=previous:
        pixels=Image.open(frames[selected]["file"]).convert("RGB").tobytes()
        previous=selected
    process.stdin.write(pixels)
process.stdin.close()
assert process.wait()==0
probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-count_frames","-show_streams","-show_format","-of","json",str(target)],encoding="utf-8"))
assert (probe["streams"][0]["width"],probe["streams"][0]["height"])==size
assert int(probe["streams"][0]["nb_read_frames"])==count
assert abs(float(probe["format"]["duration"])-duration)<1/30+.002
evidence={k:v for k,v in data.items() if k!="frames"}
evidence.update(first_frame_wall=frames[0]["wall"],native_duration_sec=duration,actual_width=size[0],actual_height=size[1],actual_capture_frames_per_sec=round(len(frames)/duration,3))
evidence.update(source_frames=len(frames),source="Unmodified real 有招 0.2.24, isolated new synthetic data, external HTTP(S) blocked",source_git_sha=subprocess.check_output(["git","-C","D:/电脑面试","rev-parse","HEAD"],encoding="utf-8").strip(),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),probe=probe)
Path(__file__).with_name("capture-evidence.json").write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"file":str(target),"frames":probe["streams"][0]["nb_read_frames"],"duration":probe["format"]["duration"],"sha256":evidence["sha256"]}))
