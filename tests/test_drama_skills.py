import copy

import pytest


@pytest.fixture
def drama_plan():
    return {
        "title": "那页笔记",
        "logline": "求职者用当时的笔记解释一个选择",
        "hook": "明明参与了项目却回答不出为什么",
        "characters": [
            {
                "id": "C01",
                "name": "小林",
                "goal": "讲清自己的选择",
                "flaw": "只记结果不记理由",
                "appearance": "短发灰外套白T恤",
                "voice_hint": "克制自然",
            }
        ],
        "scenes": [
            {
                "id": "S01",
                "name": "书桌",
                "description": "同一张木桌和笔记本",
                "lighting": "左侧暖光",
                "axis": "人物左侧电脑右侧",
                "palette": "暖灰",
            }
        ],
        "beats": [
            {
                "id": f"B{i}",
                "cause_id": f"B{i - 1}" if i > 1 else None,
                "character_id": "C01",
                "role": role,
                "action": action,
                "obstacle": "记忆模糊",
                "result": result,
            }
            for i, role, action, result in [
                (1, "hook", "面对问题停住", "决定找记录"),
                (2, "setup", "翻开旧笔记", "找到两个方案"),
                (3, "choice", "指出当时的取舍", "说出依据"),
                (4, "payoff", "把理由讲完整", "回答问题"),
            ]
        ],
        "shots": [
            {
                "id": f"SH{i}",
                "beat_id": f"B{i}",
                "scene_id": "S01",
                "character_ids": ["C01"],
                "action": action,
                "frame_prompt": "人物在左电脑在右的中景",
                "motion_prompt": "缓慢抬眼，保持人物和背景稳定",
                "framing": "medium" if i % 2 else "close",
                "camera": "固定机位",
                "start_positions": {"C01": "left"},
                "end_positions": {"C01": "left"},
                "transition_reason": "",
                "narration": line,
                "delivery": "平静",
                "frames": 121,
                "reference_asset_id": None,
            }
            for i, action, line in [
                (1, "面对问题停住", "当时为什么选这个方案？"),
                (2, "翻开旧笔记", "我把取舍写在这页了。"),
                (3, "指出方案的理由", "先让人找到，再看细节。"),
                (4, "解释自己的取舍", "这就是当时选择的理由。"),
            ]
        ],
        "uncertainties": [],
    }


def test_registry_is_pinned_and_executes_upstream_validator(drama_plan):
    from creator.drama_skills import registry, validate_script

    result = registry()
    assert len(result["skills"]) == 8
    assert all(len(s["commit"]) == 40 and s["integrity"] == "verified" for s in result["skills"])
    checked = validate_script(drama_plan, 20)
    assert checked["errors"] == [], checked
    assert checked["validator"] == "shuohao/novel-script"


@pytest.mark.parametrize(
    "damage,code",
    [
        ("cause", "DRAMA_CAUSAL_LINK"),
        ("positions", "DRAMA_CONTINUITY"),
        ("dialogue", "DRAMA_LINE_TOO_LONG"),
        ("coverage", "DRAMA_BEAT_COVERAGE"),
    ],
)
def test_logic_gates_find_specific_locations(drama_plan, damage, code):
    from creator.drama import check_plan, DramaPlan

    doc = copy.deepcopy(drama_plan)
    if damage == "cause":
        doc["beats"][2]["cause_id"] = None
    if damage == "positions":
        doc["shots"][1]["start_positions"]["C01"] = "right"
    if damage == "dialogue":
        doc["shots"][1]["narration"] = "为什么" * 12
    if damage == "coverage":
        doc["shots"][1]["beat_id"] = "B1"
    report = check_plan(DramaPlan.model_validate(doc).model_dump(), 20)
    assert any(i["code"] == code and i["location"] for i in report["issues"]), report


def test_private_edit_and_confirmation_invalidates_bindings(client, user, brand, drama_plan):
    response = client.post(
        "/api/v1/dramas",
        json={
            "brand_id": brand["id"],
            "title": "那页笔记",
            "story": "面试被问为什么，翻笔记找到取舍的原因再回答",
            "theme": "讲清自己的选择",
            "genre": "职场剧情",
            "duration_sec": 20,
            "rights_confirmed": True,
        },
    )
    assert response.status_code == 201, response.text
    item = response.json()
    uri = "/api/v1/dramas/" + item["id"]
    saved = client.put(uri + "/plan", json={"expected_revision": 1, "document": drama_plan})
    assert saved.status_code == 200, saved.text
    checked = client.post(
        uri + "/confirm", json={"expected_revision": 2, "confirmed": True, "note": "已核对因果、角色与站位"}
    )
    assert checked.status_code == 200, checked.text
    assert checked.json()["confirmation"]["revision"] == 2
    stale = client.put(uri + "/plan", json={"expected_revision": 1, "document": drama_plan})
    assert stale.status_code == 409
    edited = client.put(uri + "/plan", json={"expected_revision": 2, "document": drama_plan}).json()
    assert edited["confirmation"] == {} and edited["bindings"] == {}
    client.post("/api/v1/auth/logout")
    client.post(
        "/api/v1/auth/register",
        json={"email": "another@example.org", "password": "TestPassword987!", "name": "隔离"},
    )
    assert client.get(uri).status_code == 404


def prepare(client, brand, plan):
    r = client.post(
        "/api/v1/dramas",
        json={
            "brand_id": brand["id"],
            "title": "测试原创短剧",
            "story": "面对追问，回顾当时记录，再解释自己的选择",
            "theme": "选择有依据",
            "duration_sec": 20,
            "rights_confirmed": True,
        },
    )
    assert r.status_code == 201, r.text
    uri = "/api/v1/dramas/" + r.json()["id"]
    r = client.put(uri + "/plan", json={"expected_revision": 1, "document": plan})
    assert r.status_code == 200, r.text
    r = client.post(
        uri + "/confirm", json={"expected_revision": 2, "confirmed": True, "note": "测试已核对因果与连续性"}
    )
    assert r.status_code == 200, r.text
    return uri


def image_asset(client, brand, size=(1280, 704)):
    import io
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", size, "#234455").save(buf, "PNG")
    r = client.post(
        f"/api/v1/brands/{brand['id']}/assets",
        files={"file": ("synthetic.png", buf.getvalue())},
        data={"source": "original synthetic fixture", "license_note": "test-generated", "verified": "true"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_low_resolution_reference_is_blocked_before_submission(client, user, brand, drama_plan, monkeypatch):
    from creator import wan_comfy

    calls = []
    monkeypatch.setattr(wan_comfy, "snapshot", lambda: calls.append(True))
    asset = image_asset(client, brand, (512, 288))
    for s in drama_plan["shots"]:
        s["reference_asset_id"] = asset["id"]
    uri = prepare(client, brand, drama_plan)
    r = client.post(uri + "/shots/SH1/generate", json={"expected_revision": 2, "confirmed": True})
    assert r.status_code == 422 and r.json()["error"]["code"] == "DRAMA_SOURCE_RESOLUTION"
    assert calls == []


def test_confirmed_plan_queues_only_selected_shot_once(client, user, brand, drama_plan, monkeypatch):
    from creator import wan_comfy
    from creator.models import VideoGenerationJob
    from creator.db import SessionLocal
    from sqlalchemy import select

    monkeypatch.setattr(
        wan_comfy, "snapshot", lambda: {"model_id": "synthetic-only", "version": wan_comfy.VERSION}
    )
    asset = image_asset(client, brand)
    for s in drama_plan["shots"]:
        s["reference_asset_id"] = asset["id"]
    uri = prepare(client, brand, drama_plan)
    preview = client.get(uri + "/shots/SH2/request")
    assert preview.status_code == 200, preview.text
    assert "短发灰外套白T恤" in preview.json()["prompt"]
    r = client.post(uri + "/shots/SH2/generate", json={"expected_revision": 2, "confirmed": True})
    same = client.post(uri + "/shots/SH2/generate", json={"expected_revision": 2, "confirmed": True})
    assert r.status_code == same.status_code == 201, r.text
    assert r.json()["id"] == same.json()["id"]
    with SessionLocal() as db:
        assert len(db.scalars(select(VideoGenerationJob)).all()) == 1
    assert client.post(uri + "/build", json={"expected_revision": 2, "confirmed": True}).status_code == 409
    assert client.get(uri).json()["project"]["bindings"] == {"SH2": r.json()["id"]}
    # A retake never resubmits running/unknown work, and changes only this shot.
    denied = client.post(
        uri + "/shots/SH2/generate",
        json={"expected_revision": 2, "confirmed": True, "take_key": "retake-one"},
    )
    assert denied.status_code == 409
    with SessionLocal() as db:
        db.get(VideoGenerationJob, r.json()["id"]).status = "failed"
        db.commit()
    retake = client.post(
        uri + "/shots/SH2/generate",
        json={"expected_revision": 2, "confirmed": True, "take_key": "retake-one"},
    )
    assert retake.status_code == 201 and retake.json()["id"] != r.json()["id"], retake.text
    repeat = client.post(
        uri + "/shots/SH2/generate",
        json={"expected_revision": 2, "confirmed": True, "take_key": "retake-one"},
    )
    assert repeat.json()["id"] == retake.json()["id"]
    original_replay = client.post(
        uri + "/shots/SH2/generate", json={"expected_revision": 2, "confirmed": True}
    )
    assert original_replay.json()["id"] == r.json()["id"]
    assert client.get(uri).json()["project"]["bindings"]["SH2"] == retake.json()["id"]
    with SessionLocal() as db:
        assert len(db.scalars(select(VideoGenerationJob)).all()) == 2


def test_skill_tamper_is_not_silently_used(tmp_path, monkeypatch):
    import json
    from creator import drama_skills
    from creator.errors import DomainError

    p = tmp_path / "vendor/skills"
    p.mkdir(parents=True)
    (p / "registry.json").write_text(
        json.dumps({"files": {"vendor/skills/missing.txt": "invalid"}, "skills": [], "version": "test"})
    )
    monkeypatch.setattr(drama_skills, "ROOT", tmp_path)
    with pytest.raises(DomainError, match="内置技能"):
        drama_skills.registry()


def test_schema_and_registry_require_login(client):
    assert client.get("/api/v1/dramas/skills").status_code == 401
    assert client.get("/api/v1/dramas").status_code == 401


@pytest.mark.parametrize("outcome", ["valid", "invalid", "unknown", "stale"])
def test_budgeted_model_is_once_only_and_never_overwrites_edit(
    client, user, brand, creator_profile, drama_plan, monkeypatch, outcome
):
    import json
    from sqlalchemy import select
    from creator.db import SessionLocal
    from creator.models import BudgetEntry, Creator, DramaProject, Run, VideoGenerationJob
    from creator import drama_jobs
    from creator.errors import DomainError
    from creator.jobs import process_pending
    from test_model_workspace import configure

    configure(client)
    with SessionLocal() as db:
        db.get(Creator, creator_profile["id"]).model_consent = True
        db.commit()
    uri = prepare(client, brand, drama_plan)
    body = {
        "expected_revision": 2,
        "confirmed": True,
        "creator_id": creator_profile["id"],
        "max_cost_cents": 100,
    }
    queued = client.post(uri + "/plan-ai", json=body, headers={"Idempotency-Key": "drama-model-one"})
    assert queued.status_code == 201, queued.text
    calls = []

    def reply(settings, prompts):
        data = json.loads(prompts[1]["content"])
        assert len(data["skills"]) == 8
        assert "test-private-model-value" not in json.dumps(prompts)
        calls.append(1)
        if outcome == "unknown":
            raise DomainError("AGENT_PROVIDER_RESULT_UNKNOWN", "synthetic unknown")
        if outcome == "stale":
            with SessionLocal() as db:
                item = db.get(DramaProject, uri.rsplit("/", 1)[-1])
                item.revision += 1
                db.commit()
        return {
            "choices": [{"message": {"content": json.dumps(drama_plan if outcome != "invalid" else {})}}],
            "usage": {"prompt_tokens": 20, "completion_tokens": 10},
        }

    monkeypatch.setattr(drama_jobs, "complete", reply)
    with SessionLocal() as db:
        process_pending(db)
        process_pending(db)
        run = db.get(Run, queued.json()["id"])
        ledger = db.scalar(select(BudgetEntry).where(BudgetEntry.run_id == run.id))
        assert ledger.status == ("reserved" if outcome == "unknown" else "settled")
        if outcome != "unknown":
            assert run.release["drama_model_receipt"]["usage"] == {
                "prompt_tokens": 20,
                "completion_tokens": 10,
            }
        if outcome == "valid":
            assert run.status == "completed"
        else:
            assert run.status == "failed"
        assert db.scalar(select(VideoGenerationJob)) is None
    assert calls == [1]
    assert (
        "input_snapshot"
        not in client.get("/api/v1/creator-runs/" + queued.json()["id"] + "/diagnostic").json()["run"]
    )
    current = client.get(uri).json()["project"]
    assert current["confirmation"] == ({} if outcome == "valid" else current["confirmation"])


def test_story_continuity_pipeline_builds_existing_ir_with_silent_reaction(
    client, user, brand, drama_plan, monkeypatch, tmp_path
):
    """Synthetic video is a contract test, not AI art-quality evidence."""
    from creator import wan_comfy
    from creator.db import SessionLocal
    from creator.domains import store_file
    from creator.models import Asset, VideoGenerationJob
    from creator.video import ffmpeg
    from creator.video_generation import _source_current
    from creator import narration

    monkeypatch.setattr(
        wan_comfy, "snapshot", lambda: {"model_id": "synthetic-only", "version": wan_comfy.VERSION}
    )
    image = image_asset(client, brand)
    # One quiet reaction, with the other lines long enough for the target range.
    drama_plan["shots"][1]["narration"] = ""
    drama_plan["shots"][0]["narration"] = "另一个方案也能用，当时为什么选它？"
    for s in drama_plan["shots"]:
        s["reference_asset_id"] = image["id"]
    uri = prepare(client, brand, drama_plan)
    media = tmp_path / "synthetic.mp4"
    ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            "color=c=navy:s=1280x704:r=24",
            "-frames:v",
            "121",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            str(media),
        ]
    )
    for shot in drama_plan["shots"]:
        response = client.post(
            uri + f"/shots/{shot['id']}/generate", json={"expected_revision": 2, "confirmed": True}
        )
        assert response.status_code == 201, response.text
        with SessionLocal() as db:
            job = db.get(VideoGenerationJob, response.json()["id"])
            _source_current(db, job)
            sha, suffix = store_file(job.workspace_id, media.read_bytes(), ".mp4"), ".mp4"
            asset = Asset(
                workspace_id=job.workspace_id,
                brand_id=brand["id"],
                name="synthetic",
                kind="video",
                sha256=sha,
                suffix=suffix,
                source="synthetic contract",
                license_note="synthetic fixture",
                verified=True,
            )
            db.add(asset)
            db.flush()
            job.output_asset_id, job.status = asset.id, "completed"
            job.receipt = {"art_review": "user_confirmed", "output_sha256": sha}
            db.commit()
    captured = []
    monkeypatch.setattr(
        narration, "enqueue", lambda db, video, data, *args: captured.append(data.model_dump())
    )
    body = {
        "expected_revision": 2,
        "confirmed": True,
        "narration": {"voice_id": "synthetic-test", "fit_mode": "fixed", "usage_confirmed": True},
    }
    built = client.post(uri + "/build", json=body)
    assert built.status_code == 201, built.text
    assert captured[0]["lines"][1]["text"] == ""
    video = client.get("/api/v1/videos/projects/" + built.json()["video_id"]).json()
    assert len(video["ir"]["shots"]) == 4
    assert all(s["provider"] == "comfy_wan" and s["generation_job_id"] for s in video["ir"]["shots"])
    assert client.post(uri + "/build", json=body).json()["video_id"] == built.json()["video_id"]
    assert len(captured) == 1
    assert client.post("/api/v1/videos/" + video["id"] + "/render").status_code == 409
