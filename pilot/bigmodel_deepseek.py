"""Larger/different-pipeline spot-check: does DeepSeek's 128-token chunk
grain (established on deepseek-chat) hold on deepseek-reasoner, which has a
materially different serving pipeline (long chain-of-thought)? One
single-shot landmark position (section#24, doc-shape prefix -- deepseek-chat
reference value there was 1792).

Fresh substitution word ("clarifies") never used before, in case
deepseek-reasoner shares a cache namespace with deepseek-chat -- keeps this
single-shot measurement clean regardless.

Cost: 2 calls, ~5.6k input tokens.
"""

from __future__ import annotations

import json
import sys
import time

from client import CacheProbeClient, load_dotenv
from perturbations_doc import _blocks, _build, _header

DEEPSEEK_BASE = "https://api.deepseek.com"
SUFFIX = "In one word, what office should employees consult if a requirement is unclear?"
MODEL = "deepseek-reasoner"
SECTION = 24
REFERENCE_CHAT = 1792


def variant_for_section(i, blocks, header):
    b = list(blocks)
    b[i] = b[i].replace("This section establishes the requirements", "This section clarifies the requirements", 1)
    return _build(header, b)


def main():
    load_dotenv()
    header = _header()
    blocks = _blocks(45)
    base = _build(header, blocks)
    variant = variant_for_section(SECTION - 1, blocks, header)

    client = CacheProbeClient(model=MODEL, base_url=DEEPSEEK_BASE, api_key_env="DEEPSEEK_API_KEY")

    client.call(base, SUFFIX, cache_control=False)
    time.sleep(2.5)
    usage, _, _ = client.call(variant, SUFFIX, cache_control=False)
    cached = usage.get("prompt_cache_hit_tokens", 0)
    total = usage.get("prompt_tokens", 0)
    print(f"{MODEL} sec#{SECTION} edit: cached={cached:6d}/{total:6d}  (deepseek-chat ref={REFERENCE_CHAT})")

    results = dict(model=MODEL, section=SECTION, cached=cached, total=total, chat_reference=REFERENCE_CHAT)
    with open("bigmodel_deepseek_results.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print("Wrote bigmodel_deepseek_results.json")


if __name__ == "__main__":
    sys.exit(main())
