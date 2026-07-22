"""Re-check tool#1, #23, #45 (suspected self-hit contamination from earlier
run_perturbation_battery.py using the identical substitution text) and
tool#36 (broke an otherwise-flat plateau, likely a routing miss) using a
substitution word never sent before in this project.
"""

from __future__ import annotations

import json
import time

from client import CacheProbeClient, load_dotenv
from perturbations import _blocks, _build, _header

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
SUFFIX = "In one word, what is the primary key field called in these tools?"


def variant_for_tool(i, blocks, header):
    b = list(blocks)
    b[i] = b[i].replace("Retrieves a structured record", "Obtains a structured record", 1)
    return _build(header, b)


def main():
    load_dotenv()
    header = _header()
    blocks = _blocks(45)
    base = _build(header, blocks)

    client = CacheProbeClient(model="openai/gpt-5-mini", base_url=OPENROUTER_BASE,
                                api_key_env="OPENROUTER_API_KEY", max_tokens=500)

    results = []
    for tool_num in [1, 23, 36, 45]:
        i = tool_num - 1
        session_id = f"recheck-tool{tool_num}"
        variant = variant_for_tool(i, blocks, header)
        client.call(base, SUFFIX, session_id=session_id, max_tokens=500)
        time.sleep(2.5)
        meas_usage, _, _ = client.call(variant, SUFFIX, session_id=session_id, max_tokens=500)
        details = meas_usage.get("prompt_tokens_details") or {}
        cached = details.get("cached_tokens", 0)
        total = meas_usage.get("prompt_tokens", 0)
        print(f"  tool#{tool_num:2d} recheck: cached={cached:6d}/{total:6d}")
        results.append(dict(tool_index=tool_num, cached=cached, total=total))
        time.sleep(1)

    with open("recheck_sweep_outliers.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print("Wrote recheck_sweep_outliers.json")


if __name__ == "__main__":
    import sys
    sys.exit(main())
