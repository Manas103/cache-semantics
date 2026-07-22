"""Generalization check: does Anthropic's developer-controlled granularity
(large cache_control-marked static block + small uncached tail = perfect
partial credit, established on the tool-schema prefix in
test_anthropic_multiblock.py) also hold on the doc-shape prefix?

Splits the doc into a static block (sections 1-44, cache_control=True) and
a small always-varying tail block (section 45, no cache_control), primes,
then measures with only the tail edited.

Cost: 3 calls (prime + control repeat + edited tail), ~7.8k input tokens.
"""

from __future__ import annotations

import json
import sys
import time

from client import AnthropicNativeClient, load_dotenv
from perturbations_doc import _blocks, _header

SUFFIX = "In one word, what office should employees consult if a requirement is unclear?"


def main():
    load_dotenv()
    header = _header()
    blocks = _blocks(45)
    block1_text = header + "\n\n".join(blocks[:44])
    block2_orig = blocks[44]
    block2_edited = block2_orig.replace("This section establishes the requirements", "This section specifies the requirements", 1)

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
    with open("doc_multiblock_anthropic_results.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print("\nWrote doc_multiblock_anthropic_results.json")


if __name__ == "__main__":
    sys.exit(main())
