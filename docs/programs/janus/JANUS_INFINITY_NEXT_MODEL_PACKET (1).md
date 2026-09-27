# JANUS ∞ — SINGLE-FILE NEXT MODEL PACKET

This file concatenates the most important handoff material. The ZIP contains the executable implementation, schemas, tests, examples, generated handoff, and integrity manifest.


---
## BEGIN FILE: README.md
---

# JANUS ∞
## Causal Project Twin + Proof-Carrying Evolution Loop

JANUS ∞ is a single higher-order loop intended to subsume three separate ideas:

1. repo-independent development capsules,
2. validation/research loops,
3. later live-repository reconciliation.

Instead of treating those as separate systems, JANUS maintains a **causal digital twin of the project itself**. It tracks what exists, what is believed, when each belief became available, which subsystem owns which authority, what changed, what is uncertain, which candidate improvement has the highest expected leverage, what evidence would prove it, and what must be handed to the next model.

The core loop is:

`SENSE -> BIND -> RECONCILE -> PRIORITIZE -> FORGE -> FALSIFY -> PROVE -> CAPSULE -> HANDOFF -> LEARN -> SENSE`

The project twin is deliberately **proof-carrying**. A change is not considered promotable because an agent says it is good. It must carry its claims, assumptions, tests, affected contracts, causal-time constraints, rollback path, and evidence lineage.

The project twin is also deliberately **bi-temporal**:

- `valid_time`: when a fact/change is true in the project or market-data world.
- `known_time`: when JANUS/an agent actually learned or verified it.

This is the project-management analogue of the event-time / availability-time discipline already used in NEXUS. It prevents stale handoffs, old test counts, delayed discoveries, and contradictory documents from silently becoming current truth.

## Why this is the one loop

The earlier three-track design can be represented as three modes of the same twin:

- **No repo access:** ingest handoffs, manifests, files, datasets, test evidence, and generated work into the twin. Build isolated candidate capsules against explicit contracts.
- **Validation/research:** turn unknowns into hypotheses, rank experiments by information gain and dependency leverage, preserve negative results, and ratchet benchmarks.
- **Repo access restored:** scan the live repository, compare it to the twin, identify drift, build a minimal reconciliation plan, and only then propose integration.

No separate orchestration layer is needed to decide which of those modes is active. The twin detects available evidence and chooses the next safe action.

## Quick start

```bash
cd JANUS_INFINITY_HANDOFF
PYTHONPATH=src python -m janus_infinity init .janus/janus.db
PYTHONPATH=src python -m janus_infinity seed examples/icarus_seed_manifest.json .janus/janus.db
PYTHONPATH=src python -m janus_infinity status .janus/janus.db
PYTHONPATH=src python -m janus_infinity prioritize .janus/janus.db
PYTHONPATH=src python -m janus_infinity handoff .janus/janus.db --out janus_handoff
PYTHONPATH=src python -m janus_infinity import-handoff janus_handoff/handoff.json --db .janus/fresh.db
PYTHONPATH=src python -m unittest discover -s tests -v
```

To reconcile a checked-out repository later:

```bash
PYTHONPATH=src python -m janus_infinity snapshot /path/to/repo --db .janus/janus.db --label live-repo
PYTHONPATH=src python -m janus_infinity reconcile /path/to/repo --db .janus/janus.db
```

## Package contents

- `MASTER_HANDOFF.md` — the primary prompt/instruction package for the next model.
- `specs/JANUS_ARCHITECTURE.md` — detailed architecture and loop semantics.
- `docs/ICARUS_CONTEXT_SEED.md` — condensed, re-verification-required context derived from prior Icarus/NEXUS handoffs.
- `schemas/` — proof bundle, fact, candidate and contract schemas.
- `src/janus_infinity/` — executable reference implementation using only the Python standard library.
- `tests/` — deterministic tests for causal facts, contradiction detection, prioritization, snapshots and handoff export.
- `examples/icarus_seed_manifest.json` — seed components, boundaries, invariants, candidates and known verification facts.

## Design law

**JANUS may recommend, test, package and reconcile. It must not silently take another subsystem's authority.**

For the current Icarus architecture this means, at minimum:

- NEXUS owns market-data operating fabric.
- AION owns durable evidence memory / historical atlas.
- ARGUS owns true microstructure / execution-physics truth.
- ATHENA owns supervisory state / risk / confidence / abstention / routing.
- DAEDALUS owns scientific validation / promotion authority.
- Icarus owns production execution.
- JANUS owns only project-twin state, change evidence, prioritization, reconciliation plans, and handoff compilation.


## END FILE: README.md

---
## BEGIN FILE: MASTER_HANDOFF.md
---

# MASTER HANDOFF — BUILD JANUS ∞

## Receiving-model mission

You are receiving a design + executable seed for **JANUS ∞: the Causal Project Twin and Proof-Carrying Evolution Loop** for the Icarus ecosystem.

Do not respond by merely rewriting the architecture or proposing another orchestration framework. Your job is to **turn JANUS into a production-quality meta-engineering system** while preserving the authority boundaries of the existing Icarus subsystems.

The package is intentionally useful even when the live GitHub repository is unavailable. When the repo becomes available, JANUS must reconcile its twin against the live tree rather than assuming its capsule is current.

## First principle

Treat project knowledge with the same causal rigor that NEXUS applies to market data.

A fact may be true at one project time and only become known to an agent later. Therefore every consequential project fact should support at least:

- valid/project time,
- known/observation time,
- provenance,
- content hash,
- supersession,
- authority class.

This is the central differentiator. Do not reduce JANUS to a todo manager, RAG index, memory store, CI wrapper, or code-review bot.

## The one loop

Implement and strengthen this recurring state machine:

`SENSE -> BIND -> RECONCILE -> PRIORITIZE -> FORGE -> FALSIFY -> PROVE -> CAPSULE -> HANDOFF -> LEARN -> SENSE`

Each completed iteration must create durable value. If it does not reduce uncertainty, prove/falsify a consequential claim, strengthen a reusable test/invariant, resolve a high-centrality blocker, compress knowledge, or produce a reversible proof-carrying change, stop the branch.

## Required capabilities

### 1. Causal project fact ledger
Build a durable bi-temporal fact store. Support as-known-at and as-valid-at queries. Never delete superseded evidence merely to simplify the current view.

### 2. Project dependency twin
Represent components, contracts, datasets, transforms, tests, benchmarks, decisions, candidate changes and handoffs as a dependency graph. SQLite adjacency tables are acceptable initially; do not introduce graph infrastructure without evidence that it is needed.

### 3. Contradiction/supersession engine
Detect conflicting claims but distinguish genuine contradiction from historical supersession. Example: 80 passed at an earlier NEXUS checkpoint and 117 passed at a later checkpoint are not intrinsically contradictory.

### 4. Leverage engine
Rank next actions using cross-system impact, dependency centrality, uncertainty reduction, reusability, failure pressure, evidence gaps, cost, regression risk and duplication risk. Keep factor components visible; never hide the ranking behind one opaque scalar.

### 5. Hypothesis and variant forge
For high-impact gaps, generate materially different approaches. Do not create variants for trivial tasks. Every variant must declare falsifiers.

### 6. Adversarial proof harness
Attack candidates with stale state, missing evidence, ordering changes, duplicate inputs, worker-count changes, contract drift, corrupted manifests, unavailable siblings and rollback/replay scenarios.

### 7. Proof-carrying change bundles
No candidate is “promoted” without a machine-readable proof bundle containing exact claims, test commands/results, evidence hashes, contract impact, causal-time audit, authority audit, limitations and rollback.

### 8. Repo-independent capsule compiler
When no live repository is available, build isolated, content-addressed candidate capsules against explicit interface assumptions. Never pretend they are merged.

### 9. Live reconciliation engine
When a repo is available, scan it first. Compare snapshot hashes, contracts, tests and assumptions. Identify drift and duplicate work. Produce a minimal reconcile plan before proposing writes.

### 10. Negative knowledge + benchmark ratchet
Store failed approaches with retry conditions. Convert meaningful failures into permanent tests/fixtures/invariants whenever possible.

### 11. Handoff compiler
Produce both compact machine JSON and concise model-facing Markdown. The next agent should be able to resume from the handoff without rereading the entire conversation history.

### 12. Agent/task performance evidence
Optionally track which model/agent families perform well on which task classes, but treat it as empirical routing evidence, not a fixed hierarchy. Do not let routing logic become a source of unbounded orchestration complexity.

## Icarus authority boundaries that are architectural constraints

Preserve these boundaries until the live repos prove otherwise:

- NEXUS: market-data operating fabric.
- AION: durable evidence memory / historical atlas.
- ARGUS: authenticated microstructure/order-flow/execution physics.
- ATHENA: supervisory state/risk/confidence/abstention/routing.
- DAEDALUS: scientific validation/promotion.
- Icarus: production execution.
- JANUS: project-twin state, change evidence, prioritization, reconciliation and handoff compilation.

JANUS may observe proof from all siblings but does not gain their authority.

## Critical domain invariants imported from NEXUS

Do not violate them while building meta tooling around the project:

- Preserve raw lineage.
- Never trust filename semantics as authoritative identity.
- Preserve repeated/fractional timestamps and source-local sequence.
- Keep event/availability/ingestion concepts distinct.
- Never fabricate historical availability.
- Never relabel candle proxies as genuine L2/order flow.
- Never let duplicate representations silently create voting bias.
- No future-aware preprocessing in historical evaluations.
- Do not convert engineering smoke success into trading-edge claims.
- Do not grant NEXUS or JANUS production order authority.

## Development strategy

### Phase 0 — receive and verify
1. Read every file in this package.
2. Run the included tests.
3. Inspect the executable reference implementation.
4. If live repositories are available, snapshot them before any mutation.
5. Import current handoffs as evidence, not unquestioned truth.

### Phase 1 — harden the temporal fact ledger
Add migrations, indexes, explicit authority enums, supersession rules, source trust classes, as-known-at queries and deterministic export hashes.

### Phase 2 — build the project graph + leverage engine
Add dependency ingestion from code imports, declared interfaces, manifests, tests and docs. Keep derived graph facts separate from authoritative declarations.

### Phase 3 — proof bundle compiler
Make proof bundles first-class and content-addressed. Every candidate change should be able to generate an immutable proof manifest.

### Phase 4 — reconcile engine
Compare a live tree to the twin using stable file hashes, relevant semantic fingerprints, declared contracts and test state. Prefer AST/semantic comparison where textual churn is irrelevant.

### Phase 5 — loop executor
Implement one deterministic loop pass that:
- ingests evidence,
- updates the twin,
- identifies contradictions,
- ranks candidates,
- selects one bounded next action,
- emits its required proof plan,
- packages a handoff.

Do **not** make it an unbounded self-running agent. A loop pass must be inspectable, checkpointed, restartable and human-governable.

### Phase 6 — cross-agent handoff compression
Measure how much context can be safely removed while preserving successful resumption. Use proof hashes and structured facts to avoid repeatedly re-sending long narratives.

## High-value advanced extensions

Pursue only when the core is verified:

- semantic contract fingerprints,
- blast-radius simulation before integration,
- Monte Carlo project-change risk simulation,
- “counterfactual repo” branches evaluated as isolated capsules,
- learned but interpretable leverage weights from historical outcomes,
- graph community detection for hidden subsystem coupling,
- automatic context-packet minimization,
- proof-delta handoffs where only changed knowledge is transmitted,
- duplication fingerprints across agents/branches,
- change lineage from user intent -> decision -> code -> test -> benchmark -> handoff,
- causal attribution of regressions through dependency edges,
- adaptive verification budgets based on blast radius,
- deterministic distributed scans with worker-count parity.

## Do not build these anti-patterns

- an LLM memory dump mislabeled as a digital twin,
- a giant central service that absorbs sibling responsibilities,
- a background agent swarm that generates tasks endlessly,
- a ranking score whose components cannot be inspected,
- a “knowledge graph” with no temporal or provenance semantics,
- automatic merges based only on test pass/fail,
- silent mutation of canonical project state,
- destructive cleanup of superseded facts,
- autonomous trading or broker authority,
- claims of market edge derived from this infrastructure.

## Definition of done for JANUS v1

JANUS v1 is credible when it can, from a clean environment:

1. initialize an empty project twin;
2. ingest at least two conflicting/superseding handoffs;
3. reconstruct what was known at an earlier point in time;
4. snapshot a repository/filesystem deterministically;
5. identify drift against a prior snapshot;
6. maintain component ownership/contract boundaries;
7. rank candidate improvements with inspectable factors;
8. generate a proof plan for the top candidate;
9. attach test/benchmark results to a proof bundle;
10. export a repo-independent capsule manifest;
11. compile a compact handoff with exact evidence hashes;
12. ingest that handoff into a fresh JANUS instance and reproduce the same current-state summary.

The round-trip handoff test is crucial. If a fresh model/system cannot reconstruct the same state from the exported package, JANUS has not solved the core problem.

## Your first implementation move

Do not start by adding AI calls. The reference seed already proves the compact current-state round trip:

`seed evidence -> build twin -> export handoff -> initialize fresh twin -> import handoff -> compare authoritative current-state digest`

The included test suite currently passes this invariant. Your first substantial extension should therefore be **semantic live-repo reconciliation plus full-history evidence import/export**, while retaining the passing compact round-trip test. Add AST/interface fingerprints, explicit precondition/blocker handling for candidates, and a proof bundle for every reconcile proposal before touching live project files.

Only after deterministic reconciliation and proof-carrying promotion are strong should you add model-driven hypothesis generation or agent routing.

## Expected output of your work

Leave:
- tested code,
- updated schemas,
- architecture notes,
- migration notes,
- proof of deterministic round-trip,
- a new handoff for the next model,
- no unverified claim that integration into the live Icarus repo is complete unless you actually reconciled and tested the live tree.


## END FILE: MASTER_HANDOFF.md

---
## BEGIN FILE: specs/JANUS_ARCHITECTURE.md
---

# JANUS ∞ Architecture Specification

## 1. Mission

JANUS is a project-level causal digital twin and proof-carrying evolution loop. Its purpose is to make a complex multi-agent system progressively easier to understand, safer to modify, less repetitive to research, and cheaper to hand between models.

JANUS does **not** try to become another market model, execution engine, research authority, memory authority, or microstructure engine. It operates at the meta-engineering layer.

The system should answer five questions at any project instant:

1. **What is actually known?**
2. **What is contradictory, stale, unproved, or missing?**
3. **What change would create the greatest cross-system leverage?**
4. **What evidence is required before that change may be trusted?**
5. **What minimum context must the next model receive to continue without restarting?**

## 2. The loop

### Stage A — SENSE
Collect evidence without assuming authority.

Sources can include:
- repository filesystem and git metadata,
- test reports,
- benchmark outputs,
- Library/Work handoffs,
- design documents,
- CSV/data manifests,
- agent-produced capsules,
- issue/PR metadata,
- CI outputs,
- research results,
- human decisions.

Every observation is hashed and given provenance.

### Stage B — BIND
Convert observations into typed project facts.

Facts are never naked strings. Each fact has:
- subject,
- predicate,
- value,
- source,
- evidence hash,
- `valid_from` / optional `valid_to`,
- `known_at`,
- confidence state,
- authority class,
- supersession link if applicable.

The crucial distinction is:

`truth-in-project-time != time-the-agent-learned-the-truth`

This lets JANUS answer **as-known-at** queries and prevents hindsight leakage into prior project states.

### Stage C — RECONCILE
Find disagreements between evidence sources, snapshots, contracts and claimed baselines.

Examples:
- a handoff says 80 tests; a later freeze says 117;
- one package says DAEDALUS was not freshly rerun; another says 45/45 passed;
- an old blueprint calls a capability future work but the latest handoff says completed;
- a generated module expects an interface no longer present in the repo.

Reconciliation must prefer explicit supersession and newer verified evidence, not merely newer timestamps.

### Stage D — PRIORITIZE
Build a dependency-aware opportunity queue.

Candidate priority should reflect more than urgency. A useful default is:

`priority = impact * dependency_centrality * uncertainty_reduction * reusability * failure_pressure * evidence_gap / (cost * regression_risk * duplication_risk)`

All terms are bounded and recorded separately so a model can explain why a candidate ranked highly.

Special boosts:
- resolves contradictions used by many systems,
- reduces future context/token cost,
- eliminates classes of repeated failures,
- upgrades test/benchmark coverage,
- unlocks blocked downstream work,
- has a reversible integration path.

Special penalties:
- duplicates an existing sibling capability,
- weak or missing provenance,
- requires authority the subsystem does not own,
- cannot be falsified,
- would mutate raw evidence destructively,
- depends on unknown clock/availability semantics.

### Stage E — FORGE
Generate multiple materially different candidate solutions for high-impact problems.

The candidates should intentionally vary dimensions such as:
- simplicity,
- throughput,
- interpretability,
- isolation,
- streaming suitability,
- dependency footprint,
- storage model,
- failure containment.

The goal is not idea count. The goal is to avoid first-solution lock-in.

### Stage F — FALSIFY
Attempt to break candidates before promotion.

Generic adversarial mutations:
- delete or delay an input,
- perturb ordering,
- duplicate data,
- introduce stale evidence,
- change worker count,
- corrupt a manifest entry,
- alter timezone assumptions,
- remove a sibling service,
- replay from a checkpoint,
- supply contradictory handoff claims,
- use an older repo snapshot,
- inject an unverified “success” statement.

For market-data-adjacent work, preserve NEXUS restrictions: no invented availability times, no future-aware normalization, no collapsing repeated timestamps, no fabricated L2/order-flow claims.

### Stage G — PROVE
A candidate can advance only with a proof bundle.

A proof bundle contains:
- exact claim,
- scope,
- changed artifacts,
- input evidence hashes,
- test/benchmark commands,
- observed results,
- known limitations,
- dependency/contract impact,
- causal-time audit,
- authority-boundary audit,
- regression evidence,
- rollback plan,
- unresolved uncertainties.

“Looks good” is not proof.

### Stage H — CAPSULE
Package the candidate as a repo-independent integration capsule.

A capsule contains:
- source files,
- tests,
- schemas,
- assumptions,
- target interfaces,
- conflict zones,
- install/reconcile instructions,
- proof bundle,
- content hashes.

A capsule is safe to develop without live repo access because it never pretends the live repo matches its assumptions.

### Stage I — HANDOFF
Compile the smallest sufficient context for the receiving model.

The handoff should prioritize:
- authoritative current facts,
- unresolved contradictions,
- accepted invariants,
- ownership boundaries,
- exact latest proof state,
- next highest-leverage action,
- files to inspect first,
- commands to run before mutation.

It should exclude:
- long conversational history that has already been distilled,
- superseded implementation narratives,
- repeated descriptions,
- unverified claims presented as fact.

### Stage J — LEARN
Convert both successes and failures into durable project intelligence.

Positive knowledge:
- verified invariant,
- reusable design pattern,
- benchmark,
- proven contract,
- reliable agent/task pairing.

Negative knowledge:
- rejected approach,
- failure mechanism,
- conditions under which it failed,
- evidence needed before retrying,
- duplicate work fingerprint.

Then loop to SENSE.

## 3. Temporal truth model

JANUS uses project bi-temporality.

For fact F:

- `valid_from`: when the fact begins being true in the project reality it describes.
- `valid_to`: when it ceases being true, if known.
- `known_at`: when JANUS received/verified the evidence.

Example:

A test suite may have become 117/117 at commit C on September 23, but a later model may not learn that until September 24. Historical reasoning done before the discovery must not be rewritten as if the model knew it earlier.

This supports:
- as-known-at reconstruction,
- stale handoff detection,
- supersession without deletion,
- blame-free contradiction analysis,
- reproducible agent decisions.

## 4. Project graph

Nodes:
- subsystem,
- module,
- contract,
- dataset/archive,
- transform,
- test,
- benchmark,
- invariant,
- fact,
- decision,
- candidate change,
- proof bundle,
- capsule,
- handoff.

Edges:
- depends_on,
- owns,
- emits,
- consumes,
- validates,
- supersedes,
- derived_from,
- tested_by,
- blocked_by,
- contradicts,
- duplicates,
- affects,
- rolled_back_by.

The first implementation can store these in SQLite. A graph database is optional only if scale/queries justify it.

## 5. One-loop replacement for the earlier three tracks

### Repo-independent build mode
If no repo is available, JANUS operates on declared contracts and snapshots. It produces a capsule, not a fake merge.

### Validation/research mode
If the top-ranked gap is epistemic rather than implementation-based, JANUS generates an experiment and proof bundle instead of code.

### Repo reconciliation mode
When a repo becomes accessible, JANUS snapshots it and computes:
- new files,
- missing files,
- hash drift,
- contract drift,
- conflicting assumptions,
- likely duplicate work,
- required revalidation,
- proposed minimal integration steps.

All three are the same loop acting on different evidence availability.

## 6. Authority isolation

JANUS is forbidden from taking domain authority merely because it can observe the domain.

In the current Icarus design:

| Subsystem | Authority JANUS must preserve |
|---|---|
| NEXUS | market-data substrate, identity/time/replay/factors/topology packets |
| AION | durable evidence memory and atlas |
| ARGUS | authenticated microstructure/order-flow/execution-physics truth |
| ATHENA | supervisory interpretation, uncertainty, risk, abstention, routing |
| DAEDALUS | scientific validation and promotion |
| Icarus | production execution |
| JANUS | project twin, change evidence, prioritization, reconciliation, handoff |

## 7. Proof-carrying change protocol

Every proposed project mutation receives a `change_id` and must provide:

1. precondition snapshot hash,
2. problem statement,
3. expected leverage,
4. exact target boundary,
5. candidate implementation hash,
6. deterministic verification commands,
7. result artifacts/hashes,
8. regression scope,
9. contract deltas,
10. unresolved risk,
11. rollback instructions,
12. postcondition snapshot hash after integration.

A model can generate a candidate without proof. It cannot call the candidate promoted without the proof bundle.

## 8. Benchmark ratchet

Any meaningful bug, contradiction, leakage discovery or integration failure should become one of:
- regression test,
- static invariant check,
- fixture,
- adversarial scenario,
- contract fingerprint,
- handoff sanity check.

This creates a monotonic institutional-memory ratchet.

## 9. Negative knowledge ledger

Store rejected work using fingerprints so later agents do not rediscover the same dead end.

Required fields:
- family/signature,
- attempted context,
- rejection reason,
- evidence,
- date/known time,
- retry condition.

A candidate matching a negative-knowledge fingerprint receives a duplication penalty unless its retry condition is satisfied.

## 10. Handoff compiler

The compiler should produce two products:

### Machine handoff (`handoff.json`)
Structured facts, contracts, proof state, candidates and snapshot hashes.

### Human/model handoff (`HANDOFF.md`)
A compact narrative:
- mission,
- system map,
- current verified state,
- invariants,
- conflicts/unknowns,
- top next action,
- receive procedure,
- prohibited actions.

The receiving model must verify the live state before modifying anything.

## 11. Success metrics

JANUS is successful if, over time:
- restart/duplication rate falls,
- stale-handoff contradictions are detected automatically,
- average context needed for a clean handoff falls,
- more failures become permanent tests,
- high-centrality blockers are resolved earlier,
- candidate changes arrive with stronger evidence,
- repo reconciliation requires fewer broad rewrites,
- subsystem authority violations approach zero.

## 12. Anti-bloat law

A loop iteration is valuable only if it does at least one of the following:

- reduces a quantified uncertainty,
- verifies or falsifies a consequential claim,
- strengthens a reusable invariant/benchmark,
- resolves a high-centrality dependency blocker,
- compresses project knowledge without loss of authority/provenance,
- produces a reversible proof-carrying candidate.

Otherwise JANUS should record `NO_DURABLE_VALUE` and stop that branch.


## END FILE: specs/JANUS_ARCHITECTURE.md

---
## BEGIN FILE: docs/ICARUS_CONTEXT_SEED.md
---

# Icarus / NEXUS Context Seed for JANUS

This file is deliberately a **seed, not an unquestionable truth source**. The receiving model must re-verify live repository state before mutation.

## Current architectural shape inferred from preserved handoffs

NEXUS is described as the source-agnostic market-data substrate beneath the wider Icarus intelligence stack. Its pipeline is represented as:

`raw sources -> forensic manifest -> reviewed identity/clock policy -> causal native event fabric -> integrity/source-health gate -> representation-family consensus -> symbol plane -> adaptive factors/topology/OOD -> derivation/run hashes -> same-instant sibling packets`

Ownership boundaries repeatedly stated in the preserved handoffs:
- NEXUS: market-data operating fabric.
- AION: durable evidence memory / historical atlas.
- ARGUS: true microstructure / order-flow / execution-physics authority.
- ATHENA: supervisory world-state, risk, confidence, abstention and routing.
- DAEDALUS: research validation and promotion.
- Icarus: production execution.

JANUS must not collapse these roles.

## Latest preserved verification state to treat as a candidate fact until live re-check

A later NEXUS takeover handoff reports:
- NEXUS: 117/117 passed.
- AION: 11/11 passed.
- ARGUS: 4/4 passed.
- ATHENA: 3/3 passed.
- DAEDALUS: 45/45 passed on a fresh rerun.
- compileall passed.
- sibling contract validation passed.
- zero raw/semantic contract drift versus the sealed sibling baseline.

Earlier handoffs contain smaller NEXUS baselines (22, 80, 112), so the twin must represent these as historically valid/superseded claims rather than a contradiction that deletes history.

## Corpus facts preserved in the latest handoff

The currently accessible archive was reported as:
- 476 physical `.csv` members,
- 238 AppleDouble/resource-fork sidecars,
- 238 usable market CSV members,
- 1,970,753 usable rows,
- 231 distinct byte/logical market contents,
- 7 exact duplicate usable entries,
- 12 fractional-time streams,
- 47 filename-vs-observed-cadence mismatches,
- 64 cadence/quality-ambiguous streams withheld by the default factor gate,
- 174/238 admitted by default integrity policy.

A prior AION audit was reported as 626 usable entries / approximately 12,588,290 rows across nine ZIPs. Therefore full-corpus coverage is explicitly unresolved and must not be claimed until manifests/hashes prove it.

## Preserved non-negotiable data/causality rules

- Do not infer data identity solely from filenames.
- Do not silently sort, deduplicate, aggregate or forward-fill raw streams to make modeling easier.
- Preserve repeated timestamps and source-local order.
- Distinguish event time, availability time and ingestion/receipt time.
- Do not invent historical availability times.
- Do not call candle-derived proxies true L2/order flow.
- Do not let duplicate downloads or multiple representations silently overweight a symbol.
- Avoid future-aware normalization and centered transforms in historical evaluation.
- Exact duplicates may share compute but must retain lineage.
- NEXUS outputs remain non-production-authorizing.

## High-value unfinished areas reported in handoffs

- recover/reconcile the authoritative full corpus,
- finish reviewed representation-specific clock/identity policies,
- prove Arrow/Parquet replay parity at 12M+ scale,
- deploy same-instant sibling integration rather than only local validation,
- authenticated live source adapters and health telemetry,
- futures contract/roll identity and venue/session metadata,
- worker-count determinism,
- CI prefix-invariance certification,
- durable AION write-through of source-health/derivation/run manifests,
- representation-family consensus calibrated against the full corpus,
- live backpressure/restart/exactly-once/idempotency tests.

## Why JANUS should exist above this architecture

The preserved project already has strong domain subsystems. The expensive remaining problem is increasingly **coordination epistemology**:
- which handoff is current,
- what was actually verified,
- what changed after a handoff,
- which subsystem owns a claim,
- where duplicate work is happening,
- what next change has the highest cross-system leverage,
- what evidence would justify promotion,
- how to pass work across models without restarting.

JANUS targets that layer and should therefore improve every subsystem without replacing any of them.


## END FILE: docs/ICARUS_CONTEXT_SEED.md

---
## BEGIN FILE: docs/IMPLEMENTATION_ROADMAP.md
---

# JANUS ∞ Implementation Roadmap

## Milestone 1 — Deterministic knowledge substrate
- schema migrations
- strict timestamp parsing
- bitemporal queries: as-valid-at + as-known-at
- supersession graph
- fact source hashes
- deterministic state digest
- import/export round-trip test

## Milestone 2 — Evidence and authority
- source trust classes
- declared vs inferred facts
- authority ownership registry
- contract fingerprints
- proof bundle lifecycle
- prohibition checks for unauthorized promotion

## Milestone 3 — Project graph
- explicit dependency ingestion
- Python import graph adapter
- test-to-module linkage
- doc/contract linkage
- centrality calculation
- blast-radius estimator

## Milestone 4 — Reconciliation
- filesystem snapshot parity
- git commit/tree identity
- semantic fingerprints for Python interfaces
- stale-hand-off detection
- duplicate-work fingerprints
- minimal reconciliation plans

## Milestone 5 — Evolution loop
- opportunity generation
- transparent priority scoring
- proof-plan generation
- falsification templates
- branch/capsule manifests
- human-governed one-pass executor

## Milestone 6 — Handoff compression
- proof-delta packets
- round-trip reconstruction
- token/context budget measurements
- stale/superseded narrative pruning
- required-first-read ordering

## Milestone 7 — Advanced research
- learned but explainable leverage-weight calibration
- project graph communities
- causal regression attribution
- verification-budget optimization
- multi-agent empirical task routing


## END FILE: docs/IMPLEMENTATION_ROADMAP.md

---
## BEGIN FILE: docs/RECEIVER_CHECKLIST.md
---

# Receiver Checklist

Before modifying JANUS or integrating it into Icarus:

- [ ] Read README.md.
- [ ] Read MASTER_HANDOFF.md.
- [ ] Read specs/JANUS_ARCHITECTURE.md.
- [ ] Read docs/ICARUS_CONTEXT_SEED.md.
- [ ] Run `PYTHONPATH=src python -m unittest discover -s tests -v`.
- [ ] Seed a local twin from `examples/icarus_seed_manifest.json`.
- [ ] Confirm the historical 80 -> 117 NEXUS test evolution is not misclassified as a contradiction.
- [ ] Confirm a same-valid-time conflicting fact is detected.
- [ ] Confirm state digest is stable across repeated reads.
- [ ] If a live repo is available, snapshot before mutation.
- [ ] Reconcile the live repo against the latest available handoff/capsule.
- [ ] Do not claim live integration if only the offline capsule was tested.
- [ ] Preserve subsystem authority boundaries.
- [ ] Leave a new proof-carrying handoff at the end.

## END FILE: docs/RECEIVER_CHECKLIST.md

---
## BEGIN FILE: docs/TEST_REPORT.txt
---

test_as_known_at_prevents_hindsight (test_janus.JanusTests.test_as_known_at_prevents_hindsight) ... ok
test_handoff_is_deterministically_structured (test_janus.JanusTests.test_handoff_is_deterministically_structured) ... ok
test_handoff_round_trip_reproduces_state_digest (test_janus.JanusTests.test_handoff_round_trip_reproduces_state_digest) ... ok
test_historical_supersession_is_not_false_contradiction (test_janus.JanusTests.test_historical_supersession_is_not_false_contradiction) ... ok
test_priority_prefers_high_leverage_low_cost (test_janus.JanusTests.test_priority_prefers_high_leverage_low_cost) ... ok
test_same_valid_boundary_conflict_is_detected (test_janus.JanusTests.test_same_valid_boundary_conflict_is_detected) ... ok
test_snapshot_and_reconcile (test_janus.JanusTests.test_snapshot_and_reconcile) ... ok

----------------------------------------------------------------------
Ran 7 tests in 0.017s

OK

## END FILE: docs/TEST_REPORT.txt

---
## BEGIN FILE: docs/ROUNDTRIP_STATUS.json
---

{
  "actual_state_digest": "821ded359dc4fd00ebe1ecb9404f54a5d9a8d6c3d3bd6f3848f726cfe57a8ce7",
  "digest_match": true,
  "expected_state_digest": "821ded359dc4fd00ebe1ecb9404f54a5d9a8d6c3d3bd6f3848f726cfe57a8ce7"
}

## END FILE: docs/ROUNDTRIP_STATUS.json

---
## BEGIN FILE: examples/reference_proof_bundle.json
---

{
  "change_id": "JANUS-SEED-ROUNDTRIP-001",
  "claim": "The reference JANUS implementation can export compact authoritative current state and import it into a fresh twin with an identical state digest.",
  "scope": [
    "src/janus_infinity/core.py",
    "src/janus_infinity/__main__.py",
    "tests/test_janus.py"
  ],
  "precondition_snapshot": "reference-package-before-final-manifest",
  "postcondition_snapshot": null,
  "candidate_hash": null,
  "evidence": [
    {"kind": "unit_test", "name": "test_handoff_round_trip_reproduces_state_digest"},
    {"kind": "unit_test", "name": "test_as_known_at_prevents_hindsight"},
    {"kind": "unit_test", "name": "test_historical_supersession_is_not_false_contradiction"}
  ],
  "verification": [
    {
      "command": "PYTHONPATH=src python -m unittest discover -s tests -v",
      "expected": "7 tests pass"
    }
  ],
  "contract_deltas": [],
  "causal_time_audit": {
    "bitemporal_fact_fields": ["valid_from", "valid_to", "known_at"],
    "hindsight_guard_tested": true
  },
  "authority_audit": {
    "janus_authority": "project_twin_reconciliation_handoff",
    "domain_authority_absorbed": false
  },
  "limitations": [
    "Compact handoff imports authoritative current state, not the complete historical fact ledger.",
    "Semantic AST/interface reconciliation is specified but not yet implemented in the reference seed.",
    "No live Icarus repository integration is claimed by this package."
  ],
  "rollback": {
    "method": "Delete the fresh imported twin; source handoff remains immutable.",
    "destructive": false
  },
  "status": "proved"
}

## END FILE: examples/reference_proof_bundle.json
