"""One explicit request shape for compatible gateways. Never retry billable calls."""

import json
import math
from urllib.parse import urlsplit

import httpx

from .errors import DomainError


def payload(settings, messages, max_tokens=None):
    result = {
        "model": settings["model"],
        "messages": messages,
        settings.get("token_parameter", "max_tokens"): max_tokens or settings["max_tokens"],
    }
    if settings.get("json_mode", True):
        result["response_format"] = {"type": "json_object"}
    # These documented DeepSeek models think by default. Fixed JSON workflows
    # use non-thinking mode so the output cap is available to the JSON answer.
    if urlsplit(settings["base_url"]).hostname == "api.deepseek.com" and settings["model"] in (
        "deepseek-flash",
        "deepseek-v4-pro",
        "deepseek-v4-flash",
    ):
        result["thinking"] = {"type": "disabled"}
    return result


def complete(settings, messages, max_tokens=None):
    try:
        with httpx.Client(timeout=60, follow_redirects=False) as client:
            response = client.post(
                settings["base_url"] + "/chat/completions",
                headers={"Authorization": "Bearer " + settings["key"]},
                json=payload(settings, messages, max_tokens),
            )
        response.raise_for_status()
        if len(response.content) > 2 * 1024 * 1024:
            raise ValueError("response too large")
        result = response.json()
        if settings["key"] in json.dumps(result, ensure_ascii=False):
            raise ValueError("credential echo")
        usage = result["usage"]
        if any(type(usage.get(k)) is not int or usage[k] < 0 for k in ("prompt_tokens", "completion_tokens")):
            raise ValueError("usage")
        answer = result["choices"][0]["message"]["content"]
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("missing answer")
        return result
    except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError):
        raise DomainError("AGENT_PROVIDER_RESULT_UNKNOWN", "模型结果或费用待核对，未自动重试") from None


def cost(settings, usage):
    return math.ceil(
        (
            usage["prompt_tokens"] * settings["input_price"]
            + usage["completion_tokens"] * settings["output_price"]
        )
        / 1_000_000
    )
