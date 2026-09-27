# PROMETHEUS v0.5 Verified Checkpoint

**Date:** 2026-09-25  
**Branch:** `work/prometheus-v0.5-experiment-router`  
**Commit:** `444d978134f2b138e647b2c6c9e219f83074ac75`

## What v0.5 adds

PROMETHEUS now inserts a deterministic experiment-routing gate between disagreement diagnosis and FORGE replay.

Key additions:

- immutable `ExperimentRouteDecision` artifacts;
- qualitative research priority bands instead of a scalar "best experiment" score;
- preflight lineage and contract/plugin staleness checks before replay;
- replay preference for actionable/reducible disagreement over healthy specialization;
- `DEFER_FRESH_EVIDENCE` for stale, unavailable, or source-unhealthy evidence;
- `ABSTAIN_SPECIALIZATION` when sibling differences are explained by role boundaries;
- `DeferredExperiment` artifacts so "not eligible to run" is not mislabeled as "rejected";
- ambiguity-reduction replay without changing the diagnosis away from `IRREDUCIBLE_AMBIGUITY`;
- universal replay guardrails `leakage`, `missingness`, and `reproducibility` preserved across every replay-eligible route;
- route-specific checks can only add to those universal guardrails;
- exact negative-result reuse is bound to the immutable route/preflight contract context, preventing reuse across changed sibling/plugin fingerprints; and
- CLI output now exposes route action, priority band, reason code, and route artifact identity.

## Verification

Fresh verification from the exact committed tree:

- Python compile check: passed
- Full test suite: **77 passed in 0.18s**
- Deterministic demo: passed
- Production-authorization scan: passed
- AST-based sibling runtime-import scan: passed
- Broker/order dependency scan: passed
- Tracked bytecode scan: passed
- Git diff check: passed
- Working tree: clean

## Host research capability record

- Native Deep Research was not exposed in this host run and was not claimed as invoked.
- Exa research succeeded and informed information-gain / deterministic experimentation patterns.
- Firecrawl developer search succeeded and informed stale-evidence / deterministic-decision / replay-provenance patterns.
- Tavily research was attempted and returned plan usage-limit status 432; it was recorded as unavailable for this run rather than treated as successful evidence.

## Authority boundary

No production authority was added. PROMETHEUS still cannot place orders, control brokers, override ATHENA, manufacture NEXUS/ARGUS evidence, write AION ownership state, or represent DAEDALUS acceptance. The highest handoff remains `READY_FOR_DAEDALUS_REVIEW`, and only from a fresh, complete, engineering-pass research run.

## Remaining major integration work

- direct AION durable-evidence export contract;
- direct DAEDALUS review-ingress contract;
- live NEXUS service ingestion;
- current live ARGUS/ATHENA adapters;
- signed host plugin execution attestations;
- protected DAEDALUS holdout evaluation; and
- production-independent performance/scale testing over recovered real corpus workloads.
