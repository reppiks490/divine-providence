# JANUS ∞ Run 007 Design — Temporal Conflict Replay + Proof Lifecycle

## Intent
Extend Run 006 without changing sibling-system authority. JANUS should replay the conflict surface at a bitemporal coordinate `(valid_at, known_at)` and make proof validity itself knowledge-time aware.

## Design
1. Add an append-only `proof_lifecycle_events` ledger. A stored proof bundle keeps its immutable content/hash/base status; lifecycle events record later `revoked`, `superseded`, `proved`, or `integrated` status transitions with actor, reason, knowledge time, and optional replacement proof.
2. Make proof-reference verification accept a `known_at` boundary. The latest lifecycle event known by that boundary determines effective status; absent an event, the immutable bundle status remains the baseline for backward compatibility.
3. Add `temporal_conflicts_as_of(valid_at, known_at)`. It evaluates only facts known by `known_at`, applies only proof-valid normalization overlays known and not revoked at that boundary, tests interval membership at `valid_at`, then applies existing explicit authority/evidence policy. The output carries blast radius and proof/overlay lineage.
4. Preserve `temporal_conflicts()` as the archival raw-observation overlap detector from Run 003; do not silently change its semantics.
5. Include proof lifecycle events in state digest and handoff export/import so replay survives transfer.

## Safety invariants
- No proof lifecycle event mutates or deletes a proof bundle.
- No lifecycle status is inferred from prose or timestamps.
- Revocation/supersession affects only knowledge boundaries at or after the event.
- Authority precedence remains above evidence precedence.
- NEXUS/AION/ARGUS/ATHENA/DAEDALUS/Icarus remain external authorities; JANUS only records/replays evidence.
