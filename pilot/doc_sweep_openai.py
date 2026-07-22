"""Generalization check: does OpenAI's deterministic 1024-token chunk
granularity (measured on the tool-schema prefix in sweep_chunk_boundary.py)
also hold on a structurally different prefix shape -- prose policy
sections instead of tool/parameter schemas?

Single-shot sweep at the same 7 landmark positions used throughout this
project (1, 8, 16, 24, 32, 40, 45), via OpenRouter with session pinning
(as in sweep_chunk_boundary.py).

Cost: 7 positions x 2 calls, ~7.8k input tokens each.
"""

from __future__ import annotations

import json
import sys
import time

from client import CacheProbeClient, load_dotenv
from perturbations_doc import _blocks, _build, _header

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
SUFFIX = "In one word, what office should employees consult if a requirement is unclear?"
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

    client = CacheProbeClient(model="openai/gpt-5-mini", base_url=OPENROUTER_BASE,
                                api_key_env="OPENROUTER_API_KEY", max_tokens=500)

    results = []
    for sec_num in POSITIONS:
        session_id = f"doc-sweep-sec{sec_num}"
        variant = variant_for_section(sec_num - 1, blocks, header)
        try:
            client.call(base, SUFFIX, session_id=session_id, max_tokens=500)
            time.sleep(2.5)
            meas_usage, _, _ = client.call(variant, SUFFIX, session_id=session_id, max_tokens=500)
        except RuntimeError as e:
            print(f"  sec#{sec_num:2d} ERROR: {e}")
            continue
        details = meas_usage.get("prompt_tokens_details") or {}
        cached = details.get("cached_tokens", 0)
        total = meas_usage.get("prompt_tokens", 0)
        print(f"  sec#{sec_num:2d} edit: cached={cached:6d}/{total:6d}")
        results.append(dict(section=sec_num, cached=cached, total=total))
        time.sleep(1)

    with open("doc_sweep_openai_results.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print("Wrote doc_sweep_openai_results.json")


if __name__ == "__main__":
    sys.exit(main())
