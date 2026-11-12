"""Verify served/downloaded bytes and seek range; no external publishing."""
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/".data/short-drama-49"
base="http://127.0.0.1:8785"
results=[]
for route,file in (("/film.mp4?download=1",OUT/"别说我们-v2.mp4"),("/subtitles.srt?download=1",OUT/"别说我们.srt"),("/production.zip?download=1",OUT/"别说我们-完整制作包-v2.zip")):
    with urlopen(base+route,timeout=30) as response:
        data=response.read()
        assert response.status==200 and response.headers.get("Content-Disposition","").startswith("attachment;")
        assert hashlib.sha256(data).hexdigest()==hashlib.sha256(file.read_bytes()).hexdigest()
        results.append(dict(route=route,status=response.status,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
with urlopen(Request(base+"/film.mp4",headers={"Range":"bytes=12345-12444"}),timeout=10) as response:
    data=response.read()
    assert response.status==206 and data==(OUT/"别说我们-v2.mp4").read_bytes()[12345:12445]
    results.append(dict(route="video range",status=response.status,bytes=len(data)))
result=dict(result="pass",items=results,boundary="HTTP bytes verified; browser save-dialog confirmation not automated")
(OUT/"http-download-validation.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(result,ensure_ascii=False))
