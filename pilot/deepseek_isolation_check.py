"""Determinism check for DeepSeek, mirroring gemini_isolation_check.py.

The Gemini isolation check repeated one fixed edited condition 12x in
isolation and still saw 3 recurring discrete outcomes (0/3061/7143) --
real non-determinism. Incidental data from deepseek_chunk_sweep.py's rep
1-4 (self-hits) suggested DeepSeek returns bit-for-bit identical cache
credit on every repeat of identical text, with zero variance. This
confirms that deliberately, using the already-cached tool#24 "Supplies"
variant from deepseek_recheck_outliers.py (so this is a clean self-hit
repeat, not a fresh prime -- which is exactly the condition we want to
test: does an already-cached prefix reliably hit every time?).

8 reps, 4s gaps, nothing else touching DeepSeek in this process.
"""

from __future__ import annotations

import json
import sys
import time

from client import CacheProbeClient, load_dotenv
from perturbations import _blocks, _build, _header

DEEPSEEK_BASE = "https://api.deepseek.com"
SUFFIX = "In one word, what is the primary key field called in these tools?"
GAP = 4.0
REPS = 8
TOOL_NUM = 24


def main():
    load_dotenv()
    header = _header()
    blocks = _blocks(45)
    b = list(blocks)
    b[TOOL_NUM - 1] = b[TOOL_NUM - 1].replace("Retrieves a structured record", "Supplies a structured record", 1)
    variant = _build(header, b)

    client = CacheProbeClient(model="deepseek-chat", base_url=DEEPSEEK_BASE,
                                api_key_env="DEEPSEEK_API_KEY")

    results = []
    for r in range(REPS):
        try:
            usage, _, _ = client.call(variant, SUFFIX, cache_control=False)
        except RuntimeError as e:
            print(f"  rep {r}: ERROR {e}")
            continue
        cached = usage.get("prompt_cache_hit_tokens", 0)
        total = usage.get("prompt_tokens", 0)
        print(f"  rep {r}: cached={cached:6d}/{total:6d}")
        results.append(dict(rep=r, cached=cached, total=total))
        time.sleep(GAP)

    with open("deepseek_isolation_results.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    vals = sorted(set(x["cached"] for x in results))
    print(f"\ndistinct cached values observed: {vals}")
    print("Wrote deepseek_isolation_results.json")


if __name__ == "__main__":
    sys.exit(main())
