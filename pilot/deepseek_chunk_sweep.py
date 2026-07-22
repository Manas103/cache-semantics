"""Repeated-trial chunk-boundary sweep for DeepSeek direct (api.deepseek.com).

DeepSeek's own docs describe automatic disk-based context caching that is
explicitly "best-effort" and does NOT guarantee a 100% hit rate -- a hedge
OpenAI's docs don't carry. This tests whether that hedge cashes out as real
non-determinism (Gemini-like) or whether it's stable in practice (OpenAI-like)
despite the disclaimer, and independently measures DeepSeek's actual cache
unit size (docs say a 64-token storage unit but describe cache-unit formation
at "fixed token intervals" -- worth checking empirically like OpenAI's
1024-token result contradicted the commonly-cited 128 folklore figure).

Uses a substitution word ("Yields") never sent before in this project, to
avoid the self-hit cache contamination discovered in the OpenAI sweep.

Positions: 1, 8, 16, 24, 32, 40, 45 (spread across the 45 tool blocks) plus a
true control (no edit) baseline. 8 conditions x 5 reps x 2 calls = 80 calls,
~7.7k input tokens each. At DeepSeek's $0.14/1M miss / $0.0028/1M hit pricing
this is on the order of a few cents.
"""

from __future__ import annotations

import json
import sys
import time

from client import CacheProbeClient, load_dotenv
from perturbations import _blocks, _build, _header

DEEPSEEK_BASE = "https://api.deepseek.com"
SUFFIX = "In one word, what is the primary key field called in these tools?"
GAP = 3.0
REPS = 5
POSITIONS = [1, 8, 16, 24, 32, 40, 45]


def variant_for_tool(i, blocks, header):
    b = list(blocks)
    b[i] = b[i].replace("Retrieves a structured record", "Yields a structured record", 1)
    return _build(header, b)


def run_condition(client, base, text, label, results):
    samples = []
    for r in range(REPS):
        try:
            client.call(base, SUFFIX, cache_control=False)
            time.sleep(GAP)
            usage, _, _ = client.call(text, SUFFIX, cache_control=False)
        except RuntimeError as e:
            print(f"    rep {r}: ERROR {e}")
            continue
        cached = usage.get("prompt_cache_hit_tokens", 0)
        total = usage.get("prompt_tokens", 0)
        samples.append(dict(cached=cached, total=total))
        print(f"    rep {r}: cached={cached:6d}/{total:6d}")
        time.sleep(1)
    results[label] = samples


def main():
    load_dotenv()
    header = _header()
    blocks = _blocks(45)
    base = _build(header, blocks)

    client = CacheProbeClient(model="deepseek-chat", base_url=DEEPSEEK_BASE,
                                api_key_env="DEEPSEEK_API_KEY")

    results = {}
    print("=== control (no edit) ===")
    run_condition(client, base, base, "control", results)

    for tool_num in POSITIONS:
        print(f"=== tool#{tool_num} edit ===")
        variant = variant_for_tool(tool_num - 1, blocks, header)
        run_condition(client, base, variant, f"tool{tool_num}", results)

    with open("deepseek_chunk_sweep_results.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print("\nWrote deepseek_chunk_sweep_results.json")


if __name__ == "__main__":
    sys.exit(main())
