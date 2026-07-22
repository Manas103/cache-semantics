"""Generalization check: DeepSeek sweep on the doc-shape prefix. Single-shot
only (no repeats) -- DeepSeek's cache is disk-persisted and content-
addressed globally (see deepseek_full_sweep.py), so repeating an identical
(prime, measure) pair self-hits rather than re-measuring genuine overlap.
Since this doc text has never been sent to DeepSeek before, any
substitution word is fresh; if this script is ever rerun, change the
substitution word first to avoid self-hit contamination.

Cost: 7 positions x 2 calls, ~7.8k input tokens each.
"""

from __future__ import annotations

import json
import sys
import time

from client import CacheProbeClient, load_dotenv
from perturbations_doc import _blocks, _build, _header

DEEPSEEK_BASE = "https://api.deepseek.com"
SUFFIX = "In one word, what office should employees consult if a requirement is unclear?"
GAP = 2.5
POSITIONS = [1, 8, 16, 24, 32, 40, 45]


def variant_for_section(i, blocks, header):
    b = list(blocks)
    b[i] = b[i].replace("This section establishes the requirements", "This section specifies the requirements", 1)
    return _build(header, b)


def main():
    load_dotenv()
    header = _header()
    blocks = _blocks(45)
    base = _build(header, blocks)

    client = CacheProbeClient(model="deepseek-chat", base_url=DEEPSEEK_BASE,
                                api_key_env="DEEPSEEK_API_KEY")

    results = []
    for sec_num in POSITIONS:
        variant = variant_for_section(sec_num - 1, blocks, header)
        try:
            client.call(base, SUFFIX, cache_control=False)
            time.sleep(GAP)
            usage, _, _ = client.call(variant, SUFFIX, cache_control=False)
        except RuntimeError as e:
            print(f"sec#{sec_num:2d}: ERROR {e}")
            continue
        cached = usage.get("prompt_cache_hit_tokens", 0)
        total = usage.get("prompt_tokens", 0)
        print(f"sec#{sec_num:2d}: cached={cached:6d}/{total:6d}")
        results.append(dict(section=sec_num, cached=cached, total=total))
        time.sleep(1)

    with open("doc_sweep_deepseek_results.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print("\nWrote doc_sweep_deepseek_results.json")


if __name__ == "__main__":
    sys.exit(main())
