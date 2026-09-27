# H3 — ROBUST INTERROGATION ENGINE IMPLEMENTATION PLAN

## Mission
Choose the next information-producing action while rejecting infeasible, redundant, fragile, expensive or potentially misleading acquisitions.

ResearchAction types: QUERY_SIBLING, QUERY_SOURCE, SEARCH_LITERATURE, ACQUIRE_DATASET, RUN_EXPERIMENT, RUN_ABLATION, RUN_COUNTERFACTUAL, INSPECT_REVISION, INSPECT_PROVENANCE, WAIT_FOR_OBSERVATION, REQUEST_HUMAN_JUDGMENT, ABSTAIN. No order/trade action types exist.

## H3.1 Action contract
Store action ID, investigation, type, target system/capability, affected hypotheses, creation time, expected cost/latency, operational risk, reversibility, effect class, required evidence and policy version.

## H3.2 Feasibility gate
Failures: integration unavailable, contract incompatible, rights/auth/entitlement blocked, source unhealthy, budget/deadline exceeded, security blocked, causally invalid, redundant, execution forbidden. Feasibility is evaluated before information value.

## H3.3 Elimination baseline
ActionOutcomeModel measures expected/min/max hypotheses eliminated. This is the simplest planning baseline.

## H3.4 Exact discrete EIG baseline
Only when an actual probability model exists. Never normalize EvidenceScore into fake probabilities. InformationEstimate stores estimator/version, expected gain, bounds/error, sample count/seed, compute cost, latency and assumptions.

## H3.5 Pareto planner
Maximize information, elimination, independence, reliability and robustness; minimize cost, latency, risk, redundancy and misinformation. Pareto-filter before deterministic policy tie-break.

## H3.6 Robustness + misinformation firewall
Stress PRIOR, LIKELIHOOD, SOURCE_RELIABILITY, EVIDENCE_DEPENDENCE, OUTCOME_NOISE and REGIME. Record nominal/min/median/max gain and rank stability. If confidence rises while prospective predictive quality materially worsens under plausible misspecification, mark POTENTIALLY_MISINFORMATIVE and block default auto-selection.

## H3.7 Stopping/abstention
Explicit reasons: RESOLVED_ENOUGH, MARGINAL_VALUE_TOO_LOW, BUDGET_EXHAUSTED, DEADLINE_EXHAUSTED, SOURCE_LIMITED, MODEL_LIMITED, REDUNDANT_EVIDENCE_ONLY, WAIT_FOR_OBSERVATION, UNKNOWN_NOVEL, ABSTAIN. Never force resolution from inadequate evidence.

## H3.8 Realized information
Track expected-vs-realized information, elimination, cost, latency, contradiction/UNKNOWN deltas and downstream usefulness. Calibrate by action family and estimator version.

## H3.9 Bounded sequential planner
One-step stays baseline. Initial multistep: depth <=2, bounded nodes and compute. No unbounded autonomous research tree. Do not claim greedy optimality unless structural conditions are actually verified.

## H3.10 Tournament
Compare random benchmark, elimination, nominal EIG, Pareto, robust EIG and misinformation-aware planner across frozen worlds: cheap discriminator, correlated evidence, fragile EIG, expensive perfect question, unavailable perfect source, optimal wait, unknown mechanism, misinformation amplification, source failure/replan, restart/no duplicate dispatch.

Promotion requires no integrity/causal/authority regression and material benefit over simpler baseline.
