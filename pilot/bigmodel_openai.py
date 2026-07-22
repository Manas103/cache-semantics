"""Larger-model spot-check: does OpenAI's 1024-token chunk grain (established
on gpt-5-mini, doc_full_sweep_openai.py / openai_direct_validation.py) hold
on the full gpt-5 model? Direct api.openai.com, one mid-range landmark
position (section#24, doc-shape prefix -- OpenRouter/gpt-5-mini reference
value there was 2816).

Cost: 2 calls, ~5.6k input tokens.
"""

from __future__ import annotations

import json
import sys
import time

from client import CacheProbeClient, load_dotenv
from perturbations_doc import _blocks, _build, _header

OPENAI_BASE = "https://api.openai.com/v1"
SUFFIX = "In one word, what office should employees consult if a requirement is unclear?"
MODEL = "gpt-5"
SECTION = 24
REFERENCE_MINI = 2816


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

    client = CacheProbeClient(model=MODEL, base_url=OPENAI_BASE, api_key_env="OPENAI_API_KEY",
                                max_tokens=500, max_tokens_param="max_completion_tokens",
                                send_temperature=False)

    client.call(base, SUFFIX, max_tokens=500)
    time.sleep(2.5)
    usage, _, _ = client.call(variant, SUFFIX, max_tokens=500)
    details = usage.get("prompt_tokens_details") or {}
    cached = details.get("cached_tokens", 0)
    total = usage.get("prompt_tokens", 0)
    print(f"{MODEL} sec#{SECTION} edit: cached={cached:6d}/{total:6d}  (gpt-5-mini ref={REFERENCE_MINI})")

    results = dict(model=MODEL, section=SECTION, cached=cached, total=total, mini_reference=REFERENCE_MINI)
    with open("bigmodel_openai_results.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print("Wrote bigmodel_openai_results.json")


if __name__ == "__main__":
    sys.exit(main())
