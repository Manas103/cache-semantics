"""Generalization check: does Gemini's non-deterministic realized cache
credit (measured on the tool-schema prefix in gemini_chunk_sweep.py /
gemini_isolation_check.py) also show up on the doc-shape prefix? Repeated-
trial sweep (3 reps -- lighter than the original 5/12-rep checks, since
this is a generalization spot-check, not a re-establishment of the
mechanism) at the same 7 landmark positions plus control.

Cost: 8 conditions x 3 reps x 2 calls, ~7.8k input tokens each.
"""

from __future__ import annotations

import json
import sys
import time

from client import CacheProbeClient, load_dotenv
from perturbations_doc import _blocks, _build, _header

GEMINI_DIRECT_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"
SUFFIX = "In one word, what office should employees consult if a requirement is unclear?"
GAP = 3.0
REPS = 3
POSITIONS = [1, 8, 16, 24, 32, 40, 45]


def variant_for_section(i, blocks, header):
    b = list(blocks)
    b[i] = b[i].replace("This section establishes the requirements", "This section specifies the requirements", 1)
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

    for sec_num in POSITIONS:
        print(f"=== section#{sec_num} edit ===")
        variant = variant_for_section(sec_num - 1, blocks, header)
        run_condition(client, base, variant, f"section{sec_num}", results)

    with open("doc_sweep_gemini_results.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print("\nWrote doc_sweep_gemini_results.json")


if __name__ == "__main__":
    sys.exit(main())
