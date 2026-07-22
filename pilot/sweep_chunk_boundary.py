"""Fine-grained sweep to pin down OpenAI's actual cache chunk size.

The coarse perturbation battery showed cached-token counts of 2816, 5888,
and ~6912 at three edit positions -- all exact multiples of 256 (11x, 23x,
27x), consistent with either a 128- or 256-token chunk granularity (256 is
itself a multiple of 128, so three points can't tell them apart). Editing
at each of the 45 tool-block positions (~155 tokens apart, finer than
either candidate) resolves it directly from the resulting step function.

Cost: 45 positions x 2 calls (prime + measure), ~7k input tokens each.
"""

from __future__ import annotations

import json
import sys
import time

from client import CacheProbeClient, load_dotenv
from perturbations import _blocks, _build, _header

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
SUFFIX = "In one word, what is the primary key field called in these tools?"


def variant_for_tool(i, blocks, header):
    b = list(blocks)
    b[i] = b[i].replace("Retrieves a structured record", "Fetches a structured record", 1)
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
        session_id = f"sweep-tool{i+1}"
        variant = variant_for_tool(i, blocks, header)
        try:
            client.call(base, SUFFIX, session_id=session_id, max_tokens=500)
            time.sleep(2.5)
            meas_usage, _, _ = client.call(variant, SUFFIX, session_id=session_id, max_tokens=500)
        except RuntimeError as e:
            print(f"  tool#{i+1:2d} ERROR: {e}")
            continue
        details = meas_usage.get("prompt_tokens_details") or {}
        cached = details.get("cached_tokens", 0)
        total = meas_usage.get("prompt_tokens", 0)
        print(f"  tool#{i+1:2d} edit: cached={cached:6d}/{total:6d}")
        results.append(dict(tool_index=i + 1, cached=cached, total=total))
        time.sleep(1)

    with open("chunk_sweep_results.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print("Wrote chunk_sweep_results.json")


if __name__ == "__main__":
    sys.exit(main())
