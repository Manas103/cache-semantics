"""Larger-model spot-check: does Gemini's non-determinism (established on
gemini-2.5-flash) also show up on gemini-2.5-pro, which plausibly runs on a
different serving pool with different replica/affinity behavior -- the most
likely of the four providers to show a genuinely different result, since our
working hypothesis for the flash non-determinism is unpinned load-balancing
across backend replicas. Single condition (section#24, doc-shape prefix --
flash reference reps there were 0/0/2038), 3 reps -- a single call would be
uninterpretable given Gemini's known variance.

Cost: 3 reps x 2 calls, ~5.6k input tokens each.
"""

from __future__ import annotations

import json
import sys
import time

from client import CacheProbeClient, load_dotenv
from perturbations_doc import _blocks, _build, _header

GEMINI_DIRECT_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"
SUFFIX = "In one word, what office should employees consult if a requirement is unclear?"
MODEL = "gemini-3.1-pro-preview"
GAP = 3.0
REPS = 3
SECTION = 24
FLASH_REFERENCE_REPS = [0, 0, 2038]


def variant_for_section(i, blocks, header):
    b = list(blocks)
    b[i] = b[i].replace("This section establishes the requirements", "This section specifies the requirements", 1)
    return _build(header, b)


def main():
    load_dotenv()
    header = _header()
    blocks = _blocks(45)
    base = _build(header, blocks)
    variant = variant_for_section(SECTION - 1, blocks, header)

    client = CacheProbeClient(model=MODEL, base_url=GEMINI_DIRECT_BASE, api_key_env="GEMINI_API_KEY")

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
        print(f"  rep {r}: cached={cached:6d}/{total:6d}")
        results.append(dict(rep=r, cached=cached, total=total))
        time.sleep(1)

    out = dict(model=MODEL, section=SECTION, reps=results, flash_reference_reps=FLASH_REFERENCE_REPS)
    with open("bigmodel_gemini_results.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    vals = sorted(set(x["cached"] for x in results))
    print(f"\ndistinct cached values observed ({MODEL}): {vals}")
    print("Wrote bigmodel_gemini_results.json")


if __name__ == "__main__":
    sys.exit(main())
