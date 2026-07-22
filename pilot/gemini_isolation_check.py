"""Does Gemini's per-position credit variance survive in isolation, or was it
an artifact of the chunk-sweep script priming with the same "base" text
across 8 different conditions in one run (no session pinning on direct
Gemini, so a later condition's measure call could land on a backend that
cached "base" from an earlier condition's prime, not its own)?

Repeats a single fixed edit (tool#24, "Provides" substitution -- the exact
condition that showed 3061/7143/7143/3061/3061 in the multi-condition
sweep) in complete isolation: nothing else touches Gemini in this process,
generous 5s gaps. If the variance disappears here, it was leakage. If it
persists, it's a real property of Gemini's caching infrastructure.

Cost: 12 reps x 2 calls, ~7.7k input tokens each.
"""

from __future__ import annotations

import json
import sys
import time

from client import CacheProbeClient, load_dotenv
from perturbations import _blocks, _build, _header

GEMINI_DIRECT_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"
SUFFIX = "In one word, what is the primary key field called in these tools?"
GAP = 5.0
REPS = 12
TOOL_NUM = 24


def main():
    load_dotenv()
    header = _header()
    blocks = _blocks(45)
    base = _build(header, blocks)

    b = list(blocks)
    b[TOOL_NUM - 1] = b[TOOL_NUM - 1].replace("Retrieves a structured record", "Provides a structured record", 1)
    variant = _build(header, b)

    client = CacheProbeClient(model="gemini-2.5-flash", base_url=GEMINI_DIRECT_BASE,
                                api_key_env="GEMINI_API_KEY")

    results = []
    for r in range(REPS):
        try:
            client.call(base, SUFFIX, cache_control=False)
            time.sleep(GAP)
            usage, _, _ = client.call(variant, SUFFIX, cache_control=False)
        except RuntimeError as e:
            print(f"  rep {r}: ERROR {e}")
            continue
        details = usage.get("prompt_tokens_details") or {}
        cached = details.get("cached_tokens", 0)
        total = usage.get("prompt_tokens", 0)
        print(f"  rep {r:2d}: cached={cached:6d}/{total:6d}")
        results.append(dict(rep=r, cached=cached, total=total))
        time.sleep(2)

    with open("gemini_isolation_results.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    vals = sorted(set(x["cached"] for x in results))
    print(f"\ndistinct cached values observed: {vals}")
    print("Wrote gemini_isolation_results.json")


if __name__ == "__main__":
    sys.exit(main())
