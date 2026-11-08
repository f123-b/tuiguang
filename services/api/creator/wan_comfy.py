"""Pinned, loopback-only ComfyUI adapter. No arbitrary graph or cloud endpoint."""

from functools import lru_cache
import hashlib
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

import httpx

from .errors import DomainError

VERSION = "wan_comfy_local@1"
WORKFLOW_VERSION = "wan_ti2v_fixed@2"
ENGINE_REVISION = "0decb39ee5b5e17c200334589fc317dbbe98310e"
MODEL_ID = "Comfy-Org/Wan_2.2_ComfyUI_Repackaged"
REVISION = "ee6f4a40737a995bf5818954cfce6d59443b0f04"
MODEL_FILES = {
    "diffusion_models/wan2.2_ti2v_5B_fp16.safetensors": (
        9999658848,
        "456f901338bd9eadbded3828b819109a9b68e8a525ca5cf8d0049a69fcfeca1e",
    ),
    "text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors": (
        6735906897,
        "c3355d30191f1f066b26d93fba017ae9809dce6c627dda5f6a66eaa651204f68",
    ),
    "vae/wan2.2_vae.safetensors": (
        1409400960,
        "e40321bd36b9709991dae2530eb4ac303dd168276980d3e9bc4b6e2b75fed156",
    ),
}


def base_url():
    value = os.getenv("VIDEO_GEN_BASE_URL", "").rstrip("/")
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError:
        raise DomainError("GEN_PROVIDER_UNAVAILABLE", "本机视频服务地址不正确", 422) from None
    if (
        parts.scheme != "http"
        or parts.hostname != "127.0.0.1"
        or not port
        or parts.username
        or parts.password
        or parts.path
        or parts.query
        or parts.fragment
    ):
        raise DomainError("GEN_PROVIDER_UNAVAILABLE", "请先配置本机127.0.0.1上的视频生成服务", 422)
    return value


@lru_cache(maxsize=16)
def _model_hash(path, size, modified, changed):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024**2), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot():
    url = base_url()
    directory = Path(os.getenv("VIDEO_GEN_MODEL_DIR", "__not_configured__"))
    hashes = {}
    for name, (size, expected) in MODEL_FILES.items():
        path = directory / name
        if not path.is_file() or path.stat().st_size != size:
            raise DomainError("GEN_MODEL_FILES_MISSING", "本机视频模型尚未下载或校验完成", 422)
        stat = path.stat()
        actual = _model_hash(str(path.resolve()), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
        if actual != expected:
            raise DomainError("GEN_MODEL_HASH_MISMATCH", "视频模型字节与已冻结版本不一致，请检查安装", 422)
        hashes[name] = actual
    try:
        with httpx.Client(base_url=url, timeout=4, follow_redirects=False, trust_env=False) as client:
            info = {}
            for node in (
                "UNETLoader",
                "CLIPLoader",
                "VAELoader",
                "Wan22ImageToVideoLatent",
                "LoadImage",
                "CLIPTextEncode",
                "ModelSamplingSD3",
                "KSampler",
                "VAEDecode",
                "SaveWEBM",
            ):
                response = client.get("/object_info/" + node)
                response.raise_for_status()
                body = response.json()
                if node not in body:
                    raise ValueError("missing native node")
                info[node] = body[node]
            for node, key, name in (
                ("UNETLoader", "unet_name", "wan2.2_ti2v_5B_fp16.safetensors"),
                ("CLIPLoader", "clip_name", "umt5_xxl_fp8_e4m3fn_scaled.safetensors"),
                ("VAELoader", "vae_name", "wan2.2_vae.safetensors"),
            ):
                if name not in info[node]["input"]["required"][key][0]:
                    raise ValueError("model path not registered")
            stats = client.get("/system_stats")
            stats.raise_for_status()
            system = stats.json().get("system", {})
            version = system.get("comfyui_version", "unknown")
            if version != "0.44.0":
                raise ValueError("unexpected engine version")
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise DomainError("GEN_PROVIDER_UNAVAILABLE", "本机视频服务或固定工作流节点尚未就绪", 422) from None
    return {
        "version": VERSION,
        "workflow_version": WORKFLOW_VERSION,
        "model_id": MODEL_ID,
        "model_revision": REVISION,
        "model_sha256": hashes,
        "comfyui_version": version,
        "engine_revision": ENGINE_REVISION,
        "pytorch_version": system.get("pytorch_version", "unknown"),
        "runtime_flags": [
            arg
            for arg in system.get("argv", [])
            if arg
            in (
                "--cpu-vae",
                "--fp16-vae",
                "--fp32-vae",
                "--bf16-vae",
                "--fp16-unet",
                "--bf16-unet",
                "--fp8_e4m3fn-unet",
                "--disable-dynamic-vram",
                "--lowvram",
                "--cache-none",
            )
        ],
    }


def capabilities():
    try:
        model = snapshot()
        return {
            "version": VERSION,
            "available": True,
            "styles": ["realistic", "anime"],
            "reason": None,
            "model": model,
            "local_only": True,
        }
    except DomainError as exc:
        return {
            "version": VERSION,
            "available": False,
            "styles": ["realistic", "anime"],
            "reason": exc.message,
            "error_code": exc.code,
            "local_only": True,
        }


def workflow(data, image, identifier):
    if not re.fullmatch(r"[a-f0-9]{32}", identifier) or not re.fullmatch(
        r"creator_ref_[a-f0-9]{32}\.png", image
    ):
        raise DomainError("GEN_INPUT_INVALID", "生成引用格式不正确", 422)
    style = (
        "Photorealistic live-action cinematic scene. Natural human motion and subtle expressions. "
        if data["style"] == "realistic"
        else "Consistent 2D animated character, expressive anime scene, natural character motion. "
    )
    negative = "色调艳丽，过曝，细节模糊不清，字幕，整体发灰，最差质量，低质量，JPEG压缩残留，丑陋，残缺，多余的手指，画得不好的手部，画得不好的脸部，畸形，毁容，形态畸形的肢体，手指融合，杂乱的背景，闪烁，背景变形，颜色漂移，水印"
    return {
        "model": {
            "class_type": "UNETLoader",
            "inputs": {"unet_name": "wan2.2_ti2v_5B_fp16.safetensors", "weight_dtype": "default"},
        },
        "clip": {
            "class_type": "CLIPLoader",
            "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "cpu"},
        },
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": "wan2.2_vae.safetensors"}},
        "image": {"class_type": "LoadImage", "inputs": {"image": image}},
        "positive": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["clip", 0], "text": style + data["prompt"]},
        },
        "negative": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": negative}},
        "latent": {
            "class_type": "Wan22ImageToVideoLatent",
            "inputs": {
                "vae": ["vae", 0],
                "width": data["width"],
                "height": data["height"],
                "length": data["frames"],
                "batch_size": 1,
                "start_image": ["image", 0],
            },
        },
        "shift": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["model", 0], "shift": 8}},
        "sample": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["shift", 0],
                "seed": data["seed"],
                "steps": 20,
                "cfg": 5,
                "sampler_name": "uni_pc",
                "scheduler": "simple",
                "positive": ["positive", 0],
                "negative": ["negative", 0],
                "latent_image": ["latent", 0],
                "denoise": 1,
            },
        },
        "decode": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["sample", 0], "vae": ["vae", 0]},
        },
        "save": {
            "class_type": "SaveWEBM",
            "inputs": {
                "images": ["decode", 0],
                "filename_prefix": "creator_jobs/" + identifier,
                "codec": "vp9",
                "fps": 24,
                "crf": 18,
            },
        },
    }


class Client:
    def __init__(self):
        self.http = httpx.Client(base_url=base_url(), timeout=30, follow_redirects=False, trust_env=False)

    def close(self):
        self.http.close()

    def upload(self, identifier, image):
        filename = f"creator_ref_{identifier}.png"
        try:
            response = self.http.post(
                "/upload/image",
                files={"image": (filename, image, "image/png")},
                data={"overwrite": "true", "type": "input"},
            )
            response.raise_for_status()
            if response.json().get("name") != filename:
                raise ValueError("unexpected upload name")
        except (httpx.HTTPError, ValueError):
            raise DomainError(
                "GEN_REFERENCE_UPLOAD_FAILED", "本地参考图写入失败，尚未提交生成", 422
            ) from None
        return filename

    def submit(self, graph, identifier):
        try:
            response = self.http.post("/prompt", json={"prompt": graph, "client_id": identifier})
        except httpx.HTTPError:
            raise DomainError(
                "GEN_SUBMISSION_UNKNOWN", "生成提交回执未知，软件不会自动重复提交", 409
            ) from None
        if response.status_code == 400:
            raise DomainError("GEN_WORKFLOW_REJECTED", "本地工作流校验未通过，请检查模型与节点", 422)
        try:
            response.raise_for_status()
            identifier = response.json()["prompt_id"]
            if not isinstance(identifier, str) or not re.fullmatch(r"[a-zA-Z0-9-]{1,120}", identifier):
                raise ValueError("invalid prompt id")
            return identifier
        except (httpx.HTTPError, ValueError, KeyError):
            raise DomainError(
                "GEN_SUBMISSION_UNKNOWN", "生成提交回执未知，软件不会自动重复提交", 409
            ) from None

    def history(self, prompt_id):
        try:
            response = self.http.get("/history/" + prompt_id)
            response.raise_for_status()
            return response.json().get(prompt_id)
        except (httpx.HTTPError, ValueError):
            raise DomainError(
                "GEN_STATUS_UNKNOWN", "本地生成状态暂不可确认，保留任务回执等待检查", 409
            ) from None

    def metrics(self):
        try:
            response = self.http.get("/system_stats")
            response.raise_for_status()
            body = response.json()
            return [
                {
                    key: d.get(key)
                    for key in ("type", "vram_total", "vram_free", "torch_vram_total", "torch_vram_free")
                }
                for d in body.get("devices", [])
            ]
        except (httpx.HTTPError, ValueError, TypeError):
            return None

    def download(self, item, target, identifier):
        filename, folder = item.get("filename", ""), item.get("subfolder", "")
        if (
            not re.fullmatch(re.escape(identifier) + r"_[0-9_]+\.webm", filename)
            or folder != "creator_jobs"
            or item.get("type") != "output"
        ):
            raise DomainError("GEN_OUTPUT_INVALID", "本地服务返回了不属于本镜头的文件", 422)
        total = 0
        try:
            with self.http.stream(
                "GET", "/view", params={"filename": filename, "subfolder": folder, "type": "output"}
            ) as response:
                response.raise_for_status()
                with target.open("wb") as output:
                    for chunk in response.iter_bytes(1024**2):
                        total += len(chunk)
                        if total > 160 * 1024**2:
                            raise DomainError("GEN_OUTPUT_INVALID", "生成结果超出本地片段上限", 422)
                        output.write(chunk)
        except httpx.HTTPError:
            raise DomainError("GEN_OUTPUT_UNAVAILABLE", "生成结果暂不可读取，不会重新生成", 409) from None
        return total

    def free_models(self):
        try:
            self.http.post("/free", json={"unload_models": True, "free_memory": True})
        except httpx.HTTPError:
            pass
