"""Follow-up to bigmodel_deepseek.py: the single-position spot-check at
section#24 showed deepseek-reasoner crediting 2816 tokens vs. deepseek-chat's
1792 at the identical position -- both exact multiples of 128 (still on-grid)
but offset from each other. Tests three more positions (8, 16, 40) to check
whether that offset is a systematic phase shift or a one-off. (section#24
itself is already covered by bigmodel_deepseek.py with a different
substitution word, "clarifies" -- not repeated here.)

Fresh substitution word ("outlines") never used before at these positions.
NOTE: if this script is ever rerun, change the substitution word first --
rerunning with "outlines" at these exact positions would self-hit the
results already recorded below rather than measuring anything new (see
deepseek_chunk_sweep.py for the original diagnosis of this failure mode).

Cost: 3 positions x 2 calls, ~5.6k input tokens each.
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
POSITIONS = [8, 16, 40]
CHAT_REFERENCE = {8: 0, 16: 896, 40: 3840}


def variant_for_section(i, blocks, header):
    b = list(blocks)
    b[i] = b[i].replace("This section establishes the requirements", "This section outlines the requirements", 1)
    return _build(header, b)


def main():
    load_dotenv()
    header = _header()
    blocks = _blocks(45)
    base = _build(header, blocks)

    client = CacheProbeClient(model=MODEL, base_url=DEEPSEEK_BASE, api_key_env="DEEPSEEK_API_KEY")

    results = []
    for sec_num in POSITIONS:
        variant = variant_for_section(sec_num - 1, blocks, header)
        try:
            client.call(base, SUFFIX, cache_control=False)
            time.sleep(2.5)
            usage, _, _ = client.call(variant, SUFFIX, cache_control=False)
        except RuntimeError as e:
            print(f"sec#{sec_num:2d}: ERROR {e}")
            continue
        cached = usage.get("prompt_cache_hit_tokens", 0)
        total = usage.get("prompt_tokens", 0)
        ref = CHAT_REFERENCE[sec_num]
        print(f"sec#{sec_num:2d}: {MODEL} cached={cached:6d}/{total:6d}  (deepseek-chat ref={ref:6d}, delta={cached - ref:+d})")
        results.append(dict(section=sec_num, model=MODEL, cached=cached, total=total,
                             chat_reference=ref, delta=cached - ref))
        time.sleep(1)

    with open("bigmodel_deepseek_multipos_results.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print("\nWrote bigmodel_deepseek_multipos_results.json")


if __name__ == "__main__":
    sys.exit(main())
