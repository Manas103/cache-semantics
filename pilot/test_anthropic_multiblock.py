"""Is Anthropic's atomic all-or-nothing cache behavior inherent to
cache_control, or just an artifact of wrapping the whole prefix in one
content block?

Splits the system prompt the way Anthropic's own docs recommend: a large
static block (header + tools 1-44) marked cache_control, followed by a
small always-varying tail block (tool 45) with no cache_control at all.
Primes with both blocks unchanged, then measures with only the tail block
edited. If the atomic-miss result was a single-block artifact, block 1's
~7.6k tokens should now show up as cache_read_input_tokens even though
block 2 changed.

Cost: 2 calls (prime + measure), ~7.7k input tokens.
"""

from __future__ import annotations

import json
import sys
import time

from client import AnthropicNativeClient, load_dotenv
from perturbations import _blocks, _header

SUFFIX = "In one word, what is the primary key field called in these tools?"


def main():
    load_dotenv()
    header = _header()
    blocks = _blocks(45)
    block1_text = header + "\n\n".join(blocks[:44])
    block2_orig = blocks[44]
    block2_edited = block2_orig.replace("Retrieves a structured record", "Fetches a structured record", 1)

    client = AnthropicNativeClient(model="claude-haiku-4-5-20251001", max_tokens=20)

    print("=== prime (block1 + block2, both original, block1 cache_control=True) ===")
    prime_blocks = [(block1_text, True), (block2_orig, False)]
    prime_usage, _, _ = client.call_multiblock(prime_blocks, SUFFIX)
    print(f"  usage: {json.dumps(prime_usage)}")
    time.sleep(2.5)

    print("=== measure: control repeat (block2 unchanged) ===")
    ctrl_usage, _, _ = client.call_multiblock(prime_blocks, SUFFIX)
    print(f"  usage: {json.dumps(ctrl_usage)}")
    time.sleep(2.5)

    print("=== measure: block2 edited (block1 byte-identical) ===")
    edited_blocks = [(block1_text, True), (block2_edited, False)]
    edit_usage, _, _ = client.call_multiblock(edited_blocks, SUFFIX)
    print(f"  usage: {json.dumps(edit_usage)}")

    results = dict(prime=prime_usage, control_repeat=ctrl_usage, block2_edited=edit_usage)
    with open("anthropic_multiblock_results.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print("\nWrote anthropic_multiblock_results.json")


if __name__ == "__main__":
    sys.exit(main())
