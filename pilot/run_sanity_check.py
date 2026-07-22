"""Positive-control sanity check, run BEFORE any full pilot spend.

For each provider config: call twice with a byte-identical prefix (cold write,
then warm read) and print the raw usage telemetry. Confirms (a) caching
actually triggers and is visible in the usage object, and (b) OpenRouter's
pass-through numbers for Gemini match a direct Gemini call -- the proxy-
validity cross-check.

Cost: 8 calls total (4 configs x 2), ~7.7k input tokens each, max_tokens=20.
Should be a fraction of a cent to a few cents total.
"""

from __future__ import annotations

import json
import sys
import time

from client import AnthropicNativeClient, CacheProbeClient, load_dotenv
from prefix import make_prefix, make_suffix

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
GEMINI_DIRECT_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"

ANTHROPIC_DIRECT_BASE = "https://api.anthropic.com/v1"

CONFIGS = [
    dict(label="openrouter/anthropic-haiku", base_url=OPENROUTER_BASE,
         api_key_env="OPENROUTER_API_KEY", model="anthropic/claude-haiku-4.5",
         cache_control=True),
    dict(label="direct/anthropic-haiku", base_url=ANTHROPIC_DIRECT_BASE,
         api_key_env="ANTHROPIC_API_KEY", model="claude-haiku-4-5-20251001",
         cache_control=True, native=True),
    dict(label="openrouter/openai-gpt5-mini", base_url=OPENROUTER_BASE,
         api_key_env="OPENROUTER_API_KEY", model="openai/gpt-5-mini",
         cache_control=False, max_tokens=500),
    dict(label="openrouter/gemini-2.5-flash", base_url=OPENROUTER_BASE,
         api_key_env="OPENROUTER_API_KEY", model="google/gemini-2.5-flash",
         cache_control=False),
    dict(label="direct/gemini-2.5-flash", base_url=GEMINI_DIRECT_BASE,
         api_key_env="GEMINI_API_KEY", model="gemini-2.5-flash",
         cache_control=False),
]


def main():
    load_dotenv()
    prefix = make_prefix()
    suffix = make_suffix()
    print(f"prefix chars={len(prefix)}\n")

    only = sys.argv[1] if len(sys.argv) > 1 else None
    configs = [c for c in CONFIGS if not only or only in c["label"]]

    results = {}
    for cfg in configs:
        label = cfg["label"]
        print(f"=== {label} (model={cfg['model']}) ===")
        native = cfg.get("native", False)
        try:
            if native:
                client = AnthropicNativeClient(model=cfg["model"], api_key_env=cfg["api_key_env"])
            else:
                client = CacheProbeClient(model=cfg["model"], base_url=cfg["base_url"],
                                            api_key_env=cfg["api_key_env"])
        except RuntimeError as e:
            print(f"  SKIP: {e}\n")
            continue
        # session_id is an OpenRouter-specific sticky-routing hint; a direct
        # provider endpoint may reinterpret the same field name differently.
        session_id = f"cache-sanity-{label}" if "openrouter.ai" in cfg["base_url"] else None
        call_max_tokens = cfg.get("max_tokens")
        call_kwargs = dict(cache_control=cfg["cache_control"], max_tokens=call_max_tokens)
        if not native:
            call_kwargs["session_id"] = session_id
        try:
            usage1, finish1, raw1 = client.call(prefix, suffix, **call_kwargs)
            print(f"  call 1 (cold) usage: {json.dumps(usage1)}")
            if not usage1:
                print(f"  call 1 RAW (debug): {json.dumps(raw1)[:800]}")
            time.sleep(2)
            usage2, finish2, raw2 = client.call(prefix, suffix, **call_kwargs)
            print(f"  call 2 (warm) usage: {json.dumps(usage2)}")
            if not usage2:
                print(f"  call 2 RAW (debug): {json.dumps(raw2)[:800]}")
            results[label] = {"cold": usage1, "warm": usage2}
        except RuntimeError as e:
            print(f"  ERROR: {e}")
        print()

    out_path = "sanity_results.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    sys.exit(main())
