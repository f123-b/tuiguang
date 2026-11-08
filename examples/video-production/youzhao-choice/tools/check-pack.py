"""Check this preproduction handoff's bytes and timing, never its artistic quality."""

import hashlib
import json
import subprocess
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    root = Path(__file__).resolve().parents[1]
    plan = read(root / "production.json")
    trial = read(root / "trial-shot.json")
    evidence = read(root / "capture-evidence.json")
    shots = plan["shots"]
    assert sum(s["duration_frames"] for s in shots) == plan["total_frames"] == 1200
    identifiers = {s["id"] for s in shots}
    assert len(identifiers) == len(shots) == 12
    requirements = {a["id"]: a for a in plan["asset_requirements"]}
    assert all(set(s["assets"]) <= requirements.keys() for s in shots)
    assert all(set(a["supports_shots"]) <= identifiers for a in requirements.values())

    files = [*plan["visual_development"], requirements["ui_pickup"]]
    for asset in files:
        path = (root / asset["file"]).resolve()
        assert path.is_relative_to(root)
        assert path.stat().st_size == asset["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == asset["sha256"]
    assert trial["start_frame"]["sha256"] == files[0]["sha256"]
    video = root / requirements["ui_pickup"]["file"]
    probe = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-count_frames",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(video),
            ],
            encoding="utf-8",
        )
    )
    stream = probe["streams"][0]
    assert len(probe["streams"]) == 1 and stream["codec_type"] == "video"
    assert (stream["width"], stream["height"], stream["r_frame_rate"]) == (1920, 1080, "30/1")
    assert int(stream["nb_read_frames"]) == 413
    assert abs(float(probe["format"]["duration"]) - 413 / 30) < 0.002
    assert evidence["media"]["saved_note_verified"]
    subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-i", str(video), "-f", "null", "-"], check=True)

    # Stills and a successful media probe must not turn this into a completed film.
    assert all(not a["satisfies_dynamic_shot_requirement"] for a in plan["visual_development"])
    assert requirements["actor_rehearsal"]["status"] == "missing"
    assert plan["status"] == "preproduction_incomplete"
    assert not plan["cloud_video"]["spend_approved"]
    assert not plan["cloud_video"]["submitted_request_ids"]
    print(
        json.dumps(
            {
                "structure_and_file_integrity": "passed",
                "duration_frames": 1200,
                "ui_video_decoded_frames": 413,
                "creative_approval": plan["creative_approval"],
                "film_status": plan["status"],
                "video_quote": plan["cloud_video"]["quote"],
                "note": "Checks do not certify artistic quality or authorize video generation.",
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
