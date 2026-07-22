"""Characterize Gemini implicit-cache hit-rate variance on a byte-identical
repeat. The sanity check saw one run cache ~93% of tokens and another run
cache 0% on the exact same prefix -- need repeated samples to know if that's
real instability or a one-off fluke (e.g. TTL expiry, backend rebalancing).

Cost: N calls, ~7.7k input tokens each, max_tokens=20. Cheap.
"""

from __future__ import annotations

import json
import sys
import time

from client import CacheProbeClient, load_dotenv
from prefix import make_prefix, make_suffix

GEMINI_DIRECT_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"


def main():
    load_dotenv()
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    gap = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0

    prefix = make_prefix()
    suffix = make_suffix()
    client = CacheProbeClient(model="gemini-2.5-flash", base_url=GEMINI_DIRECT_BASE,
                                api_key_env="GEMINI_API_KEY")

    results = []
    for i in range(n):
        usage, finish, raw = client.call(prefix, suffix, cache_control=False)
        details = usage.get("prompt_tokens_details") or {}
        cached = details.get("cached_tokens", 0)
        prompt = usage.get("prompt_tokens", 0)
        pct = (cached / prompt * 100) if prompt else 0.0
        print(f"  call {i}: cached={cached}/{prompt} ({pct:.1f}%)")
        results.append({"i": i, "cached_tokens": cached, "prompt_tokens": prompt, "pct": pct})
        if i < n - 1:
            time.sleep(gap)

    with open("gemini_stability_results.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    hits = sum(1 for r in results if r["cached_tokens"] > 0)
    print(f"\n{hits}/{n} calls showed nonzero cache hit")
    print("Wrote gemini_stability_results.json")


if __name__ == "__main__":
    sys.exit(main())
