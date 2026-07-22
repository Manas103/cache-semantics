"""Larger-model spot-check: does Anthropic's developer-controlled partial
credit (static cache_control block + uncached tail, established on
claude-haiku-4-5 in test_anthropic_multiblock.py / doc_multiblock_anthropic.py)
hold on the largest available model in the family, claude-opus-4-8?
Reuses the doc-shape prefix. Single condition, same 3-call structure as the
earlier multiblock checks for direct comparability.

Cost: 3 calls, ~5.6k input tokens.
"""

from __future__ import annotations

import json
import sys
import time

from client import AnthropicNativeClient, load_dotenv
from perturbations_doc import _blocks, _header

SUFFIX = "In one word, what office should employees consult if a requirement is unclear?"
MODEL = "claude-opus-4-8"


def main():
    load_dotenv()
    header = _header()
    blocks = _blocks(45)
    block1_text = header + "\n\n".join(blocks[:44])
    block2_orig = blocks[44]
    block2_edited = block2_orig.replace("This section establishes the requirements", "This section specifies the requirements", 1)

    client = AnthropicNativeClient(model=MODEL, max_tokens=20, send_temperature=False)

    print(f"=== prime ({MODEL}, block1 cache_control=True) ===")
    prime_blocks = [(block1_text, True), (block2_orig, False)]
    prime_usage, _, _ = client.call_multiblock(prime_blocks, SUFFIX)
    print(f"  usage: {json.dumps(prime_usage)}")
    time.sleep(2.5)

    print("=== measure: block2 edited (block1 byte-identical) ===")
    edited_blocks = [(block1_text, True), (block2_edited, False)]
    edit_usage, _, _ = client.call_multiblock(edited_blocks, SUFFIX)
    print(f"  usage: {json.dumps(edit_usage)}")

    results = dict(model=MODEL, prime=prime_usage, block2_edited=edit_usage)
    with open("bigmodel_anthropic_results.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print("\nWrote bigmodel_anthropic_results.json")


if __name__ == "__main__":
    sys.exit(main())
