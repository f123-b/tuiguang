"""Local production takes, resumable only by an acknowledged Comfy prompt id.

This independent film uses FP8 weight loading to fit the installed 8 GB GPU.
It does not modify the product provider's fixed, validated workflow.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import uuid

from dotenv import load_dotenv
from filelock import FileLock
from creator import wan_comfy

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / ".data/short-drama-49/takes"
ASSETS = Path(__file__).with_name("assets")

def write(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)

def run(name, source, prompt, seed):
    OUT.mkdir(parents=True, exist_ok=True)
    receipt_path = OUT / (name + "-receipt.json")
    target = OUT / (name + ".webm")
    client = wan_comfy.Client()
    try:
        if receipt_path.exists():
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if receipt.get("status") == "complete":
                assert hashlib.sha256(target.read_bytes()).hexdigest() == receipt["sha256"]
                print("Existing completed take", name, flush=True)
                return
            if not receipt.get("prompt_id"):
                raise RuntimeError("Submission may be unknown: inspect Comfy queue/history; never automatically resubmit")
            if receipt.get("status") == "error":
                raise RuntimeError("Known failed take preserved; choose a new take name explicitly")
        else:
            identifier = uuid.uuid4().hex
            data = dict(style="realistic", prompt=prompt, seed=seed, width=1280, height=704, frames=121)
            image = client.upload(identifier, source.read_bytes())
            graph = wan_comfy.workflow(data, image, identifier)
            graph["model"]["inputs"]["weight_dtype"] = "fp8_e4m3fn"
            graph["decode"] = {"class_type":"VAEDecodeTiled", "inputs":{
                "samples":["sample",0], "vae":["vae",0], "tile_size":512,
                "overlap":64, "temporal_size":32, "temporal_overlap":8}}
            graph["negative"]["inputs"]["text"] += ", second person, foreground person, silhouette, speaking, open mouth, face morphing, camera movement, sudden zoom, duplicated objects"
            receipt = dict(job_id=identifier, shot_id=name, status="prepared", source=str(source.relative_to(ROOT)),
                           source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), input=data,
                           model=wan_comfy.snapshot(), workflow_version="short_drama_fp8_tiled@2", graph=graph,
                           started_at=time.time(), metrics_before=client.metrics())
            write(receipt_path, receipt)
            receipt["status"] = "submission_pending"
            write(receipt_path, receipt)
            receipt["prompt_id"] = client.submit(graph, identifier)
            receipt["status"] = "submitted"
            write(receipt_path, receipt)
            print("Submitted", name, receipt["prompt_id"], flush=True)
        while True:
            history = client.history(receipt["prompt_id"])
            if history:
                write(OUT / (name + "-history.json"), history)
                if history.get("status", {}).get("status_str") == "error":
                    receipt["status"] = "error"
                    write(receipt_path, receipt)
                    raise RuntimeError("Known generation failure; preserved receipt")
                if history.get("status", {}).get("completed"):
                    client.download(history["outputs"]["save"]["images"][0], target, receipt["job_id"])
                    receipt.update(status="complete", elapsed_sec=time.time()-receipt["started_at"],
                                   sha256=hashlib.sha256(target.read_bytes()).hexdigest(), metrics_after=client.metrics())
                    write(receipt_path, receipt)
                    print("Complete", name, round(receipt["elapsed_sec"], 1), flush=True)
                    return
            time.sleep(10)
    finally:
        client.free_models()
        client.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("source")
    parser.add_argument("prompt")
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    with FileLock(str(ROOT / ".data/qwen-model/.inference.lock"), timeout=7200):
        run(args.name, ASSETS / args.source, args.prompt, args.seed)
