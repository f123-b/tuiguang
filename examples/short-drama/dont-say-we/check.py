"""Technical delivery acceptance, separate from the user's artistic judgment."""
import argparse
import array
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[3]
PACK=Path(__file__).parent
OUT=ROOT/".data/short-drama-49"
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def probe(path):return json.loads(subprocess.check_output(["ffprobe","-v","error","-count_frames","-show_streams","-show_format","-of","json",str(path)],encoding="utf-8"))
def main():
    p=argparse.ArgumentParser();p.add_argument("--take",default="v2");args=p.parse_args()
    target=OUT/("别说我们-"+args.take+".mp4")
    assert target.is_file(), "Finished film not yet available"
    edit=json.loads((OUT/(args.take+"-edit-manifest.json")).read_text(encoding="utf-8"))
    assert sha(target)==edit["sha256"]
    assert edit["origin"]=="independent local production; app human review untouched"
    for row in edit["shots"]:
        assert sha(ROOT/row["source"])==row["source_sha256"]
    details=probe(target)
    v=next(s for s in details["streams"] if s["codec_type"]=="video")
    a=next(s for s in details["streams"] if s["codec_type"]=="audio")
    assert (v["width"],v["height"],v["r_frame_rate"],int(v["nb_read_frames"]))==(1920,1080,"30/1",1230)
    assert a["codec_name"]=="aac" and int(a["sample_rate"])==48000
    assert abs(float(details["format"]["duration"])-41)<.06
    assert abs(float(v["duration"])-float(a["duration"]))<.06
    subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(target),"-map","0:v","-map","0:a","-f","null","-"],check=True)
    cues=json.loads((OUT/"cue-sheet.json").read_text(encoding="utf-8"))
    assert len(cues)==11 and all(b["start"]>a["end"] for a,b in zip(cues,cues[1:]))
    for cue in cues:
        assert sha(OUT/"voices"/(cue["id"]+".wav"))==cue["sha256"]
    for name in ("s01-opening-v1","s02-side-v1","s03-resolve-v1"):
        source=OUT/"takes"/(name+".webm")
        receipt=json.loads(source.with_name(name+"-receipt.json").read_text(encoding="utf-8"))
        assert receipt["status"]=="complete" and receipt["sha256"]==sha(source)
        assert json.loads(source.with_name(name+"-history.json").read_text(encoding="utf-8"))["status"]["completed"]
        native=probe(source)["streams"][0]
        assert (native["width"],native["height"],native["r_frame_rate"],int(native["nb_read_frames"]))==(1280,704,"24/1",121)
    # Measure original channels. A correlated stereo -> mono fold adds ~3 dB.
    raw=subprocess.check_output(["ffmpeg","-v","error","-i",str(target),"-vn","-ar","24000","-f","f32le","-"])
    samples=array.array('f',raw)
    peak=max(abs(x) for x in samples)
    rms=(sum(x*x for x in samples)/len(samples))**.5
    assert .01<rms<.3 and .05<peak<.99, (rms,peak)
    loud=subprocess.run(["ffmpeg","-hide_banner","-i",str(target),"-af","loudnorm=I=-16:TP=-1.5:LRA=9:print_format=json","-f","null","-"],capture_output=True,text=True,check=True)
    match=re.findall(r'\{\s*"input_i".*?\}',loud.stderr,re.S)
    meter=json.loads(match[-1])
    assert -18<float(meter["input_i"])<-14
    assert float(meter["input_tp"])<-.8
    report={"task":"#49","take":args.take,"result":"technical_pass","duration":details["format"]["duration"],"frames":int(v["nb_read_frames"]),"sha256":sha(target),"full_decode":"pass","voice_cues":len(cues),"native_new_shots":3,"rms":rms,"sample_peak":peak,"loudness":meter,"art_review":"requires_user","commercial_license":"not_approved"}
    (OUT/(args.take+"-validation.json")).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    (PACK/"validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
