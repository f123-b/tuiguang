"""One explicit request shape for compatible gateways. Never retry billable calls."""

import json
import math

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
        return result
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise DomainError("AGENT_PROVIDER_RESULT_UNKNOWN", "模型结果或费用待核对，未自动重试") from None


def cost(settings, usage):
    return math.ceil(
        (
            usage["prompt_tokens"] * settings["input_price"]
            + usage["completion_tokens"] * settings["output_price"]
        )
        / 1_000_000
    )
