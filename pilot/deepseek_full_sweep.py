"""Single-shot 45-position sweep for DeepSeek direct, completing deepseek_chunk_sweep.py.

That earlier script showed DeepSeek's cache is disk-persisted and
content-addressed globally: once an edited variant is sent once, repeating
the identical (prime, measure) pair just self-hits the variant's own past
occurrence at ~full credit, rather than re-measuring overlap with the base.
So only rep 0 of each condition there was a clean reading -- the repeated-
trial design that worked for Gemini's transient/replica-scoped cache does
not work for DeepSeek's persistent one.

This does ONE prime+measure per position, never repeating a (position, word)
pair, across the 38 positions not already cleanly measured (1, 8, 16, 24,
32, 40, 45 already have clean single-shot values from deepseek_chunk_sweep.py
rep 0 and are skipped here to avoid self-hit contamination).

Cost: 38 positions x 2 calls, ~7.1k input tokens each -- a few cents.
"""

from __future__ import annotations

import json
import sys
import time

from client import CacheProbeClient, load_dotenv
from perturbations import _blocks, _build, _header

DEEPSEEK_BASE = "https://api.deepseek.com"
SUFFIX = "In one word, what is the primary key field called in these tools?"
GAP = 2.5

ALREADY_CLEAN = {
    1: 0, 8: 0, 16: 1152, 24: 2304, 32: 3584, 40: 4864, 45: 6016,
}


def variant_for_tool(i, blocks, header):
    b = list(blocks)
    b[i] = b[i].replace("Retrieves a structured record", "Yields a structured record", 1)
    return _build(header, b)


def main():
    load_dotenv()
    header = _header()
    blocks = _blocks(45)
    base = _build(header, blocks)

    client = CacheProbeClient(model="deepseek-chat", base_url=DEEPSEEK_BASE,
                                api_key_env="DEEPSEEK_API_KEY")

    results = {str(k): dict(cached=v, total=None, source="rep0_reuse") for k, v in ALREADY_CLEAN.items()}

    for tool_num in range(1, 46):
        if tool_num in ALREADY_CLEAN:
            continue
        variant = variant_for_tool(tool_num - 1, blocks, header)
        try:
            client.call(base, SUFFIX, cache_control=False)
            time.sleep(GAP)
            usage, _, _ = client.call(variant, SUFFIX, cache_control=False)
        except RuntimeError as e:
            print(f"tool#{tool_num:2d}: ERROR {e}")
            continue
        cached = usage.get("prompt_cache_hit_tokens", 0)
        total = usage.get("prompt_tokens", 0)
        print(f"tool#{tool_num:2d}: cached={cached:6d}/{total:6d}")
        results[str(tool_num)] = dict(cached=cached, total=total, source="fresh")
        time.sleep(1)

    with open("deepseek_full_sweep_results.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print("\nWrote deepseek_full_sweep_results.json")


if __name__ == "__main__":
    sys.exit(main())
