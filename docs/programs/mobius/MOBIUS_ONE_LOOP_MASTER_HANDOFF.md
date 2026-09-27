# MÖBIUS ONE LOOP
## Proof-Carrying Project Digital Twin Evolution Engine
### Master Architecture, Implementation Blueprint, and Next-Model Handoff

**Prepared:** 2026-09-24  
**Purpose:** Give a stronger follow-on model enough architectural context, invariants, data structures, execution rules, acceptance criteria, and implementation sequencing to build one high-leverage recursive system rather than three disconnected tools.  
**Target ecosystem:** Icarus intelligence stack and its sibling systems, especially NEXUS, AION, ARGUS, ATHENA, and DAEDALUS.  
**Important:** This document is a design/handoff. It does not claim the live repository still matches the 2026-09-23 checkpoints cited below. The receiving model must re-verify any live repo state before modification.

---

# 0. EXECUTIVE DECISION

Three previously considered systems were useful but individually incomplete:

1. **Repo-independent development capsule** — excellent for portable work, weak at deciding what should be built and proving system-wide effects.
2. **Validation/research loop** — excellent for experimentation and falsification, weak at preserving a continuously accurate structural model of the entire project and weak at merge/reconciliation.
3. **Live-repo reconciliation layer** — essential once repository access exists, but mostly dormant without a repo and not itself an intelligence system.

The higher-value build is to **collapse all three into one recursive project-evolution loop**.

That system is **MÖBIUS**.

MÖBIUS maintains a continuously updated, provenance-aware, bitemporal **digital twin of the project**. It uses the twin to find the highest-leverage unresolved problem, generates or imports a candidate change, attacks that change with tests and counterfactuals, packages successful work as a **proof-carrying capability capsule**, reconciles that capsule with the real repository when available, observes the result, and updates the digital twin so the next iteration begins from a better model of reality.

The loop is:

`OBSERVE -> COMPILE TWIN -> FIND LEVERAGE -> PROPOSE CHANGE -> BUILD SHADOW -> ATTACK -> PROVE -> PACKAGE -> RECONCILE -> OBSERVE OUTCOME -> DISTILL -> UPDATE TWIN -> REPEAT`

This is **one loop**, not a family of independent loops.

The key design insight is that MÖBIUS treats project knowledge with the same rigor NEXUS applies to market data:

- raw evidence is preserved;
- claims are not silently promoted to truth;
- discovery time is distinct from event/validity time;
- contradictions remain visible;
- derived state carries lineage;
- deterministic replay is possible;
- unknowns remain unknown rather than being guessed away.

The project itself becomes a causal, replayable information system.

---

# 1. WHY THIS HAS GREATER POTENTIAL THAN THE THREE ORIGINAL BUILDS

## 1.1 The capsule alone is passive

A portable development capsule is useful only after somebody already knows what to build. It solves transportation, not intelligence.

MÖBIUS keeps the capsule concept but makes it the **output format of a reasoning-and-proof pipeline**. Every accepted change becomes a portable capsule automatically.

## 1.2 Validation alone can optimize the wrong thing

A sophisticated validation loop can spend enormous compute disproving low-value ideas. Validation quality is not enough if prioritization is weak.

MÖBIUS chooses experiments using system-wide dependency impact, unresolved uncertainty, failure recurrence, evidence weakness, cost, and regression risk.

## 1.3 Reconciliation alone starts too late

A reconciliation layer is valuable only when the live repo is accessible. It does not preserve progress while access is absent.

MÖBIUS continuously builds against a **shadow project twin** and later reconciles the twin against Git/GitHub. Repo access increases fidelity; it is not required for the architecture to function.

## 1.4 MÖBIUS creates compounding returns

Each iteration can produce several durable assets simultaneously:

- a tested implementation or research result;
- new regression tests;
- a clarified contract;
- a corrected dependency edge;
- a negative-knowledge record;
- a new benchmark;
- an updated project-state model;
- a smaller context pack for the next model;
- a merge/reconciliation plan;
- improved prioritization statistics.

Therefore the output of one iteration improves the quality and efficiency of subsequent iterations.

---

# 2. PROJECT CONTEXT THAT THE RECEIVING MODEL MUST PRESERVE

These facts are taken from the prior NEXUS handoff artifacts and are **historical anchors**, not permission to assume the current live repo still matches them.

## 2.1 NEXUS mission

NEXUS is the causal market-data substrate beneath the broader Icarus intelligence stack.

Its design principle is:

> preserve first, infer second, adapt third, predict nowhere by default.

Its canonical conceptual pipeline is:

`raw sources -> forensic manifest -> reviewed identity/clock policy -> causal native event fabric -> integrity/source-health gate -> representation-family consensus -> symbol plane -> adaptive factors/topology/OOD -> derivation/run hashes -> same-instant sibling packets`

## 2.2 Sibling ownership boundaries

MÖBIUS must preserve the following architectural separation unless an explicit future design revision changes it through reviewed evidence:

- **NEXUS** owns market-data operating fabric, identity, clocks, causal replay, data quality/source health, representation consensus, adaptive factors/topology/OOD inputs, and sibling-safe market packets.
- **AION** owns durable evidence memory, historical atlas, and long-lived provenance/evidence persistence.
- **ARGUS** owns true microstructure, order-flow, and execution-physics authority. Candle-derived proxies must not be relabeled as real L2/order-book truth.
- **ATHENA** owns supervisory world-state interpretation, confidence, abstention, risk, and routing authority.
- **DAEDALUS** owns scientific validation, protected evidence, research-candidate testing, and promotion authority.
- **ICARUS** owns production execution authority. NEXUS must not silently become an execution system.

## 2.3 NEXUS invariants to preserve

The prior architecture explicitly prohibits:

- trusting filename timeframe/representation claims as truth;
- silently sorting away repeated/fractional timestamps;
- deleting duplicate source lineage just because compute may be shared;
- inventing historical availability or receipt times;
- forward-filling missing state into truth without an explicit derived-imputation contract;
- allowing multiple equivalent representations to overweight one symbol merely by count;
- full-data normalization or centered/future-aware transforms in historical evaluation;
- calling OHLCV/candle proxies true order flow, depth, or L2;
- letting NEXUS absorb ATHENA, AION, ARGUS, DAEDALUS, or Icarus authority;
- production authorization from NEXUS.

MÖBIUS must model these as **machine-checkable architecture invariants**, not merely prose reminders.

## 2.4 Historical verification anchor

The 2026-09-23 NEXUS v0.3 handoff reported:

- NEXUS: 117/117 tests passed.
- AION: 11/11 passed.
- ARGUS: 4/4 passed.
- ATHENA: 3/3 passed.
- DAEDALUS: 45/45 passed.
- compileall passed.
- sibling validation passed.
- final contract-drift comparison reported zero raw and zero semantic AST drift against the sealed sibling boundary baseline.

Again: these are **checkpoint claims that require fresh verification** before being treated as current repo truth.

## 2.5 Historical corpus anchor

The v0.3 handoff described the currently accessible archive at that time as:

- 476 physical `.csv` members;
- 238 AppleDouble/resource-fork sidecars;
- 238 usable market CSV members;
- 1,970,753 usable rows;
- 231 distinct byte/logical market contents;
- 7 exact duplicate usable entries;
- 12 fractional-time streams;
- 47 filename-vs-observed-cadence mismatches;
- 64 cadence/quality-ambiguous streams withheld by the default factor gate;
- 174/238 admitted by default integrity policy.

A prior AION audit reportedly referenced:

- 626 usable entries;
- approximately 12,588,290 rows;
- nine ZIP archives.

The resulting unresolved gap reported by the handoff was:

- 388 usable entries;
- 10,617,537 rows.

The project owner also expected roughly 800+ files, but the prior handoff explicitly prohibited claiming complete corpus coverage until proven by manifests/hashes.

MÖBIUS should ingest these as **historical project claims with timestamps and sources**, not hardcoded eternal facts.

---

# 3. THE FUNDAMENTAL NEW IDEA: A BITEMPORAL PROJECT DIGITAL TWIN

Most coding agents maintain a flat, accidental view of project state:

> “I read file X, therefore X is current.”

That fails badly in multi-agent projects.

A handoff may describe a state that was true yesterday. A test result may refer to a different branch. A file may be copied from an older package. A model can learn a fact after the fact changed. A GitHub action can fail after documentation still says green.

MÖBIUS therefore uses **bitemporal project knowledge**.

For every meaningful project fact, track at least:

- `valid_from`: when the fact became true in project/repo reality, if known;
- `valid_to`: when it stopped being true, if known;
- `observed_at`: when MÖBIUS learned or observed the fact;
- `source`: commit, file, test log, artifact, user statement, CI run, dataset manifest, etc.;
- `confidence/evidence_grade`;
- `supersedes` relationships;
- `contradicts` relationships.

Example:

```json
{
  "claim_id": "claim:nexus-tests:117-pass",
  "subject": "NEXUS test suite",
  "predicate": "passed_count",
  "value": 117,
  "valid_from": "2026-09-23T00:00:00Z",
  "valid_to": null,
  "observed_at": "2026-09-24T15:00:00Z",
  "source": "START_HERE_SOL_EXTRA_HIGH_v0.3.md",
  "evidence_grade": "historical_handoff_claim",
  "verification_state": "needs_live_reverification"
}
```

If MÖBIUS later observes a live run with 121 tests passing, the new observation does not erase the old claim. It becomes a new claim with stronger evidence and a later validity interval.

This creates a project memory that can answer:

- What did we believe at time T?
- What was actually verified at time T?
- Which docs are stale?
- Which test results belong to which code state?
- Which claims remain unverified?
- Which facts changed after a handoff was written?

This is one of the most important mechanisms in the entire design.

---

# 4. CORE OBJECTIVE

MÖBIUS exists to maximize **verified capability gain per unit of scarce engineering attention**.

It should not optimize for:

- number of commits;
- number of files produced;
- number of agents dispatched;
- number of experiments run;
- benchmark score in isolation;
- code volume;
- novelty for its own sake.

It should optimize for durable, system-wide improvement.

A useful conceptual objective is:

```text
ExpectedValue(change) =
    Leverage
  * EvidenceNeed
  * Reusability
  * DependencyCentrality
  * FailureRecurrence
  * StrategicFit
  * ReconciliationFeasibility
  -------------------------------------------------
    Cost
  * RegressionRisk
  * EvidenceWeakness
  * IntegrationComplexity
  * DuplicationRisk
```

The exact formula should be configurable. The crucial point is that prioritization must be **evidence-backed and explainable**.

---

# 5. THE ONE LOOP

The single MÖBIUS cycle contains thirteen phases. These are phases of one state machine, not independent daemons.

## Phase 1 — OBSERVE

Collect evidence from whatever sources are currently accessible:

- repo tree and Git history when available;
- source files;
- tests;
- CI outputs;
- package manifests;
- dataset manifests;
- benchmark outputs;
- architecture docs;
- handoff docs;
- issue lists;
- TODOs;
- agent transcripts/handoffs;
- generated artifacts;
- user decisions;
- failures;
- environment/package versions;
- external research citations when appropriate.

Nothing is promoted to canonical truth merely because it is newer or appears in a file named `README`.

## Phase 2 — COMPILE THE TWIN

Normalize evidence into the project twin:

- artifacts;
- components;
- interfaces;
- contracts;
- invariants;
- data dependencies;
- runtime dependencies;
- ownership boundaries;
- tests;
- benchmarks;
- capability claims;
- unresolved questions;
- contradictions;
- failure fingerprints;
- negative knowledge;
- candidate opportunities.

Every derived node must retain source lineage.

## Phase 3 — FIND THE HIGHEST-LEVERAGE GAP

Scan the twin for unresolved gaps and rank them.

Priority inputs can include:

- number of downstream components affected;
- current failure frequency;
- uncertainty level;
- importance of violated invariant;
- whether the gap blocks several other tasks;
- whether it is duplicated across systems;
- expected information gain;
- severity if wrong;
- likelihood a fix generalizes;
- availability of evidence/tests;
- cost of implementation;
- merge/reconciliation risk.

The output is a **Leverage Decision Record** that explains why the selected target outranks alternatives.

## Phase 4 — PROPOSE A CHANGE HYPOTHESIS

The selected gap is converted into one or more falsifiable candidate changes.

Each candidate defines:

- intended capability gain;
- assumptions;
- affected components;
- expected interfaces;
- predicted failure modes;
- success metrics;
- falsification tests;
- rollback path;
- prohibited side effects.

For high-risk work, MÖBIUS may create several candidate implementations internally, but the outer workflow is still one loop.

## Phase 5 — BUILD IN SHADOW

Construct the candidate in an isolated workspace or repo-independent capsule.

Without repo access, the shadow build should rely on:

- known interface contracts;
- package snapshots;
- copied modules when legitimately available;
- synthetic fixtures;
- recorded manifests;
- generated adapters;
- machine-readable expected-change declarations.

Every change must declare exactly what it expects to touch later.

## Phase 6 — ATTACK THE CANDIDATE

Do not merely run happy-path tests.

Generate attacks from the twin’s known invariants and failure history:

- property tests;
- contract tests;
- regression tests;
- determinism tests;
- prefix-invariance tests;
- temporal leakage tests;
- malformed input tests;
- missingness tests;
- duplicate/reordering tests;
- timezone/clock tests;
- partial-source failure;
- dependency version drift;
- intentionally stale handoff information;
- contract mismatch;
- concurrency/restart/idempotency tests;
- resource stress;
- negative controls;
- null/randomized controls for research claims;
- ablation where relevant.

The objective is to discover **where the candidate stops being true**.

## Phase 7 — PROVE OR REJECT

MÖBIUS produces an Evidence Verdict.

Possible outcomes:

- `PROVEN_FOR_DECLARED_SCOPE`
- `CONDITIONALLY_SUPPORTED`
- `ENGINEERING_CORRECT_NOT_EFFICACY_PROVEN`
- `RESEARCH_SIGNAL_NOT_PROMOTED`
- `FAILED`
- `INCONCLUSIVE`
- `BLOCKED_BY_MISSING_EVIDENCE`

For market/research systems, engineering correctness must never be conflated with trading edge, profitability, causality, or predictive power.

## Phase 8 — PACKAGE A PROOF-CARRYING CAPABILITY CAPSULE

If the candidate survives, package it with evidence.

A capsule contains:

- source/code changes;
- exact intended destination paths;
- dependencies;
- interface assumptions;
- hashes;
- test definitions;
- test outputs;
- benchmark outputs;
- before/after comparison;
- known limitations;
- invariant checks;
- rollback plan;
- dependency impact graph;
- conflict expectations;
- evidence verdict;
- negative controls;
- unresolved questions;
- context pack for another model;
- machine-readable manifest.

The capsule is useful even with no GitHub access.

## Phase 9 — RECONCILE AGAINST REALITY

When the real repository becomes accessible, MÖBIUS compares the twin and capsule with the live tree.

It must detect:

- files added since shadow build;
- files deleted or moved;
- semantic interface drift;
- AST-level contract drift;
- branch divergence;
- dependency-version changes;
- duplicate functionality added by another model;
- previously solved problems;
- incompatible architectural changes;
- test-suite changes;
- stale destination paths.

Reconciliation should create a **patch plan**, not blindly apply old assumptions.

## Phase 10 — INTEGRATE SAFELY

Only after reconciliation:

- apply minimal changes;
- rerun affected tests;
- rerun architecture invariants;
- rerun sibling contract checks;
- compare behavior before/after;
- record actual changed files;
- record merge/commit identifiers;
- attach results back to the capsule.

## Phase 11 — OBSERVE THE OUTCOME

After integration, collect actual consequences:

- new failures;
- performance changes;
- CI state;
- benchmark deltas;
- interface drift;
- downstream behavior;
- code complexity change;
- resource use;
- newly exposed uncertainty.

This closes the gap between “change passed locally” and “change worked in the system.”

## Phase 12 — DISTILL KNOWLEDGE

Compress lessons into durable reusable forms:

- invariants;
- failure fingerprints;
- negative knowledge;
- architecture rules;
- benchmark cases;
- reusable test generators;
- routing guidance for future agents;
- dependency edges;
- project facts.

Do not preserve enormous reasoning transcripts when a small invariant captures the lesson.

## Phase 13 — UPDATE THE TWIN AND REPEAT

The final step writes the new evidence back into the twin and recomputes priorities.

The system begins the next iteration from a **strictly better evidence state** or explicitly records why no durable improvement occurred.

---

# 6. MACHINE-READABLE CORE MODEL

The receiving model should implement explicit schemas rather than leaving MÖBIUS as prose.

## 6.1 `ArtifactRecord`

```json
{
  "artifact_id": "artifact:<stable-id>",
  "kind": "source|test|doc|dataset|manifest|benchmark|handoff|ci_run|capsule|config",
  "path_or_uri": "...",
  "content_hash": "sha256:...",
  "semantic_hash": "optional normalized hash",
  "created_at": "...",
  "observed_at": "...",
  "source_system": "github|library|local|user|ci|agent",
  "branch": "optional",
  "commit": "optional",
  "version": "optional",
  "trust_class": "observed|reported|generated|inferred|historical",
  "metadata": {}
}
```

## 6.2 `ProjectClaim`

```json
{
  "claim_id": "claim:<id>",
  "subject": "component or fact subject",
  "predicate": "relationship/property",
  "value": {},
  "valid_from": "optional project time",
  "valid_to": "optional project time",
  "observed_at": "when Mobius learned it",
  "source_artifact_ids": ["artifact:..."],
  "evidence_grade": "direct|test|ci|commit|handoff|inferred|user_report",
  "verification_state": "verified|unverified|stale|contradicted|superseded",
  "confidence": 0.0,
  "contradicts": [],
  "supersedes": []
}
```

## 6.3 `ComponentNode`

```json
{
  "component_id": "component:nexus.time_kernel",
  "owner_system": "NEXUS",
  "purpose": "...",
  "inputs": [],
  "outputs": [],
  "depends_on": [],
  "consumed_by": [],
  "invariants": [],
  "tests": [],
  "risk_class": "low|medium|high|critical",
  "authority_boundary": "..."
}
```

## 6.4 `ContractRecord`

```json
{
  "contract_id": "contract:nexus->aion.observation",
  "producer": "NEXUS",
  "consumer": "AION",
  "schema_hash": "...",
  "semantic_fingerprint": "...",
  "prohibited_fields_or_states": [],
  "required_invariants": [],
  "verification_tests": [],
  "valid_from": "...",
  "observed_at": "..."
}
```

## 6.5 `InvariantRecord`

```json
{
  "invariant_id": "invariant:no_future_leakage",
  "scope": ["NEXUS", "DAEDALUS"],
  "statement": "Historical state at t must not depend on observations unavailable at t.",
  "severity": "critical",
  "enforcement": ["prefix_invariance", "availability_checks"],
  "evidence_sources": [],
  "violations": []
}
```

## 6.6 `FailureFingerprint`

```json
{
  "failure_id": "failure:<hash>",
  "signature": "normalized failure pattern",
  "first_seen": "...",
  "last_seen": "...",
  "affected_components": [],
  "root_cause_hypotheses": [],
  "confirmed_root_cause": null,
  "regression_test": null,
  "resolution_capsule": null,
  "recurrence_count": 0
}
```

## 6.7 `OpportunityRecord`

```json
{
  "opportunity_id": "opp:<id>",
  "problem": "...",
  "blocked_capabilities": [],
  "dependency_centrality": 0.0,
  "uncertainty": 0.0,
  "failure_recurrence": 0.0,
  "estimated_cost": 0.0,
  "regression_risk": 0.0,
  "expected_information_gain": 0.0,
  "reusability": 0.0,
  "priority_score": 0.0,
  "why_now": "..."
}
```

## 6.8 `ChangeHypothesis`

```json
{
  "change_id": "change:<id>",
  "opportunity_id": "opp:<id>",
  "hypothesis": "If X is changed, Y capability should improve under Z conditions.",
  "assumptions": [],
  "expected_touched_components": [],
  "success_metrics": [],
  "falsification_tests": [],
  "prohibited_side_effects": [],
  "rollback": "..."
}
```

## 6.9 `EvidenceItem`

```json
{
  "evidence_id": "evidence:<id>",
  "change_id": "change:<id>",
  "kind": "test|benchmark|static_analysis|contract_check|ablation|negative_control|manual_review",
  "result": "pass|fail|mixed|blocked",
  "measurement": {},
  "artifact_hashes": [],
  "environment": {},
  "reproducible": true,
  "limitations": []
}
```

## 6.10 `CapabilityCapsuleManifest`

```json
{
  "capsule_id": "capsule:<content-hash>",
  "title": "...",
  "intent": "...",
  "source_change_id": "change:<id>",
  "created_at": "...",
  "base_twin_root": "sha256:...",
  "expected_repo_base": {
    "commit": null,
    "contract_hashes": {}
  },
  "files": [],
  "dependencies": [],
  "interfaces": [],
  "tests": [],
  "benchmarks": [],
  "evidence": [],
  "verdict": "PROVEN_FOR_DECLARED_SCOPE",
  "known_limitations": [],
  "conflict_hotspots": [],
  "rollback": {},
  "merge_instructions": [],
  "context_pack": "context.md"
}
```

---

# 7. THE TWIN GRAPH

MÖBIUS should maintain a typed graph, not just a vector store.

Suggested node classes:

- System
- Component
- File
- Function/Class/Module
- Contract
- Dataset
- Stream/Representation
- Test
- Benchmark
- Invariant
- Claim
- Failure
- Opportunity
- Experiment
- Change
- Capsule
- Commit
- Agent/Handoff
- Environment

Suggested edge classes:

- `DEPENDS_ON`
- `PRODUCES`
- `CONSUMES`
- `IMPLEMENTS`
- `TESTED_BY`
- `VIOLATES`
- `PROTECTS`
- `SUPERSEDES`
- `CONTRADICTS`
- `DERIVED_FROM`
- `BLOCKS`
- `UNBLOCKS`
- `OWNED_BY`
- `HANDOFF_TO`
- `TOUCHES`
- `REGRESSES`
- `FIXED_BY`
- `VALIDATES`
- `PROMOTES_TO`
- `MUST_NOT_BYPASS`

The graph does not need a graph database initially. A deterministic SQLite schema plus materialized adjacency tables is enough. The interface should allow migration to a graph engine later.

---

# 8. STATE HASHING AND REPLAY

MÖBIUS should be able to answer:

> “What project state did this decision depend on?”

Use content-addressing throughout.

## 8.1 Twin root

Create a deterministic Merkle-style root hash from canonicalized hashes of:

- active artifact records;
- contract fingerprints;
- invariant set;
- verified claims;
- unresolved contradictions;
- environment identity;
- dependency graph revision.

A change capsule records the twin root it was built against.

If the live project later differs, reconciliation knows the candidate was developed against a different world state.

## 8.2 Deterministic replay

Project history should be replayable from append-only events such as:

```text
ARTIFACT_OBSERVED
CLAIM_ADDED
CLAIM_VERIFIED
CLAIM_CONTRADICTED
CONTRACT_CHANGED
TEST_EXECUTED
FAILURE_OBSERVED
CHANGE_PROPOSED
CHANGE_TESTED
CAPSULE_CREATED
CAPSULE_RECONCILED
CAPSULE_INTEGRATED
OUTCOME_OBSERVED
INVARIANT_DISTILLED
```

This permits reconstruction of the twin at historical checkpoints.

---

# 9. PRIORITIZATION ENGINE

The prioritization engine is one of the highest-value components.

A starting score:

```text
priority =
    (0.20 * normalized_dependency_centrality)
  + (0.15 * uncertainty_reduction_potential)
  + (0.15 * recurrence)
  + (0.15 * invariant_severity)
  + (0.10 * reusability)
  + (0.10 * blocker_count)
  + (0.10 * evidence_availability)
  + (0.05 * strategic_fit)
  - (0.10 * normalized_cost)
  - (0.10 * regression_risk)
  - (0.05 * duplication_probability)
```

Do not treat the weights as sacred. Version them and evaluate whether they select valuable work.

## 9.1 Leverage classes

MÖBIUS should distinguish:

### Local
One module, little downstream impact.

### Cross-cutting
Affects several components.

### Architectural
Changes an interface or ownership boundary.

### Epistemic
Improves what the system can reliably know, e.g. causal clock semantics, provenance, test validity, evidence calibration.

### Multiplicative
Improves future development itself: better testing, better context compression, better reconciliation, better prioritization.

Prefer multiplicative/epistemic work when it has credible downstream impact.

---

# 10. EVIDENCE GRADING

Every result must carry a grade.

Suggested grades:

- **E0 — assertion only**: a person/model says it is true.
- **E1 — static consistency**: code/schema/doc inspection supports it.
- **E2 — unit/property evidence**: isolated tests support it.
- **E3 — integration evidence**: cross-component behavior supports it.
- **E4 — replay/real-data evidence**: representative real artifacts support it.
- **E5 — adversarial evidence**: survives attacks, negative controls, mutation, perturbation.
- **E6 — operational evidence**: survives real CI/service/runtime integration over time.

Different claims require different minimum grades.

Examples:

- “function compiles” may need E1/E2.
- “contract is compatible” needs E3.
- “causal historical replay has no future leakage” should require strong E3/E4/E5.
- “this trading signal has edge” belongs to DAEDALUS-style statistical validation and cannot be promoted merely by engineering tests.

---

# 11. PROOF-CARRYING CHANGES

The core output is not “some code.”

It is:

> **code + evidence + scope + lineage + assumptions + rollback + integration map**

Every meaningful change should carry a proof packet.

Minimum proof packet:

1. What problem was selected?
2. Why did it outrank alternatives?
3. What exact project state was assumed?
4. What changed?
5. Which invariants were relevant?
6. What tests were run?
7. What negative controls were run?
8. What failed during development?
9. What remains unproven?
10. What files/interfaces are expected to conflict?
11. How can the change be rolled back?
12. What must be revalidated after live reconciliation?

This is what makes work transferable between models.

---

# 12. THE SHADOW WORKSPACE

Without repository access, MÖBIUS should use an isolated deterministic workspace.

Suggested layout:

```text
mobius/
├── README.md
├── pyproject.toml
├── src/mobius/
│   ├── core/
│   │   ├── events.py
│   │   ├── hashes.py
│   │   ├── ids.py
│   │   └── time.py
│   ├── twin/
│   │   ├── models.py
│   │   ├── store.py
│   │   ├── graph.py
│   │   ├── compiler.py
│   │   ├── contradictions.py
│   │   └── replay.py
│   ├── ingest/
│   │   ├── filesystem.py
│   │   ├── git.py
│   │   ├── docs.py
│   │   ├── tests.py
│   │   ├── ci.py
│   │   └── datasets.py
│   ├── leverage/
│   │   ├── opportunities.py
│   │   ├── scoring.py
│   │   └── decision_record.py
│   ├── changes/
│   │   ├── hypothesis.py
│   │   ├── shadow.py
│   │   └── diff_model.py
│   ├── verify/
│   │   ├── runner.py
│   │   ├── adversarial.py
│   │   ├── contracts.py
│   │   ├── determinism.py
│   │   ├── leakage.py
│   │   └── negative_controls.py
│   ├── capsules/
│   │   ├── manifest.py
│   │   ├── builder.py
│   │   ├── verifier.py
│   │   └── context_pack.py
│   ├── reconcile/
│   │   ├── scanner.py
│   │   ├── semantic_diff.py
│   │   ├── conflicts.py
│   │   └── plan.py
│   ├── knowledge/
│   │   ├── invariants.py
│   │   ├── failures.py
│   │   ├── negative.py
│   │   └── distill.py
│   └── cli.py
├── schemas/
├── tests/
│   ├── unit/
│   ├── property/
│   ├── integration/
│   └── fixtures/
├── state/
│   ├── twin.sqlite
│   ├── events.jsonl
│   └── blobs/
├── capsules/
├── reports/
└── docs/
```

This should be portable and runnable outside the Icarus repo.

---

# 13. REPO RECONCILIATION

When GitHub/repo access returns, never assume shadow paths still match.

## 13.1 Reconciliation sequence

```text
live repo snapshot
    ↓
content + semantic fingerprints
    ↓
compare against capsule base twin
    ↓
identify drift
    ↓
classify each touched surface
    ├── unchanged
    ├── text-only drift
    ├── semantic drift
    ├── conflicting implementation
    ├── component moved
    ├── solved elsewhere
    └── architecture changed
    ↓
recompute applicability
    ↓
generate patch plan
    ↓
apply minimal patch
    ↓
reverify
```

## 13.2 Semantic diffing

For Python code, use AST-normalized fingerprints in addition to raw hashes.

For JSON/YAML/TOML, canonicalize structure.

For schemas/contracts, canonicalize field names/types/requiredness/semantic markers.

For documentation, raw drift can be tolerated more easily, but any architectural-ownership or invariant text should generate a review event.

## 13.3 Duplicate-work detection

If another model independently implemented the same capability, MÖBIUS should not stack a second version on top.

Compare:

- symbols/classes/functions;
- interface behavior;
- tests;
- dependency edges;
- semantic descriptions;
- output schemas.

Possible outcomes:

- adopt live implementation and discard capsule;
- merge unique tests/knowledge only;
- replace live implementation if evidence supports it;
- keep both behind explicit experiment boundary;
- declare conflict requiring human/architectural review.

---

# 14. KNOWLEDGE COMPRESSION AND TOKEN ECONOMY

MÖBIUS should aggressively reduce future context cost.

## 14.1 Three layers of memory

### Raw evidence layer
Immutable original artifacts and hashes.

### Structured project layer
Claims, graph, tests, contracts, failures, opportunities.

### Distilled context layer
Small, task-specific context packs generated on demand.

Agents should normally receive the distilled layer plus exact pointers to supporting evidence, not entire histories.

## 14.2 Context pack format

```text
TASK
WHY THIS TASK
CURRENT VERIFIED STATE
RELEVANT COMPONENTS
INVARIANTS
KNOWN FAILURES
CONTRACTS
FILES LIKELY INVOLVED
TESTS TO RUN
WHAT IS UNVERIFIED
WHAT NOT TO CHANGE
EXPECTED OUTPUT
```

## 14.3 Delta-first handoffs

After the first full snapshot, handoffs should be primarily deltas:

- what changed since prior twin root;
- new facts;
- superseded facts;
- new failures;
- changed contracts;
- changed priorities.

This can dramatically reduce repeated token consumption.

---

# 15. NEGATIVE KNOWLEDGE

Failed attempts must become searchable assets.

Create a negative-knowledge record when:

- a candidate architecture fails tests;
- an optimization causes regressions;
- a feature duplicates existing functionality;
- a research hypothesis fails controls;
- a parser assumption is disproven;
- a contract interpretation is wrong;
- a model repeatedly hallucinates a nonexistent interface;
- a proposed change is rejected because it violates ownership boundaries.

Suggested schema:

```json
{
  "negative_id": "negative:<id>",
  "proposal_family": "...",
  "conditions_tested": {},
  "why_rejected": "...",
  "evidence": [],
  "retest_only_if": [],
  "related_failures": []
}
```

Before starting significant work, query negative knowledge for similar attempts.

---

# 16. SELF-IMPROVEMENT WITHOUT SELF-DECEPTION

MÖBIUS may improve its own prioritization and testing strategies, but those changes must pass the same proof process.

Track:

- predicted value of selected opportunities;
- actual downstream benefit;
- predicted cost vs actual cost;
- predicted conflict risk vs actual reconciliation difficulty;
- which tests caught bugs;
- which tests never add information;
- which agent/model produced reliable outputs for which task class.

Then calibrate future routing and prioritization.

The self-improvement target is not “be more autonomous.”

It is:

> make better project decisions with less repeated work and stronger evidence.

---

# 17. AGENT ROUTING

MÖBIUS can maintain empirical task-performance profiles for models/agents.

Task classes may include:

- codebase navigation;
- architecture design;
- algorithm implementation;
- debugging;
- test generation;
- statistical critique;
- documentation synthesis;
- data forensics;
- performance optimization;
- adversarial review;
- merge conflict reconciliation.

Do not assign work based only on brand/model reputation.

Record observed outcomes:

```json
{
  "agent_class": "model-or-agent-id",
  "task_class": "contract-debugging",
  "attempts": 14,
  "verified_successes": 11,
  "regression_rate": 0.07,
  "median_rework": 0.18,
  "evidence_quality_mean": 0.82
}
```

This supports evidence-based routing later.

---

# 18. ANTI-BLOAT RULES

MÖBIUS will fail if it becomes a bureaucracy generator.

Hard rules:

1. No new artifact without a consumer.
2. No duplicated report if a structured record can represent the same information.
3. No full-context handoff when a delta pack is sufficient.
4. No experiment without a decision it can influence.
5. No benchmark without a failure/capability it measures.
6. No permanent subsystem until repeated demand proves it is reusable.
7. No new abstraction merely because the code “might need it later.”
8. No model-generated certainty when evidence is absent.
9. No repeated failed idea without satisfying its `retest_only_if` conditions.
10. Every iteration must produce at least one of:
   - verified capability gain;
   - uncertainty reduction;
   - newly exposed failure;
   - reusable invariant/test;
   - durable knowledge compression.

If none occurs, classify the iteration as `NO_DURABLE_VALUE`.

---

# 19. FAILURE CONTAINMENT

MÖBIUS must be fail-closed around uncertain project state.

Examples:

- If a contract cannot be verified, mark compatibility unknown.
- If the base commit is missing, do not fabricate it.
- If two handoffs contradict, preserve both and generate a contradiction task.
- If a dataset’s identity is uncertain, do not silently merge it.
- If test output cannot be tied to a code hash/environment, treat it as weak evidence.
- If repo access is absent, do not claim a change is integrated.
- If live CI cannot be observed, do not claim operational success.

---

# 20. EXAMPLE: HOW MÖBIUS WOULD HANDLE A NEXUS TASK

Suppose the twin contains the unresolved historical corpus mismatch:

- accessible checkpoint: 238 usable files / 1,970,753 rows;
- prior AION checkpoint: 626 usable / ~12.59M rows;
- owner expectation: ~800+ files, unverified.

MÖBIUS does not immediately write a new ingestion engine.

It first asks structurally:

1. Is corpus incompleteness blocking other capabilities?
2. Which downstream tests/factors rely on coverage?
3. Is the larger corpus actually accessible?
4. Are there existing reconciliation tools already in NEXUS?
5. What evidence would prove coverage?

If this ranks highest, the change hypothesis might be:

> A content-addressed multi-archive reconciliation index can resolve the unexplained gap without changing market semantics.

Shadow build:

- archive/member manifest schema;
- raw/logical hashes;
- duplicate graph;
- reconciliation report;
- unresolved-entry reasons.

Attack:

- repeated archives;
- AppleDouble sidecars;
- corrupted member;
- renamed duplicate;
- same logical data with newline/encoding differences;
- mismatched filename cadence;
- partial archive set;
- deterministic worker-count parity.

Proof:

- manifest hash stable across runs;
- every previously known member accounted for or explicitly missing;
- no silent deduplication of lineage;
- no false completeness claim.

Capsule:

- code;
- schemas;
- tests;
- sample manifests;
- exact merge surfaces;
- instructions to reconcile with the live NEXUS repo.

When repo access returns, MÖBIUS scans current NEXUS first. If the capability was already implemented by another model, it keeps only any useful novel tests or knowledge.

This demonstrates why MÖBIUS is safer than “continue coding from an old handoff.”

---

# 21. EXAMPLE: STALE-HANDOFF DETECTION

Suppose a handoff says:

`NEXUS tests = 117 passed`

A later live repo shows:

`NEXUS tests = 131 passed`

A normal agent may simply overwrite 117 with 131.

MÖBIUS instead stores:

- historical claim: 117 at handoff checkpoint;
- observed live claim: 131 at current commit;
- relationship: superseded;
- both source hashes;
- both code-state hashes;
- a new verified current claim.

Now an old artifact remains interpretable instead of becoming “wrong data.”

---

# 22. EXAMPLE: ARCHITECTURAL BOUNDARY PROTECTION

Suppose a candidate change adds execution authorization into NEXUS because it makes a demo easier.

The twin sees:

- NEXUS authority boundary;
- Icarus execution ownership;
- invariant prohibiting NEXUS production authorization;
- sibling contract expectations.

The candidate is rejected before integration with a machine-readable reason:

```text
REJECTED_ARCHITECTURAL_BOUNDARY
violated: invariant:nexus-no-production-authorization
owner: ICARUS
```

This is far more reliable than hoping every future model remembers a paragraph from an old handoff.

---

# 23. IMPLEMENTATION PHASES FOR THE NEXT MODEL

The receiving model should not try to implement everything at once.

## Stage A — Minimum Viable Twin

Build:

- event log;
- SQLite store;
- artifact records;
- project claims;
- components;
- contracts;
- invariants;
- hashes;
- deterministic twin-root generation;
- CLI to ingest handoff/docs/filesystem snapshots;
- CLI to show contradictions and unverified claims.

Acceptance:

- same inputs produce same twin root;
- historical claims can coexist with newer claims;
- contradictions are visible, not overwritten;
- evidence lineage can be traced from derived fact to raw artifact.

## Stage B — Opportunity/Leverage Engine

Build:

- dependency graph;
- opportunity records;
- scoring;
- leverage decision report;
- blocker analysis;
- duplicate-work probability heuristic.

Acceptance:

- given a fixed twin, ranking is deterministic;
- ranking explains its factors;
- changing a critical invariant violation materially affects priority;
- isolated cosmetic tasks cannot outrank major blockers without configured reason.

## Stage C — Proof Harness

Build:

- change hypothesis schema;
- test/evidence runner abstraction;
- adversarial test registry;
- result grading;
- negative-knowledge store;
- evidence verdict generation.

Acceptance:

- failed candidates produce durable negative knowledge;
- engineering correctness and efficacy claims have different verdict classes;
- tests are tied to environment and artifact hashes.

## Stage D — Capability Capsules

Build:

- capsule manifest;
- file bundling;
- interface declaration;
- evidence packaging;
- context-pack generation;
- capsule verification command.

Acceptance:

- capsule verifies its own file hashes;
- another machine/model can understand intent, scope, assumptions, tests, and merge hotspots without the originating conversation;
- missing dependencies are explicit.

## Stage E — Repo Reconciliation

Build when repo access exists or against fixture repos:

- tree scan;
- raw hash comparison;
- Python AST semantic fingerprints;
- structured config canonicalization;
- conflict classification;
- applicability analysis;
- reconciliation report.

Acceptance:

- detects text-only vs semantic drift;
- detects missing/moved expected files;
- detects pre-existing equivalent functionality;
- never applies a stale capsule without revalidation.

## Stage F — Closed-Loop Outcome Learning

Build:

- post-integration outcome records;
- predicted-vs-actual scoring;
- prioritization calibration;
- agent routing statistics;
- test usefulness statistics.

Acceptance:

- MÖBIUS can identify which opportunity selections produced durable downstream improvements;
- its own prioritization changes are versioned and testable.

---

# 24. SUGGESTED CLI

```text
mobius init
mobius ingest <path-or-package>
mobius ingest-handoff <file>
mobius snapshot
mobius twin status
mobius twin root
mobius claims list
mobius claims contradictions
mobius graph impact <component>
mobius opportunities rank
mobius change propose <opportunity-id>
mobius change verify <change-id>
mobius capsule build <change-id>
mobius capsule verify <capsule-path>
mobius reconcile <capsule-path> <repo-path>
mobius reconcile report <id>
mobius outcome record <capsule-id>
mobius knowledge failures
mobius knowledge negative
mobius context build <task-or-opportunity>
mobius replay --at <timestamp-or-event-id>
```

---

# 25. DATA STORAGE STRATEGY

Start simple:

- SQLite for structured twin state;
- JSONL append-only event log;
- filesystem blob store keyed by SHA-256;
- JSON schemas for interchange;
- optional Parquet for large metrics/benchmark histories.

Do not require a graph database, Kafka, vector database, or distributed service in v1.

The architecture should permit adapters later.

---

# 26. TEST STRATEGY

MÖBIUS itself needs aggressive tests because it will influence other systems.

## 26.1 Determinism

- identical evidence -> identical twin root;
- ingestion order should not change canonical state where order is semantically irrelevant;
- event replay reproduces state.

## 26.2 Bitemporal correctness

- newer observation does not erase older historical fact;
- superseded claims remain queryable;
- contradictory claims are retained;
- “as known at time T” queries work.

## 26.3 Provenance

- every derived claim can trace to one or more sources;
- missing source prevents promotion to verified state.

## 26.4 Reconciliation

Fixture repos should test:

- file renamed;
- code reformatted only;
- semantic code change;
- interface moved;
- duplicate implementation;
- deleted dependency;
- added tests;
- changed package version;
- branch divergence.

## 26.5 Anti-bloat

Test that duplicate evidence/artifacts are content-addressed and do not multiply storage/state unnecessarily.

## 26.6 Safety of architecture boundaries

Encode known Icarus sibling ownership constraints as fixtures/invariants so attempted boundary violations are detectable.

---

# 27. OBSERVABILITY

Every loop iteration should produce a compact structured run summary:

```json
{
  "run_id": "mobius-run:...",
  "base_twin_root": "...",
  "selected_opportunity": "...",
  "candidate_changes": 2,
  "tests_executed": 47,
  "new_failures_discovered": 3,
  "verdict": "PROVEN_FOR_DECLARED_SCOPE",
  "capsule": "capsule:...",
  "integrated": false,
  "new_twin_root": "...",
  "durable_value": [
    "new regression test",
    "contract clarification",
    "portable capability capsule"
  ]
}
```

Do not generate huge prose logs unless requested.

---

# 28. STOP CONDITIONS

The loop must have explicit stopping conditions.

Stop an iteration when:

- selected question is answered;
- candidate is disproven;
- required evidence is inaccessible;
- reconciliation shows problem already solved;
- marginal information gain falls below threshold;
- implementation would violate an ownership boundary without an approved architecture change;
- cost exceeds configured limit;
- a human decision is required.

Do not continue generating variants merely because compute is available.

---

# 29. SECURITY AND TRUST

MÖBIUS may eventually ingest external repos, CI, credentials-scoped connectors, and artifacts.

Rules:

- never store raw secrets in the twin;
- hash or redact sensitive configuration values;
- separate evidence metadata from credential material;
- treat external artifacts as untrusted inputs;
- sandbox code execution where practical;
- require explicit permission for destructive repo operations;
- produce patches before direct writes when integration risk is high;
- record provenance of generated code.

---

# 30. RESEARCH-SPECIFIC GUARDRAILS

Because this ecosystem includes trading/research systems:

- no backtest result is automatically a production claim;
- no statistically interesting relationship becomes “causal” without appropriate evidence;
- no candle proxy becomes true order flow;
- no current-state engineering smoke test becomes evidence of profitability;
- any historical evaluation must preserve causal availability semantics;
- full-data normalization and future-aware feature construction are prohibited unless used only for explicitly non-causal descriptive analysis;
- research promotion remains with the appropriate validation authority, historically DAEDALUS.

MÖBIUS may package research candidates, tests, and evidence. It should not bypass the project’s promotion boundaries.

---

# 31. WHAT MAKES MÖBIUS DIFFERENT FROM ORDINARY “AGENT ORCHESTRATION”

Do not reduce this system to a task router.

Ordinary orchestration asks:

> Which agent should do task X?

MÖBIUS asks:

> Is task X actually the highest-leverage unresolved problem? What evidence says so? What project state does that conclusion depend on? What would falsify the proposed change? What downstream systems could regress? What durable knowledge should survive even if the implementation fails? How will the work be reconciled if the repo changes before integration?

The orchestrator is downstream of the project intelligence, not the center of it.

---

# 32. THE DEEPEST LONG-TERM EXTENSION: COUNTERFACTUAL PROJECT SIMULATION

Once the twin and dependency graph are mature, add a counterfactual impact engine.

Questions it should answer:

- If contract X changes, what downstream tests/interfaces become invalid?
- If NEXUS drops a field, which consumers are affected?
- If a dependency version changes, which capsules become stale?
- If we adopt candidate A vs B, which invariants are at risk?
- If a dataset is discovered to be unreliable, which research conclusions depend on it?
- If a component is removed, what becomes unreachable?

Initially this can be graph traversal and rule-based simulation.

Later, empirical historical outcomes can calibrate impact estimates.

This is where MÖBIUS becomes a true project digital twin rather than a catalog.

---

# 33. SECOND LONG-TERM EXTENSION: PROJECT CAUSALITY

Do not confuse dependency with causality.

MÖBIUS can learn from project history:

- which classes of changes tend to produce regressions;
- which interfaces are fragile;
- which tests predict later CI failures;
- which complexity metrics correlate with rework;
- which data-quality failures propagate into multiple systems.

These remain empirical project-process relationships, not automatic causal truth.

Use them to improve prioritization, not to make unjustified certainty claims.

---

# 34. THIRD LONG-TERM EXTENSION: AUTOMATIC CAPABILITY GENOMES

A mature capsule can become a **Capability Genome**: a self-describing unit of system evolution.

Genome contents:

- phenotype: observable capability;
- genotype: code/config/schema changes;
- environment requirements;
- ancestry: prior capsules/commits;
- evidence profile;
- regression profile;
- compatible contract versions;
- known conflicts;
- mutation history;
- negative controls;
- rollback path.

This enables comparison of competing implementations without losing provenance.

Do not build the full metaphor in v1. The underlying data structures are what matter.

---

# 35. FIRST USEFUL ITERATION FOR THE RECEIVING MODEL

Do **not** immediately modify NEXUS.

The first MÖBIUS iteration should prove that MÖBIUS itself works.

Recommended first target:

## Build the Minimum Viable Bitemporal Twin from existing handoff artifacts

Inputs:

- NEXUS blueprint;
- NEXUS takeover handoff;
- NEXUS next-model handoff;
- any accessible Icarus sibling handoffs;
- any accessible repo/package snapshot;
- current user-provided architecture constraints.

Output:

1. deterministic artifact manifest;
2. claim ledger;
3. component/ownership graph;
4. invariant registry;
5. contradiction report;
6. unresolved-opportunity list;
7. twin root hash;
8. generated compact context pack for “continue NEXUS safely.”

Why this is the best first iteration:

- it works without GitHub;
- it immediately reduces stale-context risk;
- it creates the substrate for every later loop phase;
- it can be tested deterministically;
- it does not interfere with existing Icarus code;
- it proves the core differentiator: evidence-aware project state.

---

# 36. ACCEPTANCE CRITERIA FOR MÖBIUS v0.1

MÖBIUS v0.1 is successful when all of the following are true:

1. It can ingest multiple project artifacts and retain their hashes/provenance.
2. It can represent historical claims separately from current verified facts.
3. It can detect contradictory claims instead of choosing one silently.
4. It can build a typed component/contract/invariant graph.
5. It can compute a deterministic twin root.
6. It can replay its event ledger to the same root.
7. It can generate a ranked opportunity list with transparent scoring.
8. It can package a candidate change as a proof-carrying capsule.
9. It can verify capsule integrity independently.
10. It can reconcile a capsule against a fixture repo with semantic drift.
11. It can preserve negative knowledge from a failed candidate.
12. It can generate a compact context pack for another model.
13. It never claims repo integration when repo access was unavailable.
14. It preserves Icarus sibling ownership boundaries as explicit invariants.
15. It distinguishes engineering evidence from market-efficacy evidence.

---

# 37. NON-GOALS FOR v0.1

Do not build these first:

- autonomous production trading;
- a general distributed agent platform;
- a full graph database cluster;
- Kubernetes deployment;
- Kafka unless needed for a real adapter;
- vector-search-heavy memory as the primary truth store;
- reinforcement learning for task prioritization;
- automatic destructive Git operations;
- automatic merging of architectural changes;
- a web dashboard unless needed for inspection after core correctness exists;
- a giant language-model prompt archive.

The twin, evidence ledger, proof harness, capsule, and reconciliation semantics are the core.

---

# 38. RECEIVING MODEL OPERATING INSTRUCTIONS

You are the receiving model responsible for turning this design into a working system.

Follow these rules:

1. **Do not restart Icarus/NEXUS.** MÖBIUS is an external meta-layer first.
2. **Do not assume old handoff claims are current.** Preserve them as historical evidence until verified.
3. **Do not invent repo state.** If GitHub is inaccessible, build against the shadow twin/capsule architecture only.
4. **Do not silently merge sibling authority.** Preserve NEXUS/AION/ARGUS/ATHENA/DAEDALUS/Icarus boundaries.
5. **Use test-driven development for core twin semantics.** Bitemporal claims, hashes, replay, and contradictions must be proven before broad features.
6. **Keep state append-only where feasible.** Corrections should supersede evidence rather than erase history.
7. **Make deterministic output a first-class requirement.** The same evidence set should compile to the same canonical twin state.
8. **Keep evidence grade explicit.** A handoff claim is not equivalent to a fresh live test.
9. **Build the smallest version that demonstrates the recursive loop.** Avoid infrastructure theater.
10. **Every implemented feature needs an acceptance test.**
11. **Every failure worth learning from becomes negative knowledge or a regression test.**
12. **Generate a new handoff/capsule at every meaningful checkpoint.**
13. **Before touching any live repo later, reconcile first.**
14. **When uncertainty remains, encode it. Do not guess it away.**

---

# 39. INITIAL WORK PLAN

A strong implementation sequence:

## Checkpoint 1 — Core IDs, hashes, event ledger

Implement stable IDs, canonical JSON serialization, SHA-256 utilities, append-only event log, replay skeleton.

Tests:

- deterministic canonicalization;
- hash stability;
- event ordering;
- replay equivalence.

## Checkpoint 2 — Artifact + bitemporal claim store

Implement ArtifactRecord, ProjectClaim, supersession, contradiction detection, as-known-at queries.

Tests:

- historical preservation;
- contradictory evidence;
- later stronger verification;
- stale claim behavior.

## Checkpoint 3 — Component/contract/invariant graph

Implement typed nodes/edges and impact traversal.

Seed it with the known Icarus sibling boundaries from this handoff.

Tests:

- downstream impact;
- forbidden authority edge;
- contract traversal.

## Checkpoint 4 — Handoff/document compiler

Parse structured facts from explicit configuration first; use LLM extraction only behind a review/evidence boundary.

Do not make free-form LLM extraction the sole truth path.

Tests:

- known NEXUS handoff fixtures;
- duplicate artifact ingestion;
- contradicting counts.

## Checkpoint 5 — Opportunity engine

Implement scoring and decision record.

Tests:

- critical invariant violation outranks cosmetic issue;
- blocker centrality affects ranking;
- cost/risk affect ranking predictably.

## Checkpoint 6 — Proof harness + verdicts

Implement evidence record, test runner interface, verdict taxonomy, negative knowledge.

Tests:

- failed candidate -> negative record;
- engineering-only proof cannot emit efficacy-proven verdict.

## Checkpoint 7 — Capsule

Implement build/verify/context pack.

Tests:

- tampered file fails verification;
- missing dependency visible;
- context pack reproducible.

## Checkpoint 8 — Reconciliation fixtures

Create simulated repos and test raw/semantic drift classification.

## Checkpoint 9 — First end-to-end MÖBIUS iteration

Use the existing NEXUS historical artifacts as evidence and produce:

- compiled twin;
- opportunity ranking;
- one small candidate improvement to MÖBIUS itself;
- proof;
- capsule;
- new twin state.

This proves recursion.

---

# 40. FINAL VISION

If implemented correctly, MÖBIUS becomes the layer that makes the rest of the system **easier to evolve without losing truth**.

Icarus and its sibling systems can continue specializing in market data, evidence, supervision, research validation, microstructure, and execution.

MÖBIUS does something different:

> It maintains the causal memory of how the project itself evolves.

It knows:

- what exists;
- what used to exist;
- what is merely claimed;
- what is verified;
- what contradicts what;
- which subsystem owns what;
- which failures recur;
- what change would matter most;
- what evidence would prove the change;
- how the change was tested;
- what it depends on;
- whether the live repo drifted;
- how to merge safely;
- what was learned if the attempt failed;
- what context the next model actually needs.

That transforms multi-agent development from a sequence of loosely connected conversations into a **replayable, evidence-carrying evolution process**.

The strategic objective is not maximal autonomy.

The strategic objective is:

> **Every iteration should leave the project easier to understand, harder to corrupt, cheaper to continue, and better able to identify its next highest-leverage improvement.**

That is the MÖBIUS loop.

---

# 41. COPY/PASTE MASTER DIRECTIVE FOR THE NEXT MODEL

Use the following as the starting directive when this file is handed to a stronger implementation model:

```text
You are taking ownership of MÖBIUS, the Proof-Carrying Project Digital Twin Evolution Engine described in this file.

Your task is NOT to restart Icarus, NEXUS, or any sibling system. Build MÖBIUS as an external, repo-independent meta-layer first.

Start by reading this entire document. Treat historical NEXUS facts as time-scoped evidence, not guaranteed current truth. Preserve the established authority boundaries: NEXUS market-data fabric, AION durable evidence memory, ARGUS true microstructure/execution physics, ATHENA supervisory state/risk/abstention/routing, DAEDALUS scientific validation/promotion, and Icarus production execution.

Implement the Minimum Viable Bitemporal Twin before advanced orchestration. The first required capabilities are:

1. deterministic canonical serialization and content hashing;
2. append-only event ledger and deterministic replay;
3. ArtifactRecord ingestion;
4. bitemporal ProjectClaim storage with valid-time vs observed-time semantics;
5. contradiction/supersession handling that never silently erases history;
6. typed component/contract/invariant graph;
7. deterministic twin-root hash;
8. impact traversal;
9. ranked OpportunityRecord generation with transparent leverage scoring;
10. ChangeHypothesis and evidence-verdict schemas;
11. proof-carrying CapabilityCapsule build/verify;
12. fixture-based repo reconciliation with raw and semantic drift classification;
13. negative-knowledge persistence;
14. compact delta-first context-pack generation.

Use tests as the primary specification for bitemporal semantics, determinism, provenance, replay, contradiction handling, capsule integrity, and reconciliation. Do not build infrastructure that is not required to prove these behaviors.

Every meaningful claim must carry evidence and provenance. Every test result must be tied to the artifact/code/environment state it evaluated. Never describe an engineering test as evidence of trading edge, profitability, or causality.

When GitHub/repo access is unavailable, continue using the shadow twin and capability capsules; never claim live integration. When repo access becomes available, reconcile before applying any capsule. Detect whether another model already implemented the capability and avoid duplication.

At each checkpoint produce:
- tests and results;
- current twin root;
- changed capability list;
- unresolved contradictions;
- highest-ranked next opportunity;
- a proof-carrying checkpoint capsule/handoff.

The first end-to-end demonstration must ingest the available NEXUS handoff/blueprint artifacts, preserve their historical test/corpus claims with timestamps and evidence classes, encode the sibling ownership boundaries as invariants, generate a deterministic project twin, surface contradictions/unverified claims, rank opportunities, and create a compact context pack for safely continuing NEXUS.

Do not optimize for code volume. Optimize for verified leverage, durable knowledge, deterministic state, and transferability between models.
```

---

# 42. SOURCE ANCHORS USED TO CREATE THIS HANDOFF

The design was grounded in previously generated project artifacts available in the user’s Library, especially:

- `READ_FIRST_SOL_EXTRA_HIGH.md`
- `START_HERE_SOL_EXTRA_HIGH_v0.3.md`
- `NEXUS_BLUEPRINT_v0.1.md`
- `NEXUS_NEXT_MODEL_HANDOFF_v0.1.md`
- `WORK_HANDOFF_SOL_EXTRA_HIGH.md`

The receiving model should locate the newest accessible versions of these artifacts and re-verify the live project before using their checkpoint claims operationally.

---

**END OF MASTER HANDOFF**
