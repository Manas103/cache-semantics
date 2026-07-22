"""Cache invalidation-granularity pilot.

For each (provider, variant): prime the cache with the base prefix, then
immediately send the variant and read how much of it still got credited as
cached. A naive whole-prefix-hash cache predicts ~0% credit for any edit
except one at the very end (trailing_whitespace, edit_tool45_late); partial
credit elsewhere is evidence of finer sub-block chunking.

Providers: Anthropic direct-native (explicit cache_control), OpenAI via
OpenRouter (automatic, max_tokens=500 to clear the reasoning-token bug),
Gemini direct (automatic). Cost: 3 providers x 7 variants x 2 calls
(prime+measure) = 42 calls, ~7.7k input tokens each. Should be well under $1.
"""

from __future__ import annotations

import json
import sys
import time

from client import AnthropicNativeClient, CacheProbeClient, load_dotenv
from perturbations import build_variants

GEMINI_DIRECT_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"
OPENROUTER_BASE = "https://openrouter.ai/api/v1"

PROVIDERS = [
    dict(label="anthropic-direct", kind="anthropic-native",
         model="claude-haiku-4-5-20251001", api_key_env="ANTHROPIC_API_KEY"),
    dict(label="openai-gpt5mini", kind="openai-compatible", base_url=OPENROUTER_BASE,
         model="openai/gpt-5-mini", api_key_env="OPENROUTER_API_KEY", max_tokens=500,
         sticky=True),
    dict(label="gemini-direct", kind="openai-compatible", base_url=GEMINI_DIRECT_BASE,
         model="gemini-2.5-flash", api_key_env="GEMINI_API_KEY"),
]

GAP = 2.5


def extract(kind, usage):
    if kind == "anthropic-native":
        cached = usage.get("cache_read_input_tokens", 0)
        total = (usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
                 + usage.get("cache_read_input_tokens", 0))
        return cached, total
    details = usage.get("prompt_tokens_details") or {}
    cached = details.get("cached_tokens", 0)
    total = usage.get("prompt_tokens", 0)
    return cached, total


def make_client(p):
    if p["kind"] == "anthropic-native":
        return AnthropicNativeClient(model=p["model"], api_key_env=p["api_key_env"])
    return CacheProbeClient(model=p["model"], base_url=p["base_url"], api_key_env=p["api_key_env"])


def do_call(p, client, text, session_id):
    cache_control = p["kind"] == "anthropic-native"
    max_tokens = p.get("max_tokens")
    if p["kind"] == "anthropic-native":
        return client.call(text, "In one word, what is the primary key field called in these tools?",
                            cache_control=cache_control, max_tokens=max_tokens)
    return client.call(text, "In one word, what is the primary key field called in these tools?",
                        cache_control=False, session_id=session_id, max_tokens=max_tokens)


def main():
    load_dotenv()
    base, variants = build_variants()
    only_provider = sys.argv[1] if len(sys.argv) > 1 else None
    providers = [p for p in PROVIDERS if not only_provider or only_provider in p["label"]]

    results = {}
    for p in providers:
        label = p["label"]
        print(f"\n##### provider: {label} #####")
        try:
            client = make_client(p)
        except RuntimeError as e:
            print(f"  SKIP: {e}")
            continue
        results[label] = {}
        for v in variants:
            name = v["name"]
            session_id = f"pert-{label}-{name}" if p.get("sticky") else None
            try:
                prime_usage, _, _ = do_call(p, client, base, session_id)
                time.sleep(GAP)
                meas_usage, _, raw = do_call(p, client, v["text"], session_id)
            except RuntimeError as e:
                print(f"  {name:28s} ERROR: {e}")
                continue
            cached, total = extract(p["kind"], meas_usage)
            pct = (cached / total * 100) if total else 0.0
            print(f"  {name:28s} expect_before_diff={v['frac_before_diff']*100:5.1f}%  "
                  f"observed_cached={cached:6d}/{total:6d} ({pct:5.1f}%)")
            results[label][name] = dict(cached=cached, total=total, pct=pct,
                                          frac_before_diff=v["frac_before_diff"])
            time.sleep(1)

    with open("perturbation_results.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print("\nWrote perturbation_results.json")


if __name__ == "__main__":
    sys.exit(main())
