# VECTOR ∞ — Master Handoff Archive

**Maximum-fidelity consolidated work product through 24 September 2026**

> CURRENT AUTHORITY STATUS: SHADOW / ADVISORY / OFFLINE-SYNTHETIC ONLY. NO VERIFIED REPOSITORY IMPLEMENTATION, PRODUCTION MODEL/WEIGHT CHANGE, REGISTRY PROMOTION, EXECUTION AUTHORITY, SIBLING-SYSTEM MUTATION, LIVE-ADVISORY PROMOTION, OR LIVE TRADING PARAMETER CHANGE.

## 0. Handoff Read-Me

This archive consolidates all VECTOR ∞ work I can substantiate from the current conversation,
retrievable prior VECTOR context, and the previously generated snapshot. It is designed for handoff
to another model/agent without silently upgrading proposals into completed implementation.

CURRENT AUTHORITY STATUS: SHADOW / ADVISORY / OFFLINE-SYNTHETIC ONLY. NO VERIFIED REPOSITORY IMPLEMENTATION, PRODUCTION MODEL/WEIGHT CHANGE, REGISTRY PROMOTION, EXECUTION AUTHORITY, SIBLING-SYSTEM MUTATION, LIVE-ADVISORY PROMOTION, OR LIVE TRADING PARAMETER CHANGE.

The archive contains completed design work, reported synthetic/adversarial experiments, negative
findings, safety invariants, interface contracts, promotion gates, risks, and the planned next cycle.
It does not include private chain-of-thought, inaccessible raw tool logs, or repository/runtime
artifacts that were never actually created.

## 1. Mission and Ownership Boundary

VECTOR ∞ is the Adaptive Trend Intelligence layer for the broader Icarus ecosystem. It is meant to
learn how trends are born, strengthen, fragment, resume, exhaust, reverse, and fail across assets,
regimes, and horizons — while remaining optional to every sibling system.

VECTOR owns trend inference, trend memory, expert competence, adaptation logic, and trend-model
uncertainty. VECTOR does not own orders, portfolio risk, broker connectivity, canonical source data,
global supervision, sibling internal state, or research promotion outside its own bounded registry.

Zero Critical-Path Authority Contract:
• No order pipeline calls VECTOR synchronously.
• No existing process waits for VECTOR.
• No sibling schema must change just to accommodate VECTOR.
• Online learning cannot overwrite production.
• Model promotion does not automatically change execution.
• Unknown/stale/malformed VECTOR output is discarded; consumers continue.
• New candidates begin in shadow, then bounded canary if ever approved.

## 2. Operating Loop

OBSERVE → DECOMPOSE → ENCODE → INFER → ROUTE → FUSE → PUBLISH → OBSERVE OUTCOME →
ATTRIBUTE → LEARN → GENERATE CHALLENGERS → REPLAY → ATTACK → COMPARE →
PROMOTE/REJECT → SHADOW → CANARY → ROLLBACK → DISTILL → REPEAT ∞.

Observe uses immutable causal snapshots. Learning produces candidates rather than silently rewriting
the currently trusted model. Promotion is versioned and reversible.

## 3. Trend Genome

A TrendIntelligence representation is intended to carry:
direction; strength; persistence; maturity; velocity; acceleration; structural integrity;
participation; volatility compatibility; continuation probability; exhaustion probability;
reversal pressure; trend-quality confidence; uncertainty; novelty/OOD state; and provenance.

Example semantic packet:
“Uptrend / mature / structurally intact / decelerating / participation weakening / 4H supportive /
5m exhaustion rising / continuation confidence 0.68 / reversal pressure 0.37 / uncertainty 0.14.”

The packet is evidence, not an instruction.

## 4. Mixture-of-Experts Architecture

VECTOR rejected two extremes as the primary design:
(1) one universal trend model, which risks over-generalizing; and
(2) fully separate asset/timeframe models, which create model sprawl and weak shared learning.

Preferred architecture: a shared mixture-of-experts trend fabric. Experts can include deterministic
and learned trend estimators, state-space/Kalman variants, multiscale slope/curvature, structure
evolution, change-point models, persistence/hazard models, volatility-normalized momentum,
cross-sectional strength, cross-asset factor trend, analogue retrieval, regime-conditioned learners,
sequence models, and later deep temporal representation models.

The router selects trust contextually rather than declaring a universally best expert.

## 5. Expert Competence Tensor

The Competence Tensor stores where each expert is reliable or unreliable. Conceptual fields:
expert_id; context_embedding; posterior_competence; competence_uncertainty; sample_support;
effective_sample_size; calibration_error; recent_decay; drift_score; failure_atlas_penalty;
ood_distance; recurrent_regime_similarity; current_revalidation_score; allowed_authority.

Key invariant:
model confidence ≠ competence ≠ allowed authority.

An expert may be very confident but poorly supported in the current context. Another expert may be
weak at directional prediction but strong at detecting trend termination. VECTOR should preserve
those distinctions.

## 6. Adversarial Router Lab

The Adversarial Router Lab is the latest explicit evidence-backed baseline for promotion discipline.
Its core conclusion was that the router must have an independent safety plane and that authority
must decay under OOD, competence loss, deceptive recurrence, and malformed state.

Key results are preserved in the experiment ledger (EXP-002 through EXP-006). The lab established:
• OOD-aware fail-open routing;
• deceptive-regime competence veto;
• concentration auditing without arbitrary load balancing;
• deterministic checkpoint/resume requirements;
• malformed/NaN fail-open invariants.

These findings remain synthetic/offline. They do not prove live alpha or authorize production.

## 7. Independent Router Safety Auditor

Architecture:
Experts → Competence Tensor → Primary Router → Router Safety Auditor → TrendIntelligencePacket.

The auditor does not predict direction. It asks whether the router’s proposed expert/weight choice is
independently defensible. It monitors routing concentration, expert/context mismatch, competence
decay, unexpected regret, calibration decay, OOD distance, regime alias risk, false recurrence,
cross-horizon contradiction, expert correlation, router entropy collapse, and Failure-Atlas matches.

The auditor should not share every feature/objective with the router, reducing common-mode failure.

## 8. Trend Failure Atlas

VECTOR explicitly learns failure mechanisms:
false breakouts; exhaustion without reversal; reversal without follow-through; acceleration traps;
volatility pseudo-trends; correlation-driven moves; liquidity sweeps; parabolic late-stage
continuation; failed continuation after compression; and regime-change destruction.

Failure memories should influence competence, revalidation, challenger generation, and promotion.
A failed propagation event is recorded rather than discarded.

## 9. Cross-Horizon Temporal Propagation Graph (CHTPG)

The original static hierarchy 1m→5m→15m→1H→4H→D→W was upgraded into a probabilistic propagation
graph. Each directed horizon edge learns propagation probability/hazard, expected delay, delay
uncertainty, persistence requirements, volatility dependence, regime dependence, trend-maturity
dependence, participation/liquidity dependence, false-propagation frequency, calibration,
competence, drift, and uncertainty.

Transition taxonomy:
NOISE
PULLBACK
LOCAL REVERSAL
PROPAGATION CANDIDATE
PROPAGATING TRANSITION
HTF TRANSITION CONFIRMED
FAILED PROPAGATION

Temporal firewall:
A 1m reversal cannot directly set 4H=BEARISH. It can only alter the estimated probability of a 4H
transition. Conversely, a bullish 4H state does not erase a real 5m bearish trend; it changes its
interpretation to a local bearish trend inside a bullish higher-horizon context.

## 10. Propagation Drift Sentinel

The propagation classifier degraded sharply under deliberately shifted synthetic conditions
(EXP-008). A rolling MMD-style sentinel then separated normal and deliberately shifted windows in
the reported synthetic construction (EXP-009).

Operating principle:
cross-horizon distribution changes → propagation authority decays → transition claims are
downgraded → revalidation is required.

This prevents historical propagation probabilities from being treated as permanent laws.

## 11. Evidence Conservation Engine

Large confluence systems can produce false certainty because multiple indicators/assets/timeframes
may be manifestations of the same event. VECTOR therefore replaces raw signal count with effective
independent evidence mass.

Core conservation law:
Adding a perfectly redundant observation should contribute approximately zero marginal evidence.

Related invariants:
• removing one of many near-identical observations should barely change belief;
• genuinely independent useful evidence may materially change belief;
• uncertain dependency reduces novelty credit;
• dependency is regime-conditioned, not permanent;
• tail dependence must be treated separately from ordinary dependence.

EXP-010 demonstrated the duplicate attack failure mode and the value of dependency-adjusted
aggregation in a synthetic construction.

## 12. Dynamic Evidence Lineage Graph (DELG)

Every observation should carry provenance:
source_id; instrument; originating event/window; horizon; transformation ancestry; model ancestry;
upstream factors; timestamp; propagation_parent; root_lineage; lineage_version.

Evidence classes:
CLONE — essentially identical information.
DERIVATIVE — transformed/propagated existing information.
CORRELATED-NOVEL — overlapping but incrementally informative.
INDEPENDENT-NOVEL — materially new information.

Propagation descendants preserve root lineage. A successful propagation can add new persistence
evidence, but it cannot regenerate the ancestor’s original directional evidence.

## 13. Information Novelty

VECTOR’s preferred question is no longer “how many things agree?” but “how much decision-relevant
information does this observation add beyond evidence already admitted?”

Conceptual score:
INS(e | E_previous)

Effective evidence can be treated conceptually as:
reliability × competence × novelty × calibration × lineage_integrity.

This is an architectural quantity, not yet a production formula.

## 14. Latent Common-Cause Resolver (LCCR)

Known lineage is insufficient when several observations share an unobserved driver. LCCR therefore
adds a latent-dependency layer above explicit provenance.

Each visible signal is decomposed conceptually into:
common_component + idiosyncratic_residual.

The hidden-common-cause experiment (EXP-012) was deliberately important because factor compression
did NOT outperform the unconstrained predictor. That negative finding prevents VECTOR from
mistaking an elegant factor explanation for superior prediction.

Resulting rule:
Use soft evidence conservation. Discount shared components, but preserve residual novelty.

LCCR state may include latent_factor_id, member_sources, factor_exposure, residual_novelty,
lag_structure, regime_condition, tail_condition, factor_uncertainty, confounder_probability,
identifiability_status, and validity_horizon.

## 15. Causal Confidence Firewall

VECTOR separates:
predictive dependence confidence;
latent-common-cause probability;
directional temporal influence;
causal-identification status.

A strong predictive or lagged edge may coexist with:
causal_status = UNIDENTIFIED.

The system should never upgrade predictive association into causal authority merely because the
relationship is statistically useful.

## 16. Dependency Graph Drift Controller (DGDC)

Evidence relationships change. Dependency graphs are versioned artifacts rather than permanent
metadata.

Conceptual graph version fields:
graph_id; regime_signature; edge_distribution; lag_structure; scale_structure; tail_structure;
support; calibration; uncertainty; created_at; last_validated_at; validity_horizon.

Lifecycle:
ACTIVE → WATCH → QUARANTINED → (RECALLED or CHALLENGER) → SHADOW-VALIDATED → ELIGIBLE.
Old graphs become DORMANT rather than immediately deleted.

When graph drift rises, evidence-conservation authority decays. VECTOR first tests whether a dormant
graph truly recurs; otherwise a new graph remains a shadow challenger.

Normal-state and tail-state dependency graphs are monitored separately.
EXP-013 established that stale graphs can be actively harmful in a synthetic dynamic system.

## 17. Evolving TrendIntelligencePacket Contract

The interface is designed to expose auditability rather than a single opaque confidence score.

Candidate fields:
schema_version
model_version
source_instant
timestamp
TTL
provenance
direction/state
predictive_confidence
conserved_confidence
uncertainty
OOD score
expert competence
allowed_authority
dependency_graph_id/version
graph_stability
graph_age
regime_similarity
recurrence_confidence
tail_graph_state
dependency_drift_score
raw_sources
known_lineage_families
estimated_latent_families
effective_independent_sources/evidence_mass
largest_evidence_family_share
novelty_score
lineage_integrity
common_factor_share
residual_novelty
causal_identifiability

Consumers must be able to reject stale/unknown packets without disruption.

## 18. Checkpoint / Resume Contract

A valid checkpoint must include more than model weights. The synthetic exact-match replay motivated
persisting at least:
learner state;
expert competence/posteriors;
support counters/effective sample state;
calibration state;
drift state;
router/auditor state where necessary;
active/dormant graph version IDs;
lineage/version metadata needed for deterministic continuation.

Checkpoint restore must not silently promote a challenger or change authority level.

## 19. Fail-Open Contract

Fail-open rejection conditions include:
NaN/Inf;
schema mismatch;
expired TTL;
missing context;
unknown model version;
unknown graph version;
corrupt uncertainty;
corrupt lineage;
invalid dependency state;
unavailable VECTOR service.

Default behavior:
reject VECTOR contribution → retain prior safe consumer behavior → preserve sibling operation.

The failure itself may be logged/observed, but it cannot become a reason to block execution owned by
another subsystem.

## 20. Promotion / Champion-Challenger Gate

VECTOR adaptation is bounded. A candidate may become eligible only after passing relevant tests from
the promotion matrix. Passing does not necessarily replace the entire model; it can authorize only
a bounded routing weight within a validated competence domain.

Synthetic success, scheduler execution, or an attractive research result is not sufficient for
registry/champion/live-advisory/execution promotion.

Real Icarus replay, reproducibility, leakage controls, costs/latency, rollback, and boundary tests
remain mandatory before any production-adjacent authority.

## 21. Risks and Failure Modes

• Meta-overfitting in the router/competence model.
• Sparse competence cells creating false certainty.
• Common-mode failure if the safety auditor is too similar to the primary router.
• Shadow-label latency and delayed outcome attribution.
• Regime aliasing and false recurrence.
• Horizon leakage and developing higher-timeframe bar ambiguity.
• Event double counting and recursive confidence inflation.
• Dependency-model overfitting and stale-graph harm.
• False compression of genuinely independent evidence.
• Nonlinear, lagged, or hidden confounding.
• Tail dependence instability and sparse tail samples.
• Graph churn from over-sensitive change detection.
• Causal language exceeding what observational evidence identifies.
• Computational growth across asset × horizon × regime × graph versions.
• False confidence from cloned/transformed/propagated sources.
• Authority leakage into sibling systems if interface contracts are weakened.

## 22. Historical/Conflicting Artifact Handling

Historical design context that must NOT override the current stricter checkpoint:
An older executive-summary artifact referred to an “adaptive-gating champion” being selected/planned
for registry/shadow use. That language is not treated as a current verified promotion. The current
master truth requires reproducible present evidence and real implementation/replay before registry,
champion, live-advisory, or execution promotion. The Adversarial Router Lab remains the explicit
baseline checkpoint for authority decisions.

## 23. Current Next Cycle

VECTOR Transition Arbitration & Hysteresis Lab

Primary question: When should VECTOR admit that its world model changed?

Required adversarial scenarios:
• rapid A→B→A transitions;
• gradual drift;
• short-lived shock versus durable regime change;
• false change alarms;
• competing old/new dependency graphs;
• graph thrashing;
• delayed confirmation;
• old-regime recurrence;
• transitions where no graph deserves full authority.

Desired component: Transition Arbitration Controller (TAC) with asymmetric enter/exit evidence,
hysteresis, old/new authority blending, dormant-graph recall only after current validation,
shadow challenger learning, rollback support, and an explicit NO-TRUSTED-GRAPH state.

## 24. Implementation Sequence When Repository/Runtime Is Available

1. Verify the actual Icarus/VECTOR repository and authoritative data runtime.
2. Freeze reproducible baselines, deterministic seeds where appropriate, and artifact hashes.
3. Create the formal design spec and implementation plan under repository process rules.
4. Implement versioned TrendIntelligencePacket + fail-open consumer adapter first.
5. Implement replay/evaluation harness before adaptive learning.
6. Reproduce Adversarial Router tests from code.
7. Add Competence Tensor + Router Safety Auditor in shadow.
8. Add CHTPG + propagation drift tests.
9. Add evidence-lineage/conservation tests.
10. Add LCCR/DGDC only after regression suites exist.
11. Run real walk-forward Icarus replay with transaction costs, latency, regime segmentation,
    leakage audits, checkpoint/resume, failure injection, and rollback.
12. Keep promotion shadow-only until current reproducible evidence clears the complete gate.

## 25. Current Truth Boundary

COMPLETED:
• Architecture/design work described in this archive.
• Reported synthetic/adversarial experiments in the experiment ledger.
• Safety invariants, interfaces, promotion tests, failure modes, and next-cycle design.

NOT COMPLETED / NOT CLAIMED:
• Verified repository implementation.
• Production model/weights.
• Model registry mutation.
• Real Icarus/VECTOR replay.
• Live-market validation.
• Broker/execution integration.
• Sibling-system mutation.
• Live-advisory authority.
• Champion promotion based on current reproducible implementation.
• Artifact hash for a VECTOR implementation.
• Persistent self-training runtime.

## Appendix A — Experiment Ledger

### EXP-001 — Contextual competence routing baseline
- **Type:** Synthetic/offline
- **Result:** Historical synthetic comparison reported ~64.6% for competence-aware routing vs ~58.7% for the champion/general baseline.
- **Interpretation:** Supports contextual expert selection rather than globally fixed expert trust.
- **Promotion status:** NOT ELIGIBLE — synthetic only
- **Notes:** Retrieved from prior VECTOR context; exact generator/seed not preserved in current accessible record.

### EXP-002 — OOD-aware fail-open routing
- **Type:** Synthetic/adversarial
- **Result:** 50,000 observations; 15% deliberate OOD contamination. Generalist 59.45%; naive specialist router 65.78%; OOD-aware fail-open router 66.36%; all deliberately injected OOD packets rejected in the reported construction.
- **Interpretation:** OOD should reduce authority and trigger fallback rather than force a nearest-expert choice.
- **Promotion status:** BASELINE EVIDENCE ONLY
- **Notes:** Architecture validation; not market-alpha evidence.

### EXP-003 — False regime recurrence / deceptive similarity
- **Type:** Synthetic/adversarial
- **Result:** 4,000-observation deceptive block. Generalist 56.70%; static router 46.35%; dynamic competence-veto router 56.23%; fallback on 96.3% of deceptive observations after shadow outcomes showed incompetence.
- **Interpretation:** Dormant expert recall requires state similarity AND current competence confirmation.
- **Promotion status:** BASELINE EVIDENCE ONLY
- **Notes:** Prevents superficial regime similarity from restoring authority.

### EXP-004 — Expert monopolization / concentration audit
- **Type:** Synthetic/adversarial
- **Result:** Corrupted router 65.77%; arbitrary routing cap 64.57%; independent safety auditor 67.39%; healthy unbiased router 67.39%; auditor intervened on 18.6%.
- **Interpretation:** Detect unjustified concentration rather than imposing crude equalization/load balancing.
- **Promotion status:** BASELINE EVIDENCE ONLY
- **Notes:** Supports independent Router Safety Auditor.

### EXP-005 — Checkpoint/resume determinism
- **Type:** Synthetic/stateful safety
- **Result:** Continuous run and process→checkpoint→stop→restore→continue produced exactly matching expert choices and final competence state in the reported test.
- **Interpretation:** Checkpoint must include learner state, support counters, calibration state, drift state, and version IDs — not only model weights.
- **Promotion status:** BASELINE EVIDENCE ONLY
- **Notes:** Real runtime persistence still unimplemented.

### EXP-006 — Malformed/NaN fail-open injections
- **Type:** Synthetic/safety
- **Result:** Five malformed/NaN router packet injections all followed fallback behavior without contaminating competence state.
- **Interpretation:** NaN/schema mismatch/expired TTL/missing context/unknown version/corrupt uncertainty should reject VECTOR contribution while sibling systems continue.
- **Promotion status:** BASELINE EVIDENCE ONLY
- **Notes:** No live consumer adapter yet.

### EXP-007 — Cross-horizon propagation classification
- **Type:** Synthetic/chronological holdout
- **Result:** 60,000-step synthetic environment. Treat-every-1m-flip: precision 6.7%, recall 100%, F1 12.6%. ≥2-horizon disagreement: precision 12.4%, recall 76.3%, F1 21.4%. Hand-built hierarchy: precision 22.5%, recall 49.3%, F1 30.9%. Learned propagation classifier: precision 68.1%, recall 66.2%, F1 67.2%, AUROC ~0.964.
- **Interpretation:** Lower-timeframe disagreement is better represented as a propagation problem than a voting problem.
- **Promotion status:** DESIGN EVIDENCE ONLY
- **Notes:** Synthetic generator intentionally contained learnable transition structure.

### EXP-008 — Cross-horizon adversarial distribution shift
- **Type:** Synthetic/adversarial
- **Result:** After increasing false reversals/noise, shortening genuine lead times, and weakening confirmation: F1 fell from ~0.689 to ~0.221; AUROC fell from ~0.959 to ~0.768.
- **Interpretation:** Propagation models can become confidently obsolete; drift must decay propagation authority.
- **Promotion status:** DESIGN EVIDENCE ONLY
- **Notes:** Motivated Propagation Drift Sentinel.

### EXP-009 — Propagation drift sentinel
- **Type:** Synthetic/drift
- **Result:** MMD-style rolling monitor: 1/15 normal windows flagged, 27/27 deliberately shifted windows flagged; normal median distance 0.0023 vs shifted 0.0210.
- **Interpretation:** Cross-horizon distribution change should trigger authority reduction and revalidation.
- **Promotion status:** DESIGN EVIDENCE ONLY
- **Notes:** Threshold was synthetic-calibrated.

### EXP-010 — Evidence-conservation duplicate attack
- **Type:** Synthetic/adversarial
- **Result:** 120,000-observation environment with 8 visible observations generated by 3 latent causes. Naive aggregation: 72.34% accuracy, log loss 0.546, Brier 0.183, AUROC 0.796. Dependency-adjusted: 72.78%, 0.544, 0.182, 0.800. Adding 12 exact copies reduced naive accuracy to 68.50% and log loss to 0.592 while dependency-adjusted accuracy stayed ~72.78%; mean probability change ~0.000056.
- **Interpretation:** Repeated representation of the same information must not manufacture conviction.
- **Promotion status:** DESIGN EVIDENCE ONLY
- **Notes:** Supports Evidence Conservation Engine.

### EXP-011 — Lineage novelty / 20-clone attack
- **Type:** Synthetic/adversarial
- **Result:** 60,000 observations; 12 visible signals from 3 latent evidence families. Ordinary voting ~71.74%. After 20 copies of strongest visible signal: ~71.34%. Lineage-conserved aggregation remained ~71.74%. Adding a genuinely new fourth ~70%-reliable family raised conserved aggregation to ~75.36%.
- **Interpretation:** Clone evidence should add near-zero novelty while genuinely independent useful evidence should be able to move belief.
- **Promotion status:** DESIGN EVIDENCE ONLY
- **Notes:** Supports Dynamic Evidence Lineage Graph and Information Novelty Score.

### EXP-012 — Hidden common-cause compression
- **Type:** Synthetic/latent-factor
- **Result:** 80,000 observations; two latent drivers. Conventional logistic learner ~67.08% accuracy, 0.6036 log loss, 0.7343 AUROC. Common-factor compression + separate signal ~66.85%, 0.6053, 0.7317.
- **Interpretation:** Cleaner latent-factor stories do not automatically improve prediction; use soft conservation that preserves idiosyncratic residual novelty.
- **Promotion status:** NEGATIVE/CONSTRAINT EVIDENCE
- **Notes:** Prevents destructive deduplication.

### EXP-013 — Dependency-graph staleness
- **Type:** Synthetic/dynamic system
- **Result:** 30,000-observation, 4-node, 3-regime system. Correct regime-specific graph one-step errors: A ~1.010, B ~1.002, C ~1.011. Keeping stale A graph: B ~1.415, C ~1.113. Using wrong B graph in C: ~1.492.
- **Interpretation:** A previously valid dependency graph can become actively harmful after structural transition.
- **Promotion status:** DESIGN EVIDENCE ONLY
- **Notes:** Motivated Dependency Graph Drift Controller.

## Appendix B — Component Register

- **Adaptive Trend Intelligence Loop** — Top-level advisory intelligence fabric. Status: Designed/iterated. No execution authority; fail-open.

- **Trend Genome** — Structured trend state representation. Status: Designed. Direction, strength, persistence, maturity, acceleration, structure, participation, uncertainty, etc.

- **Mixture-of-Experts Fabric** — Population of complementary trend experts. Status: Designed. Shared primitives + specialized experts.

- **Expert Competence Tensor** — Context-conditioned expert reliability map. Status: Synthetic support. Includes uncertainty/support/calibration/drift/OOD/allowed_authority.

- **Router Safety Auditor** — Independent control plane for router choices. Status: Synthetic support. Should not share all features/objectives with router.

- **Trend Failure Atlas** — Memory of trend failure modes. Status: Designed. False breakouts, failed continuation, exhaustion, shocks, sweeps, etc.

- **Cross-Horizon Temporal Propagation Graph (CHTPG)** — Probabilistic horizon-to-horizon transition model. Status: Synthetic support. Temporal firewall prevents LTF overwrite of HTF state.

- **Propagation Drift Sentinel** — Detects obsolete propagation relationships. Status: Synthetic support. MMD-style synthetic validation.

- **Evidence Conservation Engine** — Dependency-adjusted confidence accounting. Status: Synthetic support. Redundant evidence receives near-zero marginal credit.

- **Dynamic Evidence Lineage Graph (DELG)** — Tracks evidence ancestry/provenance. Status: Synthetic support. Clone/derivative/correlated-novel/independent-novel.

- **Information Novelty Score** — Marginal information contribution concept. Status: Synthetic support. Condition on already-admitted evidence.

- **Latent Common-Cause Resolver (LCCR)** — Probabilistic hidden-driver grouping. Status: Synthetic constraint evidence. Soft conservation; preserve idiosyncratic residual.

- **Causal Confidence Firewall** — Separates predictive dependence from causal identification. Status: Designed. Allows causal_status=UNIDENTIFIED.

- **Dependency Graph Drift Controller (DGDC)** — Versions/quarantines/recalls dependency graphs. Status: Synthetic support. ACTIVE→WATCH→QUARANTINED→RECALLED/CHALLENGER→...

- **TrendIntelligencePacket** — Versioned external interface. Status: Designed. Auditable confidence, provenance, graph/version/TTL/uncertainty.

- **Champion/Challenger Promotion Gate** — Prevents silent adaptive overwrite. Status: Designed. Domain-bounded promotion only after multi-axis validation.

- **Checkpoint/Resume Contract** — State persistence requirements. Status: Synthetic support. Must include more than model weights.

## Appendix C — Promotion Test Matrix

- Chronological / walk-forward evaluation
- Leakage and prefix-invariance checks
- Calibration and reliability curves
- Contextual competence and minimum support
- Regime and tail robustness
- OOD detection and abstention
- Router entropy/concentration and independent-auditor checks
- Shadow stability and rollback readiness
- Redundancy injection / signal cloning / source removal
- Transformation and delayed-duplicate attacks
- Propagation-loop and common-shock attacks
- Hidden-common-cause / partial-common-cause / residual-novelty tests
- Dependency shift / edge reversal / leader-follower reversal
- Asynchronous / scale-specific / tail-only graph shifts
- Graph split / merge / false-recurrence / stale-graph replay
- Checkpoint/resume determinism
- Malformed/NaN/schema/TTL/version fail-open behavior
- Real Icarus replay with costs/latency before any production-adjacent authority

## Appendix D — Handoff Integrity Note

This package intentionally preserves negative results and blocked/unimplemented work so a receiving agent does not mistake design maturity for deployment maturity.
