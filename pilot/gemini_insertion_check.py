"""Length-changing-edit check for Gemini -- see openai_insertion_check.py for
full rationale. Inserts a new sentence into section#16 of the doc-shape
prefix. 3 reps (matching the other lightweight spot-checks in this project)
since a single Gemini call is uninterpretable given its known variance --
here we're not trying to re-establish the non-determinism itself, just
checking whether insertion changes its character (e.g. a consistent hard
miss downstream vs. the same kind of scattered partial credit seen for
substitutions).

Cost: 3 reps x 2 calls, ~5.6k input tokens each.
"""

from __future__ import annotations

import json
import sys
import time

from client import CacheProbeClient, load_dotenv
from perturbations_doc import _blocks, _build, _header, insert_into_section

GEMINI_DIRECT_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"
SUFFIX = "In one word, what office should employees consult if a requirement is unclear?"
MODEL = "gemini-2.5-flash"
GAP = 3.0
REPS = 3
SECTION = 16
SUBSTITUTION_REFERENCE_REPS = [1019, 1019, 0]
ADDITION = "This section reflects updates approved during the most recent quarterly compliance review."


def main():
    load_dotenv()
    header = _header()
    blocks = _blocks(45)
    base = _build(header, blocks)
    variant = _build(header, insert_into_section(blocks, SECTION - 1, ADDITION))

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

    out = dict(section=SECTION, reps=results, substitution_reference_reps=SUBSTITUTION_REFERENCE_REPS)
    with open("gemini_insertion_check_results.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    vals = sorted(set(x["cached"] for x in results))
    print(f"\ndistinct cached values observed: {vals}")
    print("Wrote gemini_insertion_check_results.json")


if __name__ == "__main__":
    sys.exit(main())
