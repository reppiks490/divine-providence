# Change Record — PROMETHEUS v0.5 Experiment Routing

**Date:** 2026-09-25
**Actor:** ChatGPT / PROMETHEUS build session
**Request:** Continue the PROMETHEUS evolution loop from the verified v0.4 checkpoint.

## Before

v0.4 diagnosed sibling disagreement and tracked stale result lineage, but the loop always built an experiment from the first detected disagreement before considering replay eligibility. Healthy role specialization, source-health problems, or stale bound contracts could therefore reach the replay stage unnecessarily.

## Change

- added immutable `ExperimentRouteDecision` artifacts;
- added explicit route actions for replay, fresh-evidence deferral, and specialization abstention;
- added qualitative research-priority bands rather than scalar experiment scores;
- added deterministic cause-to-route policy in `policy/experiments.py`;
- made routing input-order invariant;
- added a preflight lineage manifest and staleness report before any replay;
- stale contract/plugin lineage now blocks adversarial replay itself, not only DAEDALUS handoff;
- source-health and availability mismatches defer until evidence is fresh;
- healthy intentional specialization abstains without creating a false rejection;
- ambiguity can run a bounded information-gain replay without pretending the cause is known;
- introduced `DeferredExperiment` to distinguish “not eligible to run” from “tested and rejected”;
- the live loop chooses an actionable diagnosis instead of blindly using the first sorted disagreement;
- final result lineage now includes the preflight lineage, staleness decision, and route artifact; and
- CLI demo output now exposes route action, priority band, and reason code; and
- final review hardened replay policy so route-specific probes cannot drop the universal `leakage`, `missingness`, or `reproducibility` guardrails; and
- final review bound `ExperimentSpec` identity to the route/preflight lineage so negative-result reuse cannot cross changed sibling/plugin contract fingerprints.

## Research/runtime capability record

Native Deep Research was not exposed in this host runtime and therefore was not claimed as invoked. Exa and Firecrawl were used for external research-pattern checks. Tavily research was attempted and returned a plan usage-limit error; that failure is explicitly recorded rather than treated as a successful source.

## Authority impact

None. This change only decides which PROMETHEUS research experiment is justified next. Production, broker/order, supervisory, data-fabric, durable-evidence, and scientific-promotion ownership remain with their existing systems.

## Verification intent

The final gate must prove:

- stale lineage prevents adversarial replay;
- healthy specialization produces deferral/abstention, not rejection;
- actionable disagreement outranks specialization deterministically;
- ambiguity remains labeled ambiguous while still allowing a bounded replay probe;
- exact negative-result reuse still works;
- DAEDALUS handoff remains gated by clean final lineage; and
- no production/broker/sibling-write authority appears in `src`.

**Stale when:** routing policy, diagnosis taxonomy, contract-fingerprint semantics, or authority boundaries change.
