"""Whitelist the finished local production. Never include profiles or credentials."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT=Path(__file__).resolve().parents[3]
PACK=Path(__file__).parent
OUT=ROOT/".data/short-drama-49"
TAKE="v2"
target=OUT/f"别说我们-完整制作包-{TAKE}.zip"
if target.exists():raise RuntimeError("Preserve existing delivery archive")
validation=json.loads((OUT/f"{TAKE}-validation.json").read_text(encoding="utf-8"))
assert validation["result"]=="technical_pass"
paths=[OUT/f"别说我们-{TAKE}.mp4",OUT/"别说我们.srt",OUT/f"{TAKE}-edit-manifest.json",OUT/f"{TAKE}-video-project-ir.json",OUT/f"{TAKE}-validation.json",OUT/"cue-sheet.json",OUT/"film.ass",OUT/"end-card.png",OUT/"original-bed.wav",OUT/"mix.wav"]
paths+=list((OUT/"voices").glob("*.wav"))+[OUT/"voices/receipts.json"]
paths+=list((OUT/"takes").glob("*.webm"))+list((OUT/"takes").glob("*-receipt.json"))+list((OUT/"takes").glob("*-history.json"))
paths+=[ROOT/"docs/implementation/DONT_SAY_WE_FILM_VALIDATION.md"]
old=ROOT/".data/ai-drama-quality-v2"
paths += [old/name for name in ("native.webm","closeup.webm","comparison-receipt.json","closeup-receipt.json","comparison-history.json","closeup-history.json")]
paths += [p for p in PACK.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix in (".py",".cjs",".mjs",".json",".md",".png",".mp4")]
rows=[]
with zipfile.ZipFile(target,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
    for file in dict.fromkeys(paths):
        assert file.is_file(),file
        relative=file.relative_to(ROOT).as_posix()
        assert not any(part in relative.lower() for part in (".env","product-profile","product-data","certificate","private-key",".inference"))
        if file.suffix in (".json",".md",".py",".cjs",".mjs"):
            assert not re.search(r"\bsk-[A-Za-z0-9]{16,}",file.read_text(encoding="utf-8")), "Credential-like text; do not package"
        arc="复现工程/"+relative
        z.write(file,arc)
        rows.append(dict(file=arc,bytes=file.stat().st_size,sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
    z.write(OUT/f"别说我们-{TAKE}.mp4","成片/别说我们.mp4")
    z.write(OUT/"别说我们.srt","成片/别说我们.srt")
    z.writestr("文件清单.json",json.dumps(rows,ensure_ascii=False,indent=2))
with zipfile.ZipFile(target) as z:assert z.testzip() is None
receipt=dict(file=target.name,bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),source_files=len(rows),zip_crc="pass",credentials_scan="whitelisted text pass",models_included=False,personal_data_included=False)
(OUT/"bundle-receipt.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(receipt,ensure_ascii=False))
