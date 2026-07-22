"""Length-changing-edit check for DeepSeek -- see openai_insertion_check.py
for full rationale. Inserts a new sentence into section#16 of the doc-shape
prefix (doc-shape substitution reference at this position was 896 credited
tokens on deepseek-chat). Single-shot only -- DeepSeek's cache is disk-
persisted and content-addressed globally, so this is a fresh, never-before-
sent addition to avoid self-hit contamination.

Cost: 2 calls, ~5.6k input tokens.
"""

from __future__ import annotations

import json
import sys
import time

from client import CacheProbeClient, load_dotenv
from perturbations_doc import _blocks, _build, _header, insert_into_section

DEEPSEEK_BASE = "https://api.deepseek.com"
SUFFIX = "In one word, what office should employees consult if a requirement is unclear?"
MODEL = "deepseek-chat"
SECTION = 16
SUBSTITUTION_REFERENCE = 896
ADDITION = "This paragraph was expanded with additional context for the current fiscal year."


def main():
    load_dotenv()
    header = _header()
    blocks = _blocks(45)
    base = _build(header, blocks)
    variant = _build(header, insert_into_section(blocks, SECTION - 1, ADDITION))

    client = CacheProbeClient(model=MODEL, base_url=DEEPSEEK_BASE, api_key_env="DEEPSEEK_API_KEY")

    client.call(base, SUFFIX, cache_control=False)
    time.sleep(2.5)
    usage, _, _ = client.call(variant, SUFFIX, cache_control=False)
    cached = usage.get("prompt_cache_hit_tokens", 0)
    total = usage.get("prompt_tokens", 0)
    print(f"insertion at sec#{SECTION}: cached={cached:6d}/{total:6d}  (substitution ref={SUBSTITUTION_REFERENCE})")
    verdict = "AT/BELOW substitution ref (consistent with pure prefix caching)" if cached <= SUBSTITUTION_REFERENCE \
        else "ABOVE substitution ref (evidence of downstream resync!)"
    print(verdict)

    results = dict(section=SECTION, cached=cached, total=total,
                    substitution_reference=SUBSTITUTION_REFERENCE, verdict=verdict)
    with open("deepseek_insertion_check_results.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print("Wrote deepseek_insertion_check_results.json")


if __name__ == "__main__":
    sys.exit(main())
