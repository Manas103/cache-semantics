"""Recheck positions 1, 8, 16, 24, 32, 40, 45 for DeepSeek.

deepseek_full_sweep.py reused their rep-0 values from deepseek_chunk_sweep.py,
but those came out of a multi-condition run (control, then 7 edited
conditions in sequence, each priming+measuring 5x) -- and the resulting
values don't fit the smooth monotonic pattern the other 38 fresh positions
show (e.g. tool#16=1152 is LESS than tool#15=2048, which can't be right if
everything before an edit point survives). Consistent with the OpenAI sweep's
self-hit contamination bug: earlier conditions in that run left order-
dependent state in DeepSeek's persistent, content-addressed disk cache that
confounded later conditions' readings.

This retests all 7 positions completely in isolation (nothing else touching
DeepSeek in this process), one at a time, with a fresh substitution word
("Supplies") never before sent to DeepSeek at these positions.
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
POSITIONS = [1, 8, 16, 24, 32, 40, 45]


def variant_for_tool(i, blocks, header):
    b = list(blocks)
    b[i] = b[i].replace("Retrieves a structured record", "Supplies a structured record", 1)
    return _build(header, b)


def main():
    load_dotenv()
    header = _header()
    blocks = _blocks(45)
    base = _build(header, blocks)

    client = CacheProbeClient(model="deepseek-chat", base_url=DEEPSEEK_BASE,
                                api_key_env="DEEPSEEK_API_KEY")

    results = {}
    for tool_num in POSITIONS:
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
        results[str(tool_num)] = dict(cached=cached, total=total)
        time.sleep(2)

    with open("deepseek_recheck_outliers.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print("\nWrote deepseek_recheck_outliers.json")


if __name__ == "__main__":
    sys.exit(main())
