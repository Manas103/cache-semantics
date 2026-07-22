"""Validation check: does direct api.openai.com reproduce the same cache
credit numbers we measured through OpenRouter (doc_sweep_openai.py /
doc_full_sweep_openai.py)? The paper's OpenAI numbers so far all come via
OpenRouter's OpenAI-compatible proxy, not OpenAI's own API directly --
a real, previously-undisclosed threat to validity (does OpenRouter add
its own routing/session logic that could confound the numbers?).

Single-shot sweep at the same 7 landmark positions used throughout this
project, on the doc-shape prefix (chosen because we already have full
45-position OpenRouter ground truth for it in doc_full_sweep_openai_results.json
to compare against). No session_id -- that's an OpenRouter-specific pinning
concept; direct OpenAI's automatic caching doesn't need or accept it.

Direct API quirks discovered getting this working (gpt-5-mini specifically):
  - max_tokens is rejected -- must use max_completion_tokens.
  - temperature=0.0 is rejected -- only the default (1) is supported.
Both are silently normalized by OpenRouter's compat shim, which is itself
worth a methods-section footnote regardless of whether the cache numbers
match.

Cost: 7 positions x 2 calls, ~5.6k input tokens each.
"""

from __future__ import annotations

import json
import sys
import time

from client import CacheProbeClient, load_dotenv
from perturbations_doc import _blocks, _build, _header

OPENAI_BASE = "https://api.openai.com/v1"
SUFFIX = "In one word, what office should employees consult if a requirement is unclear?"
POSITIONS = [1, 8, 16, 24, 32, 40, 45]

REFERENCE = {1: 0, 8: 0, 16: 1792, 24: 2816, 32: 2816, 40: 3840, 45: 4864}


def variant_for_section(i, blocks, header):
    b = list(blocks)
    b[i] = b[i].replace("This section establishes the requirements", "This section specifies the requirements", 1)
    return _build(header, b)


def main():
    load_dotenv()
    header = _header()
    blocks = _blocks(45)
    base = _build(header, blocks)

    client = CacheProbeClient(model="gpt-5-mini", base_url=OPENAI_BASE,
                                api_key_env="OPENAI_API_KEY", max_tokens=500,
                                max_tokens_param="max_completion_tokens",
                                send_temperature=False)

    results = []
    for sec_num in POSITIONS:
        variant = variant_for_section(sec_num - 1, blocks, header)
        try:
            client.call(base, SUFFIX, max_tokens=500)
            time.sleep(2.5)
            meas_usage, _, _ = client.call(variant, SUFFIX, max_tokens=500)
        except RuntimeError as e:
            print(f"  sec#{sec_num:2d} ERROR: {e}")
            continue
        details = meas_usage.get("prompt_tokens_details") or {}
        cached = details.get("cached_tokens", 0)
        total = meas_usage.get("prompt_tokens", 0)
        ref = REFERENCE[sec_num]
        match = "MATCH" if cached == ref else "MISMATCH"
        print(f"  sec#{sec_num:2d} edit: cached={cached:6d}/{total:6d}  (OpenRouter ref={ref:6d})  {match}")
        results.append(dict(section=sec_num, cached=cached, total=total, openrouter_ref=ref, match=(cached == ref)))
        time.sleep(1)

    with open("openai_direct_validation_results.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    n_match = sum(1 for r in results if r["match"])
    print(f"\n{n_match}/{len(results)} positions matched OpenRouter reference values.")
    print("Wrote openai_direct_validation_results.json")


if __name__ == "__main__":
    sys.exit(main())
