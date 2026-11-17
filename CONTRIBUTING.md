# Rerunning and extending the measurements

This repo holds the measurement scripts, raw results and manuscript for one study. Issues and pull requests are welcome, especially reruns on newer models.

## Setup

- Every probe script is stdlib-only Python 3 (`urllib` for HTTP). `make_figures.py` also needs `matplotlib` (`pip install -r requirements.txt`).
- API keys are read from environment variables (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `DEEPSEEK_API_KEY`, `GEMINI_API_KEY`). `pilot/client.py` also loads a `.env` file from up to four parent directories. Never commit a `.env` file or put keys on the command line.

## Commands

- Run a probe: from `pilot/`, for example `python deepseek_full_sweep.py`. Each script is a one-shot measurement that writes a `*_results.json` next to itself. Read the top of a script before rerunning it; several are single-shot by design (see below).
- Rebuild the figures from the committed results (no API calls): from `pilot/`, `python make_figures.py`.
- Build the paper: from `paper/`, run `pdflatex -interaction=nonstopmode main.tex` twice (the bibliography is inline, no BibTeX). A clean build is 14 pages with no undefined references.
- Smoke-test any new script against one position before a full sweep. The whole study took about 350 API calls.

## Provider-specific traps (read before rerunning)

Both are described in the paper's Method section (`sec:method` in `paper/main.tex`).

- **DeepSeek's cache is disk-persisted and content-addressed globally.** Any exact prefix sent once stays cache-hittable indefinitely. A repeated-trial design that reuses the same edit text across runs silently contaminates itself and reads near-100% credit. The DeepSeek sweeps use single-shot, never-reused edit text per position for this reason.
- **OpenAI (through OpenRouter) showed transient routing noise** at a few sweep positions on the first pass. `pilot/recheck_sweep_outliers.json` holds the independently rechecked values, applied on top of `chunk_sweep_results.json` in `make_figures.py`.
- **Gemini's non-determinism is a finding, not noise.** Its automatic cache is not a stable function of request content (isolation checks with 12 or more repetitions of one fixed condition). Do not collapse Gemini's per-position readings to a single number; the variance is the result.

## Known limitations

Two synthetic prefix shapes, one small model per provider (spot-checked on a larger one), a point-in-time characterization (July 2026), self-reported usage telemetry, and OpenAI measured mostly through OpenRouter (cross-validated directly on 7 of 45 positions).
