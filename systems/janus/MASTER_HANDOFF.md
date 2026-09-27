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


## Latest verified direction — Run 007

Run 007 advances the offline JANUS twin with knowledge-time proof lifecycle and point-in-time conflict replay. Treat its generated verification artifacts as offline evidence only; reconcile any live repository before mutation.

## Run 010 continuation

Latest verified offline increment: **JANUS ∞ Run 010 — Automatic Causal Horizon Discovery**.

- Full suite: 42/42 passing.
- Python compilation: passed.
- Seed digest: `bf7298ae5d40fb00348cc7a85195efa6722ca983fe8b1ba531f428ce20e04bab`.
- Fresh handoff import reproduces the seed digest exactly.
- New API: `automatic_causal_horizon(change_id)`.
- New schema: `schemas/causal_horizon.schema.json`.
- New regression: historical supersession lineage survives later proof lifecycle status changes.
- Live-repository parity remains unverified; reconcile before mutation.

## Run 013
Added deterministic per-object Merkle inclusion proofs, missing-chunk discovery, and fail-closed receiver verification-contract negotiation. See `docs/RUN_013_INCREMENT.md`. Full suite: 54/54 passing; Python compilation passes.

## Latest verified offline checkpoint — Run 028
- Parent: Run 027.
- Full suite: 105/105 passing under `PYTHONPATH=src`.
- Compilation: passed.
- Added full SQLite WAL header/frame/salt/rolling-checksum validation.
- Added external SIGKILL-capable wait boundary after authoritative backup and before promotion-journal resolution; restart proves committed outcome from the already-promoted joint receipt.
- Added signed `janus-forensic-proof-link-v1` binding storage-fault audit -> recovery certificate -> session receipt/current receipt head -> fencing epoch.
- Live Git repository parity remains unverified; reconcile before any live mutation.

## Latest verified offline checkpoint — Run 029
- Parent: Run 028.
- Adds WAL-index/SHM-to-WAL consistency validation across duplicated header checksums, `mxFrame`, salts, last-commit checksum, backfill horizon, and `aPgno` frame map.
- Adds isolated kernel-enforced host storage fault probing via `RLIMIT_FSIZE` / `EFBIG`; the probe is scratch-only and must never target authoritative project truth.
- Adds `janus-forensic-proof-dag-v1`, joining forensic links, signed storage audits, quarantine evidence, recovery certificates, and receipt-chain anchors with content-addressed node verification, reference-closure checks, signature checks, and cycle rejection.
- Preserve JANUS ownership boundaries. This remains an offline checkpoint until reconciled against the authoritative live Icarus Git checkout.

## Latest verified offline checkpoint — Run 030
- Parent: Run 029 package SHA-256 `6244dcc32e71a578ecc56fefdff6069f8aa5cf27f0e55faec7d240f6fd763c45`.
- Adds `janus-storage-state-certificate-v1`: a non-self-mutating Ed25519 certificate over the logical project state, portable main-DB/WAL/SHM bytes+horizons, fencing epoch, receipt head, recovery certificate, session quarantine closure, and forensic DAG root/digest.
- Adds receiver verification that re-checks local project state, observed storage state, promotion journal/recovery state, receipt head, quarantine closure, forensic DAG signatures/reference closure, and root-link semantic alignment.
- Adds `run_host_permission_fault_probe()` for a second real kernel-enforced host failure class (`EACCES`/permission denial) isolated from authoritative project truth.
- Adds `live_reconciliation_gate()`, which refuses READY_TO_COMMIT unless a real Git worktree has a resolvable HEAD, a clean status, explicit expected artifact hashes, and exact hash matches. The actual Run 030 workspace returns `git_repository_unavailable` and therefore remains offline-only.
- Full final verification and artifact hashes are in `STATE_CAPSULE_RUN_030.md` and the adjacent standalone capsule packaged with the final ZIP.

## Run 031 checkpoint
Independent receiver replay now reconstructs JANUS state in an isolated staging database and separately verifies the original certified physical storage snapshot. Storage certificates can be linked through signed content-addressed delta entries with predecessor-chain continuity. A child-process RLIMIT_NOFILE probe adds real EMFILE coverage without touching authoritative storage. Live repository reconciliation remains blocked/unclaimed.

## Run 036 continuation
Run 036 adds descriptive-only acquisition provenance crosslinks, deterministic adversarial receipt-chain schedules, and possession-continuity cache snapshot/restore proofs. The exact Run 035 artifact was reconciled before changes: its Run 035 content manifest matches all 245 entries and pytest reproduces 132/132. A stale inherited generic checksum list is preserved as legacy evidence and corrected only in this new Run 036 candidate. Run 036 verifies 136/136 tests and 67/67 schemas; repository adoption/READY_TO_COMMIT remains unasserted.
