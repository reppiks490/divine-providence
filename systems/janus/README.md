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
- `schemas/` — proof bundle, proof lifecycle, temporal replay, normalization, fact, candidate and contract schemas.
- `src/janus_infinity/` — executable reference implementation; Run 014 adds `cryptography` for Ed25519 signatures.
- `tests/` — deterministic tests for causal facts, contradiction detection, bitemporal replay, proof lifecycle, normalization overlays, prioritization, snapshots and handoff export/import.
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



## Latest increment — Run 007

Adds knowledge-time proof lifecycle and bitemporal conflict replay. See `docs/RUN_007_INCREMENT.md`.

## Run 007 capability

JANUS can replay the project conflict surface at `(valid_at, known_at)` while evaluating proof validity at the same knowledge boundary. Proof revocation/supersession is append-only and survives handoff round trips; raw archival conflict semantics remain unchanged.

## Latest increment — Run 008

Adds proof-supersession provenance DAG validation and a deterministic historical evidence archive. The compact handoff remains optimized for current authoritative transfer; the archive preserves the observations required to reproduce historical bitemporal conflict surfaces.

## Run 009

Run 009 adds a single authority/evidence adjudication kernel shared by archival and bitemporal conflict replay, plus `proof_impact_graph()` for causal before/after explanation from proof lifecycle state through normalization decisions, affected facts, conflict deltas, and downstream blast radius. See `docs/RUN_009_INCREMENT.md`.

### Run 010

`JanusTwin.automatic_causal_horizon(change_id)` automatically discovers proof-chain-dependent normalization decisions, affected validity intervals, replay points, knowledge transitions, conflict deltas, transitive blast radius, a transparent exposure score, and a deterministic read-only causal certificate. See `docs/RUN_010_INCREMENT.md`.

### Run 014

Run 014 adds Ed25519-signed Merkle root envelopes plus incremental evidence synchronization. Receivers can combine local and fetched content-addressed chunks, verify each Merkle inclusion before mutation, reproduce the causal certificate, and emit a deterministic sync receipt. Signature identity is deliberately separate from JANUS authority adjudication. This increment adds the `cryptography` runtime dependency. See `docs/RUN_014_INCREMENT.md`.

### Run 028
Run 028 upgrades storage forensics from WAL-header triage to full SQLite WAL header/frame/salt/rolling-checksum validation, proves externally induced process death after authoritative backup recovers as committed, and adds signed forensic proof links joining storage-fault audit evidence to promotion recovery and receipt history. Full offline suite: 105/105 passing; compileall passes. See `docs/RUN_028_INCREMENT.md`.

### Run 029
Run 029 adds SQLite WAL-index/SHM-to-WAL consistency validation, an isolated kernel-enforced `RLIMIT_FSIZE` storage-fault probe, and a unified forensic proof DAG verifier spanning forensic links, signed storage-fault audits, quarantine evidence, recovery certificates, and receipt-chain anchors. Full offline suite and final hashes are recorded in `STATE_CAPSULE_RUN_029.md`. See `docs/RUN_029_INCREMENT.md`.

### Run 030
Run 030 adds a non-self-mutating Ed25519 storage-state certificate binding project truth to portable DB/WAL/SHM state, fencing, receipt/recovery state, quarantine closure, and the forensic DAG root; a second real kernel host-fault probe for write-permission denial; and a fail-closed live Git reconciliation gate requiring explicit artifact hashes. Final verification/hashes are recorded in `STATE_CAPSULE_RUN_030.md`. See `docs/RUN_030_INCREMENT.md`.

## Run 031 — Independent Receiver Replay
Run 031 adds fresh-receiver reconstruction for signed storage-state certificates, signed/hash-chained storage-certificate deltas, and an isolated kernel `EMFILE` fault probe. Replay verifies bundle integrity, certificate signature, forensic closure, certified physical DB/WAL/SHM snapshot, and reconstructed project state before promotion.

## Run 032 — exact object replay closure and fork evidence

Run 032 adds an exact SHA-256-addressed replay graph for fresh receivers, rejecting missing, extra, or substituted objects before promotion. The receiver reconstructs only the project-state and certificate-verification closure, independently verifies the signed storage certificate against the certified DB/WAL/SHM snapshot, and emits a deterministic reconstruction receipt. It also adds cryptographic certificate-fork evidence without selecting a winning branch, plus an isolated kernel `RLIMIT_FSIZE` / `EFBIG` fault probe. See `ARCHITECTURE_INCREMENT_RUN_032.md` and `docs/RUN_032_INCREMENT.md`.

## Latest increment — Run 036
Run 036 cross-links compact acquisition receipt chains into proof lineage as descriptive-only provenance, adds deterministic splice/out-of-order/duplicate-round adversarial schedules, and adds cache snapshot/restore proofs that establish possession continuity while explicitly requiring separate temporal-truth revalidation. No winner selection or authority expansion is introduced. See `ARCHITECTURE_INCREMENT_RUN_036.md` and `STATE_CAPSULE_RUN_036.md`.

## Run 037
- Added portable provenance/cache-snapshot replay bundles for fresh receivers.
- Possession continuity remains descriptive-only and cannot mint temporal-truth validity.
- Added independent receiver truth-revalidation receipts bound to certified object replay.
- Added semantic corruption schedules for truncated receipt chains, crosslink-head mismatch, and snapshot object substitution.
- Full suite: 140/140 PASS; 70/70 Draft 2020-12 schemas valid; protected sibling authority boundaries unchanged.

## Run 038
- Added receiver-local durable truth-revalidation receipt chaining with stale-head/rollback detection.
- Preserved receiver-local revalidation history across subsequent certified project replay.
- Excluded that local control ledger from sender project-truth replay surfaces.
- Added descriptive cross-receiver replay-equivalence proofs.
- Added forged/stale truth-revalidation receipt semantic attack schedules.
- Full suite: 144/144 PASS; 72/72 Draft 2020-12 schemas valid; authority boundaries unchanged.
