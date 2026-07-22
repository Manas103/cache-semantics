# Working title
"How Much of Your Prompt Survives an Edit? A Cross-Provider Measurement of
Prompt-Cache Invalidation Granularity"

(alt: "Prompt Cache Semantics in the Wild: Granularity, Determinism, and the
Gap Between Anthropic, OpenAI, DeepSeek, and Gemini")

## Abstract (draft bullets, not prose yet)
- Prompt caching is now load-bearing for cost/latency in agentic LLM apps,
  but its invalidation semantics are undocumented and provider-specific.
- We measure, via direct API usage-telemetry (not timing side-channels, cf.
  arXiv 2502.07776), exactly how much of a shared prefix survives a single
  controlled perturbation, across Anthropic, OpenAI, DeepSeek, and Gemini.
- Four qualitatively different regimes: Anthropic is developer-controlled
  (granularity = however you place `cache_control` blocks); OpenAI and
  DeepSeek are both deterministic fixed-chunk boundaries (1024 and 128
  tokens respectively); Gemini's realized cache credit is not a stable
  function of request content at all.
- Documented posture does not predict measured reliability: DeepSeek's own
  docs explicitly hedge ("best-effort... does not guarantee 100% hit
  rate") while OpenAI's don't — yet DeepSeek is the one that measured
  perfectly deterministic, and Gemini (no such hedge in its docs) is the
  one that's actually unreliable.
- Implication: "prompt caching" is not one mechanism — it's (at least) four
  different reliability contracts, and cost/latency estimates that assume
  one provider's behavior generalizes will be wrong on another.

## 1. Introduction
- Motivate: agentic tool-calling systems resend large static tool/system
  prefixes on every turn; caching is the difference between re-billing
  the whole prefix and billing pennies.
- Problem: providers document *that* caching exists, not precisely *how*
  invalidation is scoped (block? token count? position?), and whether it's
  deterministic.
- Prior art gap: arXiv 2502.07776 infers cache hits from response-latency
  side channels — noisy, and can't distinguish "partial hit" magnitude.
  We read the providers' own accounting fields directly.
- Contribution list (measurement paper, not a benchmark):
  1. First direct-telemetry (not timing-inferred) cross-provider comparison
     of cache invalidation granularity.
  2. Empirical, corrected value for OpenAI's chunk size (1024, not the
     commonly cited 128) via a systematic step-function sweep — and a
     second provider, DeepSeek, that actually does match the folklore
     128-token figure, confirming the two numbers were never the same
     claim about the same system.
  3. Demonstration that Anthropic's granularity is a *developer* choice
     (content-block structure), not a fixed provider constant — atomic
     with one block, perfect partial credit with the recommended
     static/variable split.
  4. Evidence that Gemini's automatic caching yields non-deterministic
     realized credit under an *identical, isolated, repeated* request —
     a reliability property, not just a granularity number — while
     DeepSeek, tested with the identical isolation protocol, returns
     bit-for-bit identical credit every time despite its docs hedging
     more explicitly than any other provider's.
  5. A methods note: the Anthropic OpenAI-compatibility shim silently
     drops all cache-accounting fields; only the native Messages API
     exposes them. Anyone benchmarking through the compat layer would
     falsely conclude Anthropic reports no cache stats.
  6. A second methods note: DeepSeek's cache is disk-persisted and
     content-addressed globally (any prefix, once sent, is cached going
     forward regardless of what was "just primed"), unlike Gemini's
     transient/replica-scoped cache — so the repeated-trial design that
     correctly surfaced Gemini's non-determinism silently self-contaminates
     on DeepSeek (every repeat after the first just hits the *edited*
     variant's own prior occurrence). The fix (single-shot, never-reused
     edits) is itself evidence that experimental design must be adapted
     per provider, not assumed portable.
  7. A generalization check on a second, structurally different prefix
     (prose document, not a tool-schema list) confirms three of four
     provider characterizations unchanged, and sharpens the fourth:
     OpenAI's chunk boundaries are content-anchored (content-defined
     chunking with a ~1024-token target), not fixed absolute-token
     addresses — invisible on a uniform-block prefix, exposed by a
     non-uniform one.
  8. Cross-model-endpoint spot-checks find the same class of subtlety one
     layer down: DeepSeek's 128-token grain is a genuine platform
     constant shared between deepseek-chat and deepseek-reasoner, but the
     two endpoints' chunk *phase* differs, so a fixed nominal prefix
     position doesn't correspond to a fixed absolute token offset once
     you cross model endpoints, not just prefix shapes.
  9. A length-changing-edit check (insertion, not substitution) finds no
     evidence of content-defined/rolling-hash resync on OpenAI or
     DeepSeek — credit is lost past an insertion exactly as pure
     prefix-continuity caching predicts, direct evidence against a
     plausible alternative mechanism and in favor of radix-tree-style
     KV-cache reuse.

## 2. Background
- How each provider implements caching (cache_control breakpoints vs.
  automatic/implicit), briefly, with citations to provider docs.
- Definition of terms used throughout: prefix, perturbation, credited
  tokens, hit fraction, chunk boundary.
- Scope statement: this paper measures invalidation granularity from
  content edits, not time-based cache expiration/TTL behavior (e.g.
  Anthropic's 5-minute ephemeral windows) — a related but distinct
  question, out of scope here.
- Scope statement: all measurements are of the author's own request
  content, read via each provider's own accounting fields. This is not a
  timing side-channel study and makes no attempt to infer or access
  other tenants' cached content.

## 3. Method
- Test artifact: synthetic tool-definition prefix (45 tool schemas,
  ~7.7k tokens), chosen to be large enough to span multiple cache chunks
  and structurally representative of real agent system prompts.
- Perturbation types: single-word edit at controlled offset, header edit,
  trailing whitespace, adjacent-block reorder — see `perturbations.py`
  variant set (7 variants, offsets 0%–100% through the prefix).
- Measurement: prime call (populate cache) → gap → measurement call
  (perturbed prefix) → read exact credited-token field from the response
  (`cache_read_input_tokens` / `prompt_tokens_details.cached_tokens`).
- Per-provider protocol notes: native vs. compat endpoint (Anthropic),
  OpenRouter session pinning (OpenAI), isolation controls (Gemini).
- Repeated-trial design for Gemini once single-shot measurements showed
  variance; isolation control to rule out cross-condition test-harness
  leakage as a confound.
- Inter-call gap timing (2.5-5s depending on provider/script) was not
  held rigorously constant across all scripts; noted here rather than
  treated as a confound, since gap length is orthogonal to the
  content-addressed/deterministic mechanisms being measured and every
  provider's isolation/determinism check used its own fixed gap
  throughout.

## 4. Results
### 4.1 Anthropic — developer-controlled granularity
- Single-block prefix: any edit anywhere → full miss (atomic).
- Static block (cache_control) + uncached tail: static block always fully
  credited regardless of tail edits (`anthropic_multiblock_results.json`).
- Table: block structure vs. credited tokens under each perturbation.

### 4.2 OpenAI — deterministic 1024-token chunks
- 45-position sweep, corrected after removing a self-hit contamination
  bug (documented as its own subsection/callout — real methodological
  finding).
- Table/plot: edit position vs. credited tokens, showing 5 clean +1024
  step transitions (`chunk_sweep_results.json` + `recheck_sweep_outliers.json`).

### 4.3 DeepSeek — deterministic 128-token chunks despite a hedged spec
- 45-position single-shot sweep (after diagnosing that DeepSeek's disk-
  persisted, content-addressed cache breaks the Gemini-style repeated-
  trial design — see methods note): clean monotonic staircase, every
  step an exact multiple of 128 tokens, matching DeepSeek's documented
  64-token cache unit (`deepseek_full_sweep_results.json` +
  `deepseek_recheck_outliers.json`).
- Isolation determinism check: 8 reps of one fixed condition, bit-for-bit
  identical credit (7040/7055) every single time — zero variance
  (`deepseek_isolation_results.json`).
- Notable given DeepSeek's own docs explicitly disclaim a guaranteed hit
  rate ("best-effort... does not guarantee 100%") — measured behavior is
  in fact the most deterministic of the four providers tested.

### 4.4 Gemini — unpredictable realized credit
- Multi-position repeated-trial sweep showing per-position variance
  (`gemini_chunk_sweep_results.json`).
- Isolation control: single fixed condition, 12 reps, nothing else
  touching the API — variance persists (0/3061/7143 recurring values),
  ruling out harness leakage (`gemini_isolation_results.json`).
- Interpretation: consistent with unpinned load-balancing across backend
  replicas with independent cache state, no client-facing session
  affinity (contrast with OpenRouter's `session_id` stickiness).
- Contrast directly with §4.3: same isolation protocol, opposite result
  — this is the paper's clearest apples-to-apples determinism comparison.

## 5. Discussion / Implications
- For agent framework authors: cache-aware prefix design is *possible and
  effective* on Anthropic (you control it), *free but coarse* on OpenAI
  and DeepSeek (align edits to the 1024- or 128-token boundary if you
  care), and *not reliable* on Gemini regardless of what you do.
- Cost-estimation tooling that assumes a fixed hit rate per provider will
  be systematically wrong for Gemini.
- Documented posture is not a reliable predictor of measured behavior:
  the provider with the strongest hedge in its docs (DeepSeek) was the
  most deterministic in practice; the provider with no such hedge
  (Gemini) was the least.
- The compat-shim telemetry gap is a trap for anyone building
  cross-provider observability tooling on an OpenAI-compatible surface.
- Experimental design itself doesn't transfer across providers: the
  repeated-trial protocol that correctly diagnosed Gemini's noise
  silently produces false-positive "determinism" on DeepSeek if you
  don't first understand that its cache is persistent and content-keyed
  rather than session-scoped.
- A uniform-block synthetic prefix can hide mechanism: OpenAI's 1024-token
  finding held at the magnitude level on a non-uniform prefix, but the
  boundary alignment shifted, revealing content-anchored (not
  fixed-address) chunking. Measurement papers using synthetic prefixes
  should vary block-size uniformity, not just count/position, to avoid
  mistaking an aliasing artifact for the true mechanism.
- For agent framework authors specifically: append, don't insert. Adding
  new content at the very end of a prefix costs nothing beyond the new
  content itself; inserting it mid-prefix (e.g. adding a new tool in the
  middle of a tool list) costs at least as much cache credit as editing
  that same spot, and — on every provider tested — never recovers any of
  it downstream, however far past the insertion the identical old content
  continues.

### 4.5 Generalization check — a second prefix shape
- Repeated the core measurements on a structurally different prefix: a
  45-section prose policy-handbook document (no tool schemas or
  parameters), sized to match the original prefix (~7.7k tokens), at the
  same landmark positions used throughout (`prefix_doc.py`,
  `perturbations_doc.py`).
- Anthropic: static block + uncached tail reproduces perfect partial
  credit exactly as before (`doc_multiblock_anthropic_results.json`).
- DeepSeek: 7-position single-shot sweep reproduces a clean monotonic
  128-token-multiple staircase (`doc_sweep_deepseek_results.json`).
- Gemini: non-determinism not only reproduces but is starker — an edit
  at section#1 (immediately after the header) still returned 91% cache
  credit in 2 of 3 reps, underscoring that realized credit tracks
  something other than edit position (`doc_sweep_gemini_results.json`).
- OpenAI: a 7-point sweep showed a non-1024-multiple reading (1792
  tokens), prompting a full 45-position follow-up
  (`doc_full_sweep_openai_results.json`). Result: inter-boundary spacing
  is still a clean +1024 tokens (three consecutive confirmed steps), but
  the *first* boundary is not aligned to a multiple of 1024 from the
  prefix start — something never observed on the uniform tool-list
  prefix. Best interpretation: OpenAI's chunk boundaries are
  content-anchored (rolling-hash/content-defined chunking with a
  ~1024-token target), not fixed absolute-token addresses. The tool
  list's uniform ~155-token blocks made this indistinguishable from
  fixed-address chunking; the doc's non-uniform section lengths exposed
  it. A refinement of the §4.2 finding, not a contradiction.
- Headline: 3 of 4 provider characterizations generalize unchanged across
  prefix shape; OpenAI's generalizes at the magnitude level but reveals a
  more precise mechanism (content-anchored, not fixed-address chunking).

### 4.6 OpenAI cross-validation — OpenRouter vs. direct API
- All OpenAI numbers up to this point were measured through OpenRouter's
  OpenAI-compatible proxy, not api.openai.com directly — an unresolved
  confound (does OpenRouter add its own routing/session logic that could
  alter the numbers?) that wasn't yet disclosed anywhere in this outline.
- Bought a direct OpenAI API key and reran the 7 landmark positions on
  the doc-shape prefix directly against api.openai.com, comparing against
  the existing OpenRouter ground truth (`doc_full_sweep_openai_results.json`).
- Result: 7/7 positions matched exactly, including the total prompt token
  count (5587 in both) — OpenRouter passes through OpenAI's real cache
  telemetry unmodified for this model/prefix (`openai_direct_validation_results.json`).
- Methods footnote: getting the direct API call working required two
  request-shape changes OpenRouter's compat layer silently absorbs —
  `max_tokens` is rejected by gpt-5-mini (`max_completion_tokens` only),
  and `temperature=0.0` is rejected (only the default is supported).
  Worth a line in Methods regardless of the numbers matching.

### 4.7 Larger-model spot-checks
- Single-position (or, for Gemini, single-condition repeated-trial)
  spot-checks on a bigger model per provider family, targeting the
  stated "single model tier tested" limitation cheaply rather than
  leaving it purely as an admitted gap.
- Anthropic (claude-opus-4-8 vs. claude-haiku-4-5): identical behavior —
  static block fully credited (8374/8374) regardless of tail edit, same
  as the small-tier model (`bigmodel_anthropic_results.json`).
- OpenAI (gpt-5 vs. gpt-5-mini, direct API): identical — cached=2816 at
  section#24, exactly matching the mini-tier reference
  (`bigmodel_openai_results.json`).
- DeepSeek (deepseek-reasoner vs. deepseek-chat): NOT identical, but not
  random either. At all 4 positions tested (8, 16, 24, 40), reasoner
  credits systematically more than chat at the same nominal position —
  yet every single reading, on both models, remains an exact multiple of
  128 tokens (`bigmodel_deepseek_results.json`,
  `bigmodel_deepseek_multipos_results.json`). Interpretation: the
  128-token grain itself is confirmed as a shared platform constant
  across DeepSeek's model endpoints, but the chunk *phase/alignment*
  differs between deepseek-chat and deepseek-reasoner — plausibly because
  the reasoner endpoint prepends a different amount of hidden
  scaffolding, shifting where a given nominal prefix position lands in
  the model's actual token stream. A genuine finding, not a spot-check
  null result — parallels the OpenAI content-anchored-boundary nuance
  in §4.6 (a uniform block-position index isn't equivalent to an
  absolute token offset once you cross model endpoints, not just prefix
  shapes).
- Gemini (gemini-3.1-pro-preview vs. gemini-2.5-flash): 3/3 reps at
  section#24 returned cached=0 with zero variance
  (`bigmodel_gemini_results.json`), contrasting with flash's variance at
  the same position (0/0/2038 across 3 reps on the doc-shape sweep).
  Reported cautiously: 3 reps is a much smaller sample than the 12-rep
  isolation checks used to establish flash's non-determinism, so this is
  not strong evidence that the pro tier is more deterministic — only
  that no variance happened to appear in this small a sample. Flagged as
  an open question, not a claim.
- Also surfaced two direct-API parameter quirks needed to reach the
  larger tiers: claude-opus-4-8 rejects `temperature` outright
  ("deprecated for this model"), and gemini-2.5-pro / gemini-3-pro-preview
  were both already deprecated for new API keys by the time of testing —
  used gemini-3.1-pro-preview instead. `AnthropicNativeClient` gained a
  `send_temperature` option to match `CacheProbeClient`'s existing one.

### 4.8 Length-changing edits — insertion, not just substitution
- Every perturbation up to this point has been a same-length-ish word
  substitution. Real prompt edits (adding a tool, extending a parameter
  description) are often insertions that shift the absolute token offset
  of everything downstream — untested until now, and the natural next
  question raised by the content-anchored-boundary (§4.6) and
  endpoint-phase-shift (§4.7) findings: does a length change let
  downstream content resync with the cache (evidence of true
  content-defined/rolling-hash chunking), or is credit lost entirely
  past the insertion point (pure prefix/LCP-continuity caching, as used
  by radix-tree-style KV-cache reuse systems)?
- Method note: the naive comparison (insertion vs. a substitution at the
  *start* of the same section) is not apples-to-apples, because
  appending new content after a section's full original text moves the
  actual byte-level divergence point later than a substitution in that
  section's first sentence. Caught this via an initial DeepSeek reading
  that looked like resync evidence (1792 credited vs. a naively-chosen
  896 reference) until a corrected reference (substitution in the
  section's *last* sentence, matching the insertion's true divergence
  point) gave 1920 — the original "evidence" evaporated. Worth its own
  methods-section callout: comparing edit conditions requires matching
  the actual byte-divergence offset, not just the nominal section index.
- Corrected result, OpenAI (direct API): insertion credited 1792,
  identical to both start- and end-of-section substitution references
  (both 1792, since sections 16-23 form one flat plateau on OpenAI's
  coarser grain — see §4.2/4.6). No resync evidence
  (`openai_insertion_check_results.json`).
- Corrected result, DeepSeek: insertion credited 1792, *below* the
  correct end-of-section reference of 1920 — insertion costs slightly
  more than a same-position substitution, exactly as pure
  prefix-continuity caching predicts (extra shifted tokens fall just
  short of the next chunk boundary). No resync evidence
  (`deepseek_insertion_check_results.json`).
- Gemini: 3 reps returned {0, 5096, 5096} — the same near-full-credit
  value (5096) that recurs across unrelated conditions throughout this
  project's Gemini data (control, section#1 edits, section#45 edits),
  reinforcing that Gemini's realized credit doesn't track the edit's
  content or position at all, insertion included — it reflects whichever
  backend replica answered, not anything about the request
  (`gemini_insertion_check_results.json`).
- Anthropic not retested here: its cache_control mechanism is fully
  developer-explicit (block granularity, not position-inferred), so an
  edit's length can't change the answer — already fully characterized by
  §4.1/§4.5.
- Headline: no evidence of content-defined/rolling-hash resync on any
  provider tested. Length-changing edits behave exactly as pure
  prefix-continuity caching predicts — consistent with (though not
  direct proof of) radix-tree-style KV-cache reuse as the underlying
  mechanism. Practical implication for §5: appending new content at the
  very end of a prefix is strictly safer than inserting mid-prefix,
  which costs at least as much credit as an equivalent substitution and
  never recovers it downstream.

## 6. Threats to Validity / Limitations
- Two synthetic prefix shapes tested (tool-schema list, prose document);
  both are synthetic surrogates for real agent system prompts and may
  still not generalize to other structures (e.g. few-shot examples,
  retrieved-chunk RAG contexts with heterogeneous source formatting).
- Primary results use one model per provider family (haiku-class /
  gpt-5-mini / deepseek-chat / gemini-2.5-flash). Spot-checked (not
  systematically swept) against a larger/different-pipeline model per
  provider (§4.7): Anthropic and OpenAI reproduced identically; DeepSeek's
  grain held but its boundary phase shifted between chat and reasoner;
  Gemini's pro-tier determinism remains genuinely untested at the sample
  size that would be needed to draw a conclusion (only 3 reps run, vs.
  12 for flash).
- Gemini non-determinism (and DeepSeek's determinism) characterized at one
  point in time; provider-side infra changes could alter or fix either.
- No access to provider-internal ground truth — telemetry fields are
  trusted as accurate but are still self-reported by the provider.

## 7. Conclusion
- Restate: "prompt caching" is (at least) four different reliability
  contracts, not one mechanism; measured directly via usage telemetry
  rather than timing.

## Appendix
- Full per-position tables for all four providers.
- Script listing / repro instructions (this pilot dir doubles as the
  artifact repo).

---
## Scaffolding decisions (settled)
1. Target: arXiv-only preprint, no conference/journal submission planned.
2. Scope: 4 providers (Anthropic, OpenAI, DeepSeek, Gemini) — DeepSeek
   added because it tested a genuinely new axis (documented-hedge vs.
   measured-determinism), not just another data point. Open to more only
   if a candidate clears the same bar.
3. Figures: matplotlib step-plots for §4.2/4.3 (OpenAI, DeepSeek), still
   TBD whether Gemini's variance is better shown as a plot or a table.
