# cache-semantics: how much of your prompt survives an edit?

A black-box measurement of **prompt-cache invalidation granularity** across four LLM API
providers: Anthropic, OpenAI, DeepSeek, and Gemini.

Agentic tool-calling systems resend the same large tool-schema and system-prompt prefix on every
turn. Prompt caching is what makes that affordable, but provider documentation says caching
*exists* without saying precisely how it's *scoped*: does editing one line of a cached prefix
invalidate the whole thing, or does partial credit survive, and at what granularity? This project
answers that directly, by reading each provider's own usage telemetry
(`cache_read_input_tokens`, `prompt_tokens_details.cached_tokens`, DeepSeek's
`prompt_cache_hit_tokens`) after sending a primed prefix and a single controlled edit to it, rather
than inferring caching behavior from response-timing side channels the way prior work has.

## Findings, in brief

| Provider | Granularity | Determinism |
|---|---|---|
| Anthropic | Developer-controlled (`cache_control` block boundaries) | Deterministic by construction |
| OpenAI | ~1,024-token chunks, content-anchored | Deterministic |
| DeepSeek | 128-token chunks | Deterministic (bit-for-bit, even under an explicit "best-effort" docs hedge) |
| Gemini | N/A | **Not** a stable function of request content: identical repeated requests return different credited-token counts |

Full results, methodology, and four additional cross-cutting checks (a second structurally
different prefix, OpenAI direct-API cross-validation, larger-model spot-checks, and a
length-changing-edit/insertion check) are in `paper/main.pdf`.

## Layout

```
pilot/
  client.py              CacheProbeClient (OpenAI-compatible) + AnthropicNativeClient
  prefix.py / perturbations.py          tool-schema test prefix + edit variants
  prefix_doc.py / perturbations_doc.py  prose-document test prefix (generalization check)
  *_sweep.py, *_isolation_check.py,     one script per provider/check; each writes
  *_insertion_check.py, bigmodel_*.py,  its raw output to an adjacent *_results.json
  doc_*.py, openai_direct_validation.py
  make_figures.py        rebuilds paper/figures/*.pdf from existing *_results.json (no API calls)
  paper_outline.md        pre-write-up outline, indexed by finding
paper/
  main.tex / main.pdf     the manuscript
  figures/                 step-plot figures (OpenAI, DeepSeek chunk sweeps)
  arxiv_metadata.txt        submission form fields
```

## Reproducing a result

Every script is stdlib-only Python (`urllib` for HTTP), one script per measurement, writing a raw
`*_results.json` next to it. To rerun one:

```bash
# needs the relevant provider API key in the environment (see CONTRIBUTING.md)
python pilot/deepseek_full_sweep.py
```

To rebuild the two figures from already-collected data (no API calls, needs `matplotlib`):

```bash
pip install -r requirements.txt
python pilot/make_figures.py
```

To rebuild the paper:

```bash
cd paper && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex
```

## Status

Manuscript complete (14 pages, `paper/main.pdf`); not yet on arXiv. This is a solo research project; treat the code as measurement
scripts for a specific study, not a maintained library. See `CONTRIBUTING.md` to rerun or extend it.
