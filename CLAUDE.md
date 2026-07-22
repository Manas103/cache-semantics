# CLAUDE.md — cache-semantics

Operational notes for Claude Code. **Facts only** — strategy, status, and "why" live in the
linked docs (and in the user's Claude Code memory, project entry `cache-semantics-preprint`), so
don't duplicate narrative here; keep this file in sync with reality as the repo changes.

## What this is
A black-box measurement study of **prompt-cache invalidation granularity** across four LLM API
providers (Anthropic, OpenAI, DeepSeek, Gemini): given a primed cache and a single controlled
edit to a shared prefix, how many tokens of that prefix still get credited as cached, read
directly from each provider's own usage telemetry (not a timing side-channel, unlike the closest
prior art). It ships as a solo arXiv preprint, Paper 4 of Manas's portfolio (after `tzarith`/
`dst-bench`). **Status: manuscript is drafted and compiles clean; not yet submitted to arXiv**
(blocked on the same endorsement requirement as `tzarith` — see the `arxiv-endorsement-gate`
memory entry). No further data collection is planned; remaining work is submission logistics.

## Security (hard rule)
- **Never print the contents of `.env`** (it lives at `../.env` relative to this repo, i.e. the
  Research-Paper root, shared with the `tzarith`/`dst-bench` project). It holds
  `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `DEEPSEEK_API_KEY`, and
  `GEMINI_API_KEY`. Load in-process only. If you must verify a key, print its length/prefix, never
  the value.
- `pilot/client.py`'s `load_dotenv()` auto-loads `.env` by walking up to 4 parent directories.
  Every probe script imports and calls it; use that path rather than putting keys on the command
  line or in a script.

## Layout
- `pilot/` — all measurement code and raw results. Stdlib-only Python (`urllib` for HTTP, no
  third-party dependencies) except `make_figures.py`, which needs `matplotlib` (see
  `requirements.txt`).
  - `client.py` — `CacheProbeClient` (OpenAI-compatible surface: OpenAI via OpenRouter or direct,
    DeepSeek, Gemini) and `AnthropicNativeClient` (native `/v1/messages`, required because
    Anthropic's OpenAI-compat shim silently drops cache telemetry fields).
  - `prefix.py` / `perturbations.py` — the primary test artifact: 45 templated tool schemas
    (~6,900–7,700 tokens depending on tokenizer) plus the 7 perturbation variants (control,
    header edit, first/mid/late block edit, trailing whitespace, adjacent-block reorder).
  - `prefix_doc.py` / `perturbations_doc.py` — the second, structurally different test artifact:
    a 45-section prose policy-handbook document, used for the generalization check.
  - One script per provider/check (`*_sweep.py`, `*_isolation_check.py`,
    `*_insertion_check.py`, `bigmodel_*.py`, `doc_*.py`, `openai_direct_validation.py`), each
    writing its raw output to an adjacent `*_results.json`. These JSON files are the source of
    truth for every number in the paper — do not hand-edit them.
  - `make_figures.py` — rebuilds the two step-plot figures in `paper/figures/` from already-collected
    `*_results.json` data. No API calls.
  - `paper_outline.md` — the pre-write-up outline the manuscript was drafted from; still useful as
    a compressed index of every finding and which script/JSON backs it.
- `paper/` — the manuscript. `main.tex` (LaTeX source), `main.pdf` (compiled, tracked in git),
  `figures/` (the two step-plot PDFs), `arxiv_metadata.txt` (submission form fields, not yet used).

## Commands
- Build the paper: from `paper/`, run `pdflatex -interaction=nonstopmode main.tex` **twice**
  (manual `thebibliography`, no BibTeX). A clean build is 14 pages, no undefined refs, no real
  errors. Clean up `*.aux`/`*.log`/`*.out` after a successful build (gitignored, but keep the
  working tree tidy).
- Regenerate figures: from `pilot/`, run `python make_figures.py` (needs `matplotlib`; reads
  existing `*_results.json`, writes `../paper/figures/*.pdf`).
- Run any probe script: from `pilot/`, e.g. `python deepseek_full_sweep.py`. Each is a one-shot
  script, not a CLI with flags; read the top of the file before rerunning one, since several
  (DeepSeek especially) are single-shot-only by design (see the contamination note below).

## Results guardrail — provider-specific self-contamination gotchas
Two of the probe scripts hit real methodological traps during data collection; both are now
documented in the paper's Method section (`sec:method`), but matter if you ever rerun or extend
these scripts:
- **DeepSeek's cache is disk-persisted and content-addressed globally** (any exact prefix text
  sent once stays cache-hittable indefinitely, not scoped to a session or short TTL). A
  repeated-trial design that reuses identical perturbation text across runs will silently
  self-contaminate (false near-100%-credit readings). DeepSeek sweep scripts use single-shot,
  never-reused edit text per position for this reason — don't "fix" that into a repeated-trial
  design without rereading `sec:method` in `main.tex` first.
- **OpenAI** (via OpenRouter) showed transient session-routing noise at a handful of sweep
  positions on the first pass; `recheck_sweep_outliers.json` holds the corrected, independently
  rechecked values for those positions and is applied on top of `chunk_sweep_results.json` (see
  `make_figures.py` for the exact override logic).
- **Gemini's non-determinism is a real finding, not noise to average away.** Its automatic cache
  is not a stable function of request content; isolation checks (12+ reps, single fixed
  condition) are how this was established. Don't collapse Gemini's per-position readings to a
  single number in any future analysis — the variance itself is the result.

## Writing conventions (paper)
Same conventions as `tzarith`/`dst-bench`:
- **No em-dashes.** Use commas, parentheses, or colons.
- Avoid AI-tell vocabulary and marketing voice (no "delve / leverage / underscore / crucial", no
  repeated "sharp / stark"). Formal but plain.
- Keep Limitations honest; don't overclaim. Load-bearing hedges already in the paper: two
  synthetic prefix shapes only, one small model per provider (spot-checked, not swept, on a
  larger model), point-in-time characterization (July 2026), self-reported telemetry, OpenAI
  measured mostly through OpenRouter (cross-validated on 7 of 45 positions, not the full sweep).

## Cost discipline
The whole pilot (~350+ API calls across four providers) ran for about $7 in direct top-ups
(Anthropic Console + DeepSeek prepaid; OpenAI stayed on OpenRouter, no direct key purchased until
the cross-validation check). Per-call cost has been fractions of a cent throughout. If extending
this work, smoke-test any new script against one position before a full sweep.

## Pointers (read these; don't copy their content here)
- Full narrative (why this topic, every finding as it was made, budget, all methodological
  traps and fixes in chronological order): the `cache-semantics-preprint` entry in the user's
  Claude Code memory (`~/.claude/.../memory/cache-semantics-preprint.md`), not part of this repo.
- arXiv endorsement blocker (shared with `tzarith`): `arxiv-endorsement-gate` memory entry.
