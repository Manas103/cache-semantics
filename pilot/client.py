"""Minimal OpenAI-compatible client for prompt-cache telemetry probing.

Unlike tzarith's runner.py (which only needs prompt/completion token counts),
this needs the full ``usage`` object -- cached_tokens, cache_write_tokens, and
whatever provider-specific cache fields ride along -- plus structured message
content so Anthropic's explicit ``cache_control`` breakpoint can be attached.
Stdlib-only (urllib), same .env walk-up convention as dst-bench.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request


def load_dotenv():
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(4):
        path = os.path.join(d, ".env")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
            return path
        d = os.path.dirname(d)
    return None


class CacheProbeClient:
    def __init__(self, model, base_url, api_key_env, max_tokens=20, timeout=120,
                 max_retries=5, extra_headers=None, max_tokens_param="max_tokens",
                 send_temperature=True):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = os.environ.get(api_key_env, "")
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries
        self.extra_headers = extra_headers or {}
        self.max_tokens_param = max_tokens_param
        self.send_temperature = send_temperature
        if not self.api_key:
            raise RuntimeError(f"environment variable {api_key_env} is not set")

    def call(self, system_prefix: str, user_suffix: str, cache_control: bool = False,
              session_id: str | None = None, max_tokens: int | None = None):
        """One request. Returns (raw_usage_dict, finish_reason)."""
        system_content = [{"type": "text", "text": system_prefix}]
        if cache_control:
            system_content[0]["cache_control"] = {"type": "ephemeral"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_suffix},
            ],
            self.max_tokens_param: max_tokens if max_tokens is not None else self.max_tokens,
        }
        if self.send_temperature:
            payload["temperature"] = 0.0
        if session_id:
            payload["session_id"] = session_id
        body = json.dumps(payload).encode()
        headers = {"Authorization": f"Bearer {self.api_key}",
                   "Content-Type": "application/json"}
        headers.update(self.extra_headers)
        req = urllib.request.Request(f"{self.base_url}/chat/completions", data=body,
                                      headers=headers)
        last_err = None
        for attempt in range(self.max_retries):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read())
                usage = data.get("usage") or {}
                finish = (data.get("choices") or [{}])[0].get("finish_reason")
                return usage, finish, data
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", "replace")[:600]
                last_err = f"HTTP {e.code}: {err_body}"
                if e.code == 429 or e.code >= 500:
                    time.sleep(min(30, 4 * 2 ** attempt))
                    continue
                raise RuntimeError(last_err)
            except (urllib.error.URLError, TimeoutError) as e:
                last_err = str(e)
                time.sleep(2 ** attempt)
        raise RuntimeError(f"exhausted {self.max_retries} retries: {last_err}")


class AnthropicNativeClient:
    """Anthropic's native /v1/messages endpoint.

    The OpenAI-compatible /v1/chat/completions shim on api.anthropic.com
    silently drops cache_creation_input_tokens/cache_read_input_tokens from
    its usage object even when cache_control is honored server-side -- so
    this is required to get real direct-Anthropic cache telemetry.
    """

    BASE_URL = "https://api.anthropic.com/v1"
    ANTHROPIC_VERSION = "2023-06-01"

    def __init__(self, model, api_key_env="ANTHROPIC_API_KEY", max_tokens=20,
                 timeout=120, max_retries=5, send_temperature=True):
        self.model = model
        self.api_key = os.environ.get(api_key_env, "")
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries
        self.send_temperature = send_temperature
        if not self.api_key:
            raise RuntimeError(f"environment variable {api_key_env} is not set")

    def call(self, system_prefix: str, user_suffix: str, cache_control: bool = False,
              max_tokens: int | None = None):
        """One request, single system block. Returns (usage, stop_reason, raw_data)."""
        system_content = [{"type": "text", "text": system_prefix}]
        if cache_control:
            system_content[0]["cache_control"] = {"type": "ephemeral"}
        return self._post(system_content, user_suffix, max_tokens)

    def call_multiblock(self, blocks: list[tuple[str, bool]], user_suffix: str,
                          max_tokens: int | None = None):
        """One request, system built from multiple independently-markable blocks.

        blocks is a list of (text, cache_control) pairs -- tests whether an
        earlier block's cache survives when only a later block changes
        (hierarchical/incremental caching), vs. everything living in one
        atomic block.
        """
        system_content = []
        for text, cc in blocks:
            block = {"type": "text", "text": text}
            if cc:
                block["cache_control"] = {"type": "ephemeral"}
            system_content.append(block)
        return self._post(system_content, user_suffix, max_tokens)

    def _post(self, system_content, user_suffix, max_tokens):
        payload = {
            "model": self.model,
            "system": system_content,
            "messages": [{"role": "user", "content": user_suffix}],
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
        }
        if self.send_temperature:
            payload["temperature"] = 0.0
        body = json.dumps(payload).encode()
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }
        req = urllib.request.Request(f"{self.BASE_URL}/messages", data=body, headers=headers)
        last_err = None
        for attempt in range(self.max_retries):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read())
                usage = data.get("usage") or {}
                stop_reason = data.get("stop_reason")
                return usage, stop_reason, data
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", "replace")[:600]
                last_err = f"HTTP {e.code}: {err_body}"
                if e.code == 429 or e.code >= 500:
                    time.sleep(min(30, 4 * 2 ** attempt))
                    continue
                raise RuntimeError(last_err)
            except (urllib.error.URLError, TimeoutError) as e:
                last_err = str(e)
                time.sleep(2 ** attempt)
        raise RuntimeError(f"exhausted {self.max_retries} retries: {last_err}")
