"""Repeated-trial chunk-boundary sweep for Gemini direct.

Unlike OpenAI (deterministic, single-shot sweep sufficed), Gemini's
implicit caching showed real backend-affinity noise in earlier probes
(consistent partial credit under tight back-to-back repetition, but flat
misses when interleaved with other calls). This repeats each (prime,
measure) cycle multiple times per position and reports the distribution,
rather than trusting a single sample.

Uses a substitution word ("Provides") never sent before in this project,
to avoid the self-hit cache contamination discovered in the OpenAI sweep.

Positions: 1, 8, 16, 24, 32, 40, 45 (spread across the 45 tool blocks) plus
a true control (no edit) baseline. 8 conditions x 5 reps x 2 calls = 80
calls, ~7.7k input tokens each.
"""

from __future__ import annotations

import json
import sys
import time

from client import CacheProbeClient, load_dotenv
from perturbations import _blocks, _build, _header

GEMINI_DIRECT_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"
SUFFIX = "In one word, what is the primary key field called in these tools?"
GAP = 3.0
REPS = 5
POSITIONS = [1, 8, 16, 24, 32, 40, 45]


def variant_for_tool(i, blocks, header):
    b = list(blocks)
    b[i] = b[i].replace("Retrieves a structured record", "Provides a structured record", 1)
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
        details = usage.get("prompt_tokens_details") or {}
        cached = details.get("cached_tokens", 0)
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

    client = CacheProbeClient(model="gemini-2.5-flash", base_url=GEMINI_DIRECT_BASE,
                                api_key_env="GEMINI_API_KEY")

    results = {}
    print("=== control (no edit) ===")
    run_condition(client, base, base, "control", results)

    for tool_num in POSITIONS:
        print(f"=== tool#{tool_num} edit ===")
        variant = variant_for_tool(tool_num - 1, blocks, header)
        run_condition(client, base, variant, f"tool{tool_num}", results)

    with open("gemini_chunk_sweep_results.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print("\nWrote gemini_chunk_sweep_results.json")


if __name__ == "__main__":
    sys.exit(main())
