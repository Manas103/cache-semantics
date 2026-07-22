"""Length-changing-edit check for OpenAI: every perturbation tested so far
has been a same-length-ish word substitution. Real prompt edits (adding a
tool, extending a parameter description) are often insertions that shift the
absolute token offset of everything downstream -- untested so far, and
directly relevant given the content-anchored-boundary nuance found in
doc_full_sweep_openai.py (§4.6).

Inserts a new sentence into section#16 of the doc-shape prefix (doc-shape
substitution reference at this position was 1792 credited tokens). Two
possible outcomes: credit caps at or below the substitution reference
(everything downstream of the insertion is a totally new byte sequence --
pure prefix/LCP-continuity caching, the expected result for radix-tree-style
KV-cache reuse) or credit exceeds it (evidence some content downstream of the
insertion still gets matched -- real content-defined/rolling-hash chunking).

Direct api.openai.com, single-shot.

Cost: 2 calls, ~5.6k input tokens.
"""

from __future__ import annotations

import json
import sys
import time

from client import CacheProbeClient, load_dotenv
from perturbations_doc import _blocks, _build, _header, insert_into_section

OPENAI_BASE = "https://api.openai.com/v1"
SUFFIX = "In one word, what office should employees consult if a requirement is unclear?"
MODEL = "gpt-5-mini"
SECTION = 16
SUBSTITUTION_REFERENCE = 1792
ADDITION = "This section was most recently revised during the annual policy review cycle described above."


def main():
    load_dotenv()
    header = _header()
    blocks = _blocks(45)
    base = _build(header, blocks)
    variant = _build(header, insert_into_section(blocks, SECTION - 1, ADDITION))

    client = CacheProbeClient(model=MODEL, base_url=OPENAI_BASE, api_key_env="OPENAI_API_KEY",
                                max_tokens=500, max_tokens_param="max_completion_tokens",
                                send_temperature=False)

    client.call(base, SUFFIX, max_tokens=500)
    time.sleep(2.5)
    usage, _, _ = client.call(variant, SUFFIX, max_tokens=500)
    details = usage.get("prompt_tokens_details") or {}
    cached = details.get("cached_tokens", 0)
    total = usage.get("prompt_tokens", 0)
    base_total = len(base)  # for reference only
    print(f"insertion at sec#{SECTION}: cached={cached:6d}/{total:6d}  (substitution ref={SUBSTITUTION_REFERENCE})")
    verdict = "AT/BELOW substitution ref (consistent with pure prefix caching)" if cached <= SUBSTITUTION_REFERENCE \
        else "ABOVE substitution ref (evidence of downstream resync!)"
    print(verdict)

    results = dict(section=SECTION, cached=cached, total=total,
                    substitution_reference=SUBSTITUTION_REFERENCE, verdict=verdict)
    with open("openai_insertion_check_results.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print("Wrote openai_insertion_check_results.json")


if __name__ == "__main__":
    sys.exit(main())
