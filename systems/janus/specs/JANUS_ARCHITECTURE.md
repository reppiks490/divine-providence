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


## Bitemporal reconstruction gate (v0.2 increment)

JANUS now exposes an explicit `facts_as_of(valid_at, known_at)` query. A project fact is eligible only when its project-valid interval contains `valid_at` and the fact was known by `known_at`. This separates retrospective truth (what later evidence says was true then) from contemporaneous agent knowledge (what the system could have known then). Explicit `valid_to` boundaries are enforced; expired facts do not remain silently current. This gate is project-state infrastructure only and does not alter NEXUS market-time authority or sibling responsibilities.

## Run 003 — Authority-Aware Temporal Conflict Core

Temporal contradiction is defined over overlapping validity intervals, not only identical `valid_from` boundaries. JANUS compares unsuperseded facts sharing `(subject, predicate)` and flags differing values when their half-open validity intervals overlap. Resolution is conservative: JANUS may resolve automatically only when an explicit persisted authority-precedence policy yields one unique highest-ranked fact. Missing policy or a top-rank tie is quarantined and requires proof/review. The conflict artifact also carries the transitive downstream dependency blast radius. Authority policy participates in the state digest and handoff round-trip.

## Run 004: evidence-aware adjudication and temporal normalization

Conflict adjudication is lexicographic and policy-driven: explicit authority precedence first; only an authority tie may consult explicit evidence precedence. Confidence labels have no built-in semantic rank. If policy is incomplete or tied, quarantine remains mandatory.

Temporal interval normalization is non-mutating by default. JANUS may emit an interval-closure proposal only for a narrow same-source/same-authority progression pattern. A proposal is evidence for review, not permission to rewrite history; acceptance requires a future proof-backed approval operation.
