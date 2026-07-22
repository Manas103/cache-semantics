"""Follow-up to doc_sweep_openai.py: the 7-landmark-position sweep on the
doc-shape prefix produced cached=1792 at section#16 -- NOT a multiple of
1024, breaking the clean 1024-token-chunk pattern established on the
tool-schema prefix (sweep_chunk_boundary.py). Doc sections are non-uniform
length (topic-name strings vary a lot, e.g. "Code Review" vs "Multi-Factor
Authentication"), so the 7 sparse landmark positions may land at different
*effective token offsets* than they did in the tool-list shape, where every
block was near-identical length.

Full single-shot 45-position sweep (mirrors sweep_chunk_boundary.py exactly)
to resolve whether the underlying grain is still 1024 tokens (and the 1792
reading was a non-uniform-spacing artifact) or genuinely different on this
prefix shape.

Cost: 45 positions x 2 calls, ~5.6k input tokens each.
"""

from __future__ import annotations

import json
import sys
import time

from client import CacheProbeClient, load_dotenv
from perturbations_doc import _blocks, _build, _header

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
SUFFIX = "In one word, what office should employees consult if a requirement is unclear?"


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

    only = int(sys.argv[1]) if len(sys.argv) > 1 else None
    indices = [only - 1] if only else range(45)

    results = []
    for i in indices:
        session_id = f"doc-full-sweep-sec{i+1}"
        variant = variant_for_section(i, blocks, header)
        try:
            client.call(base, SUFFIX, session_id=session_id, max_tokens=500)
            time.sleep(2.5)
            meas_usage, _, _ = client.call(variant, SUFFIX, session_id=session_id, max_tokens=500)
        except RuntimeError as e:
            print(f"  sec#{i+1:2d} ERROR: {e}")
            continue
        details = meas_usage.get("prompt_tokens_details") or {}
        cached = details.get("cached_tokens", 0)
        total = meas_usage.get("prompt_tokens", 0)
        print(f"  sec#{i+1:2d} edit: cached={cached:6d}/{total:6d}")
        results.append(dict(section=i + 1, cached=cached, total=total))
        time.sleep(1)

    with open("doc_full_sweep_openai_results.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print("Wrote doc_full_sweep_openai_results.json")


if __name__ == "__main__":
    sys.exit(main())
