# PROMETHEUS — Autonomous Systems Evolution Loop Design

**Date:** 2026-09-24  
**Status:** design approved in chat; implementation not yet authorized under the Superpowers architectural workflow  
**System role:** research-only meta-layer / sibling system  
**Primary stack:** Icarus ecosystem with NEXUS, AION, ARGUS, ATHENA, DAEDALUS, PARALLAX, ORACLE and Icarus execution  

## 1. Purpose

PROMETHEUS exists to improve the rest of the system without becoming another competing prediction or execution engine.

Its job is to:

1. observe exact, causally valid system evidence;
2. identify failures, disagreements, redundancy and unexplained behavior;
3. formulate falsifiable research hypotheses;
4. attack those hypotheses with adversarial tests;
5. replay proposed changes against exact historical states using only information available at each decision instant;
6. compare candidates to the current baseline across robustness, calibration, fragility, cost and regime stability;
7. emit research candidates only;
8. preserve both successful and failed experiments as durable knowledge; and
9. periodically evaluate whether system components should be simplified, combined, retired or isolated.

PROMETHEUS must increase the rate at which the Icarus stack learns from evidence while decreasing repeated research, silent regressions, feature duplication and architecture drift.

## 2. Non-goals and hard authority boundaries

PROMETHEUS is not an execution engine, broker adapter, production strategy, supervisory risk engine, market-data authority, historical-memory replacement or statistical-promotion authority.

It MUST NOT:

- set `production_authorized=true`;
- place, route, size, cancel or modify production orders;
- construct or override ATHENA supervisory `WorldState` or abstention decisions;
- claim OHLCV/candle-derived information is trade, depth, L2 or authenticated order-flow truth;
- create historical availability or receipt timestamps that were not observed or attested;
- consume DAEDALUS protected holdouts through an unrestricted research interface;
- silently mutate sibling-system production parameters or source trees;
- write directly into a sibling repository during a research run;
- promote a candidate because PnL, hit rate or one headline metric improved;
- reuse future information, centered windows or full-sample normalization in historical evaluation;
- treat disagreement as an error that must be forced into consensus.

Authority remains:

- **NEXUS:** market-data identity, causal timing, replay, source health, representations, factor/topology/OOD ingredients and same-instant routing.
- **AION:** durable evidence memory, historical atlas and long-lived event/derivation history.
- **ARGUS:** authenticated microstructure, trades/depth semantics and execution-physics evidence.
- **ATHENA:** supervisory world state, uncertainty, confidence, routing, advisory risk and abstention.
- **DAEDALUS:** scientific validation, protected evidence and candidate promotion.
- **PARALLAX:** historical/representation analogy and similarity intelligence where available.
- **ORACLE:** anomaly-to-hypothesis intelligence where available.
- **Icarus:** production decisions, broker state and orders.

PROMETHEUS is authoritative only for its own research orchestration state, experiment lineage, cross-system comparison artifacts and research memory index.

## 3. Placement in the architecture

PROMETHEUS is a separate sibling/meta-layer.

```text
                           +----------------+
                           |     AION       |
                           | evidence memory|
                           +--------+-------+
                                    ^
                                    | durable research evidence
                                    |
+---------+     +---------+    +----+-----+    +----------+
| NEXUS   |---->|         |<---| PARALLAX |    |  ORACLE  |
| causal  |     |         |    +----------+    +-----+----+
| fabric  |---->|         |                         |
+----+----+     |         |<------------------------+
     |          |PROMETHEUS|
+----v----+     |         |<---- ARGUS evidence
| ATHENA  |---->|         |
+---------+     |         |----> DAEDALUS research candidate
                |         |              |
                +----+----+              v
                     |               validation/
                     |               promotion
                     v                   |
                research memory          v
                                     +---+----+
                                     | Icarus |
                                     | prod   |
                                     +--------+
```

PROMETHEUS consumes read-only snapshots/artifacts. It emits research artifacts. Production change remains an explicitly separate process outside the loop.

## 4. Core loop

The canonical loop state machine is:

```text
OBSERVE
  -> DETECT
  -> EXPLAIN
  -> HYPOTHESIZE
  -> ATTACK
  -> REPLAY
  -> MEASURE
  -> DECIDE_RESEARCH_STATUS
  -> REMEMBER
  -> REPEAT
```

No stage is allowed to skip directly to production mutation.

Every loop iteration has an immutable `loop_run_id` and binds:

- source evidence identifiers;
- decision instant(s);
- causal frontier / availability basis;
- sibling-system versions;
- code/config hashes;
- experiment specification hash;
- model/feature versions when relevant;
- replay data/corpus identity;
- baseline identifier;
- candidate identifier;
- adversarial-test results;
- rejection or advancement reasons; and
- parent/child experiment lineage.

## 5. Three nested loops

### 5.1 SENTINEL — fast observation and discrepancy loop

SENTINEL operates on each eligible exact market/replay instant or on small batches of instants.

Responsibilities:

- verify required evidence exists for the same decision instant;
- detect contract/schema drift before interpretation;
- detect source-health degradation and unknown availability;
- detect sibling output disagreement;
- detect confidence collapse, abstention, regime transition and OOD conditions;
- record feature/system coverage and missingness;
- identify impossible-value and causality violations;
- open `FailureCase`, `DisagreementCase` or `OpportunityCase` artifacts.

SENTINEL must be cheap, deterministic where inputs are deterministic, and incapable of mutating production behavior.

### 5.2 FORGE — research and adversarial experiment loop

FORGE receives prioritized cases from SENTINEL and turns them into falsifiable experiments.

Responsibilities:

- root-cause decomposition;
- hypothesis generation;
- baseline selection;
- candidate transformation/feature/policy generation;
- leakage and causal-frontier audit;
- ablation and counterfactual design;
- adversarial robustness tests;
- exact or causally equivalent replay;
- regime-stratified evaluation;
- redundancy and information-value analysis;
- candidate-vs-baseline tournament;
- emission of `CandidateImprovement` or `RejectedHypothesis`.

FORGE does not promote. It may mark a candidate `READY_FOR_DAEDALUS_REVIEW` only when all PROMETHEUS engineering/research preconditions pass.

### 5.3 ASCENSION — slow architecture-evolution loop

ASCENSION operates over accumulated experiment history rather than individual market instants.

Responsibilities:

- identify duplicated features and nearly equivalent subsystems;
- map dependency concentration and single points of failure;
- quantify marginal information contribution;
- identify dead or consistently non-contributing components;
- find recurrent failure classes across systems;
- find research methods that repeatedly fail or repeatedly produce value;
- propose system-boundary simplification, decomposition or retirement;
- propose where compute/token/research budget should be concentrated;
- open architectural `EvolutionProposal` artifacts for human/agent review.

ASCENSION may never auto-delete or auto-merge sibling systems.

## 6. Typed research artifacts

PROMETHEUS uses typed, immutable research artifacts rather than free-form logs as the canonical machine state.

### 6.1 `ObservationEnvelope`

Minimum fields:

- `observation_id`
- `decision_ns`
- `nexus_frame_hash`
- `source_health_hash`
- `sibling_versions`
- `sibling_payload_hashes`
- `availability_policy_id`
- `corpus_or_stream_manifest_hash`
- `received_at_ns`
- `lineage`

Purpose: prove that compared sibling outputs refer to compatible evidence and time.

### 6.2 `DisagreementCase`

Fields include:

- participants;
- exact outputs being compared;
- disagreement dimensions;
- confidence/abstention state;
- OOD/regime/source-health context;
- severity;
- novelty score;
- recurrence count;
- candidate root-cause categories;
- linked prior cases.

Disagreement is not automatically failure. It is a research trigger.

### 6.3 `FailureCase`

Captures:

- expected contract/invariant;
- observed behavior;
- first failing instant;
- reproducer/replay locator;
- impact class;
- whether the failure is data, causal, statistical, execution-model, integration or architecture related.

### 6.4 `OpportunityCase`

Captures potential improvements such as:

- unused but available evidence;
- duplicated calculations;
- high-cost/low-value components;
- stable cross-system conditional relationships;
- repeated abstention with identifiable missing context;
- recurrent failure preceded by detectable state.

### 6.5 `ResearchHypothesis`

Must include:

- precise falsifiable claim;
- target subsystem/interface;
- causal/data prerequisites;
- baseline;
- candidate change;
- expected measurable effect;
- primary metric family;
- guardrail metrics;
- invalidation criteria;
- prohibited evidence sources;
- protected-holdout policy;
- parent case ids.

A hypothesis without explicit invalidation criteria is invalid.

### 6.6 `ExperimentSpec`

Defines exactly how a hypothesis is tested:

- data/replay manifest;
- time split policy;
- embargo/purge requirements;
- regime partitions;
- transaction/execution-cost model if relevant;
- random seed policy;
- ablations;
- perturbations;
- missingness tests;
- latency tests;
- normalization/fitting scope;
- baseline/candidate hashes;
- expected outputs;
- acceptance gate configuration.

### 6.7 `ReplayComparison`

Binds baseline and candidate to identical or explicitly compatible replay evidence and stores per-regime, per-case and aggregate differences.

### 6.8 `CandidateImprovement`

Statuses:

- `RESEARCH_ONLY`
- `PROMETHEUS_ENGINEERING_PASS`
- `READY_FOR_DAEDALUS_REVIEW`
- `DAEDALUS_ACCEPTED`
- `DAEDALUS_REJECTED`
- `SUPERSEDED`

PROMETHEUS itself can set only the first three. DAEDALUS-sourced evidence is required for the last three transitions.

### 6.9 `RejectedHypothesis`

Stores rejection as first-class negative knowledge:

- reason codes;
- failing tests;
- affected regimes;
- sensitivity results;
- closest related prior hypothesis;
- conditions under which retesting would become justified.

### 6.10 `ResearchLesson`

A compact reusable rule derived from multiple experiments. It must link to supporting experiment ids and may not be treated as universal outside its evidence scope.

### 6.11 `EvolutionProposal`

ASCENSION output proposing architectural change. It requires explicit human/agent design review before implementation.

## 7. Cross-system interfaces

PROMETHEUS adapters are read-only by default and versioned independently from sibling internals.

### 7.1 NEXUS adapter

Consumes:

- `ReplayInstant` / same-instant bundle identity;
- `frame_hash`;
- source-health plane/hash;
- factor/topology/OOD/quality ingredients;
- derivation records and factor genealogy;
- corpus/representation registry/run-manifest identity;
- causal replay/checkpoint locators.

Rules:

- PROMETHEUS never synthesizes a common clock that NEXUS did not provide;
- unknown availability remains unknown/fail-closed;
- NEXUS factor/topology/OOD values are ingredients, not supervisory conclusions;
- NEXUS data identity remains authoritative.

### 7.2 AION adapter

Consumes/retrieves:

- historical observations;
- prior similar research cases;
- experiment lineage;
- prior rejected hypotheses;
- exact evidence needed to reconstruct decisions.

Writes only PROMETHEUS research observations through an explicit AION-supported evidence contract. PROMETHEUS must not create a parallel durable market-history store that competes with AION.

### 7.3 ARGUS adapter

Consumes:

- authenticated trade/depth/order-flow evidence where ARGUS has it;
- execution-physics diagnostics;
- explicit evidence tier.

CANDLE_PROXY evidence remains proxy evidence. PROMETHEUS must preserve ARGUS evidence-tier semantics.

### 7.4 ATHENA adapter

Consumes:

- advisory world-state outputs;
- uncertainty/confidence;
- abstention/rejection reasons;
- route/expert decisions;
- supervisory diagnostics exposed by contract.

PROMETHEUS may study ATHENA behavior but cannot override it in production.

### 7.5 DAEDALUS adapter

Emits only fully lineage-bound research candidates and receives validation/promotion results.

DAEDALUS remains authoritative for protected holdouts, false-discovery control and promotion. PROMETHEUS must not infer `DAEDALUS_ACCEPTED` merely from locally positive results.

### 7.6 PARALLAX adapter

Consumes historical analogues, similarity neighborhoods and representation-space evidence where available. PROMETHEUS records the analogue method/version so changing embedding/similarity logic cannot silently rewrite prior experiments.

### 7.7 ORACLE adapter

Consumes anomaly/hypothesis artifacts where available and can feed those into FORGE as candidate cases. PROMETHEUS does not treat ORACLE hypotheses as validated claims.

### 7.8 Icarus adapter

Read-only for outcome attribution and production-decision lineage where exposed. No order mutation path exists in PROMETHEUS.

## 8. Disagreement engine

The first operational research target is cross-system disagreement.

A disagreement event requires:

1. a common decision instant or an explicitly reconciled causal window;
2. evidence that each participant's output is valid for that instant;
3. typed comparison dimensions rather than generic `agree/disagree` labels.

Initial dimensions:

- direction/state classification;
- confidence/calibration bucket;
- regime classification;
- abstain/act;
- data-quality interpretation;
- risk state;
- anomaly/OOD classification;
- analogue family;
- execution feasibility when applicable.

PROMETHEUS clusters recurrent disagreement signatures and asks whether one of these explanations fits:

- different evidence sets;
- different clocks/availability;
- different representation assumptions;
- data quality/source-health issue;
- regime boundary;
- model blind spot;
- intentional specialization;
- true irreducible ambiguity.

The system must be capable of concluding that disagreement is healthy specialization and should not be removed.

## 9. Hypothesis factory

Hypothesis generation is constrained, not free-form optimization.

Valid hypothesis families include:

- feature addition/removal;
- context gating;
- confidence calibration;
- abstention boundary refinement;
- representation weighting;
- source-quality-aware behavior;
- architecture simplification;
- caching/throughput improvement that preserves output identity;
- cross-system evidence handoff improvement;
- test/verification improvement;
- research-priority adjustment.

Each generated hypothesis must pass a pre-experiment screen:

- non-duplicate against research memory;
- authority-boundary safe;
- causally testable;
- data availability sufficient;
- explicit baseline exists;
- falsifiable;
- cost/complexity justified by plausible value.

## 10. Adversarial laboratory

FORGE attempts to destroy a candidate before DAEDALUS ever sees it.

Default adversarial families:

1. **Temporal leakage attacks** — prefix invariance, shifted labels, future-window contamination probes.
2. **Parameter perturbation** — neighboring values and randomized valid configurations.
3. **Regime decomposition** — trend/range, volatility, source-health, liquidity and OOD states where evidence supports those labels.
4. **Ablation** — remove one feature/source/system/group at a time.
5. **Permutation/null tests** — where statistically appropriate and without violating time dependence.
6. **Latency injection** — delay availability/receipt or downstream output within evidence-backed ranges.
7. **Missingness/corruption** — drop eligible inputs, degrade source quality and test fail-closed behavior.
8. **Cost sensitivity** — commissions/slippage/impact/queue models when the hypothesis affects tradable outcomes.
9. **Representation perturbation** — compare eligible representation families without silently treating derived/event bars as fixed-time bars.
10. **Boundary tests** — regime transitions, session boundaries, contract rolls and feed reconnects when data supports them.
11. **Complexity challenge** — compare against simpler baselines and reject improvements that do not justify added complexity.
12. **Reproducibility challenge** — rerun from hashes/manifests and require stable outputs within explicitly allowed stochastic tolerance.

Passing these tests does not authorize production; it only qualifies a candidate for DAEDALUS review.

## 11. Tournament and evaluation model

PROMETHEUS must not optimize one scalar score as the truth.

Candidate comparisons produce a scorecard with distinct dimensions:

- causal correctness;
- reproducibility;
- data/source robustness;
- calibration;
- coverage;
- abstention quality;
- regime stability;
- fragility/sensitivity;
- latency/throughput cost;
- memory/compute cost;
- execution realism where applicable;
- incremental information value;
- redundancy;
- complexity burden;
- failure severity;
- uncertainty.

A candidate can advance only if all hard safety/correctness gates pass and no guardrail metric crosses its configured rejection bound.

PROMETHEUS may maintain a Pareto frontier of candidates. It should not force a total ranking when candidates trade off different desirable properties.

## 12. Information-value accounting

PROMETHEUS tracks marginal contribution rather than raw standalone importance.

For each feature, subsystem output or evidence channel it may estimate:

- unique predictive/descriptive information conditional on the rest;
- redundancy with neighboring signals;
- outcome displacement when ablated;
- confidence/calibration displacement;
- contribution by regime;
- compute/latency/token cost per unit of useful information;
- instability under perturbation.

No single method is authoritative. Information-value conclusions must carry the estimator/method/version and uncertainty.

ASCENSION uses accumulated evidence to propose consolidation or retirement only when repeated experiments show persistent redundancy or negative value.

## 13. Causal ancestry graph

Every research artifact should be traversable back to original evidence.

Example:

```text
CandidateImprovement
  -> ReplayComparison
  -> ExperimentSpec
  -> ResearchHypothesis
  -> DisagreementCase
  -> ObservationEnvelope
  -> sibling payload hashes
  -> NEXUS frame / ARGUS evidence / ATHENA advisory / AION history
  -> original source observations and availability evidence
```

The ancestry graph is append-only. Revisions create new nodes rather than mutating the meaning of old evidence.

## 14. Research memory

PROMETHEUS maintains a local research index optimized for orchestration, while durable evidence is written to AION when that contract is available.

Required memory functions:

- exact experiment lookup by hash/id;
- semantic/structural similarity search over prior hypotheses;
- negative-result lookup before generating new experiments;
- recurrence tracking for failure/disagreement signatures;
- experiment dependency graph;
- stale-evidence detection when sibling versions or contracts change;
- lineage export suitable for AION persistence.

A failed experiment is not garbage. It is retained unless retention policy explicitly expires the raw bulk artifact while preserving its immutable summary/hash/lineage.

## 15. Prioritization and budget control

PROMETHEUS should not run every possible experiment.

Each case receives a research priority derived from separate components such as:

- severity/impact;
- recurrence;
- novelty;
- uncertainty reduction potential;
- cross-system scope;
- evidence completeness;
- experiment cost;
- likelihood of resolving an existing blocker;
- whether the same question has already been answered.

Budget classes:

- `FAST`: deterministic checks, contract validation, lightweight replay.
- `STANDARD`: targeted ablations, regime comparisons, calibration checks.
- `HEAVY`: large replays, multiple candidate families, expensive representation analyses.
- `ARCHITECTURAL`: ASCENSION investigations requiring explicit review before implementation.

A heavy experiment must declare why a cheaper probe cannot answer the question.

## 16. Failure handling

PROMETHEUS fails closed on research integrity.

Examples:

- missing required evidence -> `INSUFFICIENT_EVIDENCE`, not an inferred value;
- incompatible decision instants -> no comparison;
- unknown availability -> no causal replay claim;
- contract drift -> quarantine affected adapter and open a `FailureCase`;
- reproducibility mismatch -> candidate cannot advance;
- protected-holdout boundary violation -> experiment invalidated and quarantined;
- sibling unavailable -> case remains pending; no fabricated substitute;
- partial experiment failure -> retain partial evidence but status remains failed/incomplete.

No exception handler may silently convert a research-integrity failure into a passing/default result.

## 17. Security and mutation model

Default permissions:

- sibling repositories: read-only during experiments;
- production services: read-only telemetry where explicitly exposed;
- research workspace: read/write;
- DAEDALUS submission boundary: write research candidate only;
- AION research-evidence boundary: append via supported contract only;
- broker/execution APIs: no credentials and no client implementation.

Candidate code is created in isolated research branches/worktrees or generated patch artifacts. PROMETHEUS never applies a candidate directly to a production branch.

## 18. Observability

Each loop run emits structured events:

- `loop_started`
- `observation_validated`
- `case_opened`
- `hypothesis_created`
- `experiment_started`
- `adversarial_test_result`
- `replay_completed`
- `candidate_rejected`
- `candidate_ready_for_daedalus`
- `research_lesson_created`
- `evolution_proposal_created`
- `loop_completed`

Metrics include:

- cases opened/closed;
- duplicate hypotheses prevented;
- negative-result reuse rate;
- experiments by budget class;
- adversarial rejection rate;
- reproducibility failures;
- contract-drift events;
- median evidence-to-hypothesis latency;
- median hypothesis-to-decision latency;
- compute/token spend by research family;
- candidate advancement rate;
- stale research artifacts after sibling changes.

These metrics measure the research process, not trading profitability.

## 19. Initial implementation boundary

The first implementation must be intentionally narrower than the full vision.

### Initial vertical slice

1. ingest a NEXUS same-instant sibling bundle or a deterministic fixture representing it;
2. normalize sibling observations into `ObservationEnvelope`;
3. run same-instant/contract/availability checks;
4. detect typed disagreement among available sibling outputs;
5. open immutable `DisagreementCase` artifacts;
6. deduplicate cases against local research memory;
7. create a constrained `ResearchHypothesis` from an approved hypothesis family;
8. compile an `ExperimentSpec`;
9. run a deterministic replay comparison against a baseline fixture or NEXUS replay adapter;
10. run a first adversarial suite: leakage guard, ablation, perturbation, missingness and reproducibility;
11. emit either `RejectedHypothesis` or `CandidateImprovement(status=RESEARCH_ONLY|PROMETHEUS_ENGINEERING_PASS)`;
12. persist the complete lineage locally and expose an AION/DAEDALUS adapter interface without requiring those services for unit tests.

### Explicitly deferred

- autonomous code generation across sibling repos;
- direct GitHub branch/PR mutation;
- live broker or execution integration;
- automatic DAEDALUS promotion;
- full information-theory estimator zoo;
- distributed experiment scheduler;
- generalized agent marketplace/orchestrator;
- self-modifying PROMETHEUS production code;
- automatic subsystem deletion or merge.

These remain future evolution steps after the research loop itself demonstrates reliability.

## 20. Repository/module design target

PROMETHEUS should remain separate from NEXUS.

Proposed package boundaries:

```text
src/prometheus_loop/
  contracts.py          # immutable typed research artifacts
  ids.py                # stable content-derived ids/hashes
  clock.py              # decision-instant compatibility checks only
  adapters/
    nexus.py
    aion.py
    argus.py
    athena.py
    daedalus.py
    parallAX.py
    oracle.py
    icarus.py
  sentinel/
    validate.py
    disagreement.py
    failure.py
    opportunity.py
  forge/
    hypothesis.py
    experiment.py
    adversarial.py
    replay.py
    compare.py
    information_value.py
  ascension/
    redundancy.py
    dependency_graph.py
    evolution.py
  memory/
    store.py
    index.py
    lineage.py
  policy/
    authority.py
    budgets.py
    gates.py
  orchestration/
    loop.py
    queue.py
    events.py
  cli.py
```

The exact module split may be simplified during implementation, but authority, evidence and research-state boundaries must remain explicit.

## 21. Testing strategy

Implementation must be test-driven.

### Contract tests

- immutable artifact hashing;
- stable serialization;
- schema/version rejection;
- production-authority fields impossible or fixed false where appropriate.

### Causality tests

- mismatch decision instants rejected;
- unknown availability fails closed;
- prefix-invariance/leakage fixtures rejected;
- no future event can alter an earlier completed experiment result.

### Adapter tests

- sibling payload versions are explicit;
- evidence tiers preserved;
- missing sibling fields fail or degrade explicitly;
- NEXUS/DAEDALUS/AION boundary invariants retained.

### Loop tests

- deterministic case ids for identical evidence;
- duplicate case/hypothesis suppression;
- negative research memory reuse;
- valid state-machine transitions only;
- partial failures cannot advance candidate status.

### Adversarial tests

- a deliberately leaky candidate is rejected;
- a brittle parameter candidate is rejected;
- a redundant feature is identified as low incremental value in a controlled fixture;
- a candidate that wins aggregate but fails a protected guardrail is rejected.

### Replay tests

- baseline and candidate consume the same eligible evidence;
- repeated replay produces identical hashes for deterministic candidates;
- stochastic candidates require explicit seed/tolerance contracts.

### Architecture tests

- no broker/execution dependency exists;
- no write dependency into sibling source trees exists;
- candidate status cannot transition to production-authorized inside PROMETHEUS;
- DAEDALUS acceptance cannot be fabricated locally.

## 22. Acceptance criteria for v0.1

PROMETHEUS v0.1 is successful when all of the following are true:

1. a deterministic same-instant observation can be ingested and hashed;
2. at least two sibling outputs can be compared through typed dimensions;
3. disagreement/failure cases are immutable and deduplicated;
4. a falsifiable hypothesis and experiment specification can be generated without unrestricted free-form production mutation;
5. adversarial tests can reject known-bad candidates;
6. replay comparisons bind baseline/candidate to identical eligible evidence;
7. negative research results are searchable and prevent duplicate experiments;
8. candidate outputs remain research-only and cannot authorize production;
9. DAEDALUS and AION boundaries are represented by explicit adapters/contracts;
10. all tests pass from a clean checkout with deterministic fixture evidence;
11. repository documentation explains authority boundaries and the current scope;
12. no existing NEXUS ownership or sibling authority is duplicated.

## 23. First loop objective after v0.1 exists

The first real research loop should target a cross-system disagreement class, not raw price prediction.

Preferred target:

**“When NEXUS source/factor/OOD state, ATHENA supervisory output and ARGUS evidence disagree around the same decision instant, can PROMETHEUS classify whether the disagreement is caused by evidence mismatch, source health, regime transition, specialization or model fragility, and can it produce a falsifiable candidate improvement without violating sibling authority?”**

Success is measured by reproducible explanation quality, experiment integrity, negative-result reuse and safe candidate generation—not by an unsupervised claim of trading edge.

## 24. Design decisions frozen by this spec

- PROMETHEUS is a separate sibling/meta-layer.
- The loop is research-only and fail-closed.
- The initial implementation is a closed research loop, not autonomous production evolution.
- SENTINEL, FORGE and ASCENSION are distinct nested loops.
- cross-system disagreement is the first research target.
- artifacts are immutable, lineage-bound and content-addressed where feasible.
- negative results are first-class memory.
- NEXUS remains authoritative for causal market fabric/replay.
- DAEDALUS remains authoritative for statistical promotion.
- AION remains authoritative for durable evidence memory.
- ARGUS/ATHENA/Icarus authority boundaries are preserved.
- no broker dependency or production authorization path exists in PROMETHEUS v0.1.

## 25. Assumptions requiring validation during implementation planning

These are explicit assumptions, not invented facts:

- exact current contracts for PARALLAX, ORACLE and some Icarus outcome-attribution interfaces may not be available in the recovered NEXUS package;
- PROMETHEUS adapters for unavailable siblings must therefore begin as interfaces/fixtures and be bound only after their authoritative contracts are inspected;
- AION/ARGUS/ATHENA/DAEDALUS integration tests should use real sibling packages when accessible, otherwise contract fixtures must be clearly labeled non-authoritative;
- the current NEXUS v0.3 handoff is the engineering baseline used to define NEXUS-facing invariants for this design.

No implementation may guess missing sibling fields.

## 26. Per-run plugin orchestration contract

This section incorporates the owner's 2026-09-24 requirement that each new PROMETHEUS loop run actively use every installed plugin that is materially beneficial to that run, with Deep Research explicitly included when available.

### 26.1 Top-level run requirement

Every top-level PROMETHEUS run MUST begin with a plugin inventory and selection pass before research conclusions are produced. The inventory captures the plugins/tools visible to the orchestrator at run start. The selector MUST:

1. consider every visible plugin against the run objective;
2. invoke every plugin judged materially beneficial and policy-eligible;
3. invoke the Deep Research plugin at least once for every top-level research run when it is available and connected;
4. never invoke an irrelevant plugin solely to increase plugin count;
5. record every considered plugin with one of `SELECTED`, `SKIPPED_NOT_BENEFICIAL`, `SKIPPED_REDUNDANT`, `SKIPPED_POLICY`, `UNAVAILABLE`, `FAILED`, or `COMPLETED`;
6. preserve the plugin/tool version or stable identity when exposed by the host;
7. hash normalized plugin outputs or record an immutable external result reference when raw output is not locally materializable; and
8. bind every plugin-use record to the same `loop_run_id` as the research artifacts it informed.

The phrase "every beneficial plugin" means positive expected marginal information, validation, execution-quality, provenance, or orchestration value for the current run after accounting for duplication, latency, cost, permissions, and data sensitivity. It does not mean blindly calling unrelated plugins.

### 26.2 Deep Research rule

`DEEP_RESEARCH_REQUIRED` is a top-level run invariant. If the Deep Research plugin is visible and connected, a new PROMETHEUS research run cannot reach `RESEARCH_COMPLETE` unless at least one Deep Research invocation is recorded. If it is unavailable, disconnected, rate-limited, or fails, the run records the exact failure state and may continue only in `DEGRADED_RESEARCH` unless the run objective itself requires Deep Research, in which case it fails closed.

SENTINEL's internal low-latency subchecks do not individually invoke Deep Research; the requirement applies to the containing top-level PROMETHEUS run. This prevents a high-frequency safety monitor from becoming dependent on a slow external research service while still satisfying the owner requirement for each new loop run.

### 26.3 Plugin selection evidence

The minimum immutable plugin-selection record contains:

- `loop_run_id`;
- `plugin_id` and display name;
- capability tags;
- selection status;
- explicit reason;
- policy decision;
- invocation start/end timestamps when invoked;
- input fingerprint;
- output fingerprint or external result reference;
- failure class and retry/quarantine state where applicable;
- whether the result contributed to a downstream artifact;
- downstream artifact ids when it did.

Plugin outputs are evidence, not authority. They may create observations, supporting sources, code-review findings, or research candidates, but they cannot set `production_authorized=true`, mutate sibling production state, or bypass DAEDALUS validation.

### 26.4 Security and failure posture

Plugin access is deny-by-default and least-privilege. A plugin receives only the minimum data and capabilities required for the run. Where the host supports scoped/ephemeral authorization, PROMETHEUS prefers it. Each plugin must be mediated through a typed adapter boundary when an executable adapter exists. Invalid schemas, permission failures, timeouts, or suspicious output are isolated to that plugin record and cannot silently advance research status.

A plugin failure does not erase its evidence. Failed and rejected plugin paths are retained as negative research memory so future runs can avoid repeated cost or recognize recurring reliability problems.

### 26.5 Plugin-aware loop state

The top-level state machine therefore becomes:

```text
INVENTORY_PLUGINS
  -> SELECT_BENEFICIAL_PLUGINS
  -> INVOKE_REQUIRED_RESEARCH_PLUGINS
  -> OBSERVE
  -> DETECT
  -> EXPLAIN
  -> HYPOTHESIZE
  -> ATTACK
  -> REPLAY
  -> MEASURE
  -> DECIDE_RESEARCH_STATUS
  -> REMEMBER
  -> FINALIZE_PLUGIN_AUDIT
  -> REPEAT
```

A run cannot finalize without a complete plugin audit record covering both selected and skipped candidates.

### 26.6 Staleness condition

This section must be reviewed when the host plugin model, plugin permission model, Deep Research invocation contract, or available connector/tool identity semantics change.
