# PROMETHEUS v0.5 — Experiment Routing and Replay Eligibility

PROMETHEUS v0.5 inserts a deterministic research-routing layer between disagreement diagnosis and FORGE replay. The router decides **what research action is justified next**; it does not decide whether a trading strategy, model, or production system should be deployed.

## Why this layer exists

v0.4 could diagnose disagreement and later mark result lineage stale, but it still constructed an experiment from the first disagreement and ran replay before staleness was considered. That meant healthy sibling specialization or stale contract context could consume research work even when replay was not justified.

v0.5 separates three questions:

1. **What disagreement is most useful to investigate?**
2. **Is the evidence fresh and replay-eligible?**
3. **If replay runs, what does the experiment show?**

Routing never substitutes for the later adversarial/replay result.

## Routing contract

`ExperimentRouteDecision` is an immutable, content-addressed artifact containing:

- selected disagreement case and diagnosis;
- action;
- qualitative priority band;
- stable reason code;
- required adversarial checks;
- evidence IDs;
- preflight lineage ID; and
- the staleness-report ID used for the decision.

The action set is deliberately small:

- `RUN_REPLAY` — bounded deterministic replay is justified;
- `DEFER_FRESH_EVIDENCE` — replay is blocked until causal evidence is fresh; and
- `ABSTAIN_SPECIALIZATION` — disagreement is currently explained by healthy sibling role specialization, so no replay is justified.

Priority is ordinal (`HIGH`, `MEDIUM`, `LOW`, `NONE`) and is **not** a scalar quality score.

Every `RUN_REPLAY` route retains the non-negotiable guardrails `leakage`, `missingness`, and `reproducibility`. Cause-specific checks may add `ablation` or `perturbation`, but routing cannot weaken the universal safety set.

## Cause-to-route policy

- `EVIDENCE_MISMATCH` -> high-priority replay.
- `REPRESENTATION_MISMATCH` -> high-priority representation-sensitivity replay.
- `MODEL_BLIND_SPOT` -> high-priority targeted replay when that diagnosis becomes evidence-supported.
- `REGIME_BOUNDARY` -> medium-priority boundary probe.
- `IRREDUCIBLE_AMBIGUITY` -> medium-priority bounded ambiguity-reduction replay; the replay does not relabel the cause.
- `AVAILABILITY_MISMATCH` -> wait for fresh causal availability evidence.
- `SOURCE_HEALTH_ISSUE` -> wait for fresh source-health evidence.
- `INTENTIONAL_SPECIALIZATION` -> abstain unless contracts or shared evidence later change.

When multiple cases exist, replay-eligible reducible uncertainty outranks deferral or healthy-specialization cases. Ties are broken deterministically by content-addressed diagnosis identity, so input order cannot change the decision.

## Preflight lineage

Before routing, PROMETHEUS builds a preflight `ResearchLineageManifest` over the observations, plugin evidence, plugin contribution artifacts, disagreement cases, diagnoses, and plugin audit. The same sibling/plugin fingerprints used by the run are attached to this manifest.

A `StaleEvidenceReport` is computed before replay. Any stale required fingerprint globally vetoes replay for that run, even when an otherwise actionable disagreement exists.

This is intentionally conservative: stale evidence is not treated as a negative experiment result.

`ExperimentSpec` identity is also bound to the immutable route context. Exact negative-result reuse therefore requires the same routed case, diagnosis, preflight lineage, and contract/plugin fingerprints; a changed contract creates a different experiment identity rather than reusing stale negative memory.

## Deferred research is not rejection

When replay is blocked or intentionally skipped, PROMETHEUS emits a `DeferredExperiment` rather than `RejectedHypothesis`.

- Rejection means an experiment ran or an exact negative result was reused and the hypothesis failed the research gate.
- Deferral means the experiment was **not eligible to run** under the present evidence/authority state.

Deferred artifacts record an explicit rerun condition. No DAEDALUS review packet is generated.

## Existing authority boundaries remain unchanged

The router does not:

- authorize production;
- rank or choose trades;
- mutate NEXUS replay/data truth;
- reinterpret ARGUS candle proxies as authenticated microstructure;
- override ATHENA supervisory state;
- write AION durable sibling memory directly; or
- represent DAEDALUS acceptance.

It only selects PROMETHEUS research work.

## External design evidence used in this cycle

The design was cross-checked against experiment systems that separate readiness from outcome, uncertainty/information-gain research methods, and stale-evidence/provenance patterns. Exa and Firecrawl were available and used. The Tavily research endpoint was attempted but returned a plan usage-limit error. Native Deep Research was not exposed in this host cycle and was not claimed as invoked.

**Stale when:** disagreement taxonomy, route policy, contract-fingerprint semantics, adversarial check vocabulary, or sibling authority boundaries change.
