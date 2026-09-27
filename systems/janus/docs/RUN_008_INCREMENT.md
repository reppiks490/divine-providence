# JANUS ∞ Run 008 — Proof Provenance DAG + Historical Evidence Archive

Run 008 extends Run 007 without changing sibling authority boundaries.

## Added

- Knowledge-time `proof_provenance_graph(known_at)` over proof supersession edges.
- Cycle prevention for known proof replacement chains.
- Missing replacement targets are preserved for backward compatibility but surfaced as graph errors (`valid=false`).
- Deterministic proof-chain roots, paths, and terminals.
- Full historical archive export/import preserving all fact observations rather than only compact current-state facts.
- Archive digest excludes insertion-time noise so receiver reconstruction is deterministic.
- Historical archive round-trip proves that old `(valid_at, known_at)` conflict surfaces remain replayable.

## Invariants

1. Proof bundles remain immutable evidence objects.
2. Lifecycle events remain append-only.
3. A known supersession cycle is rejected before insertion.
4. Legacy missing replacement targets are not silently repaired; they remain explicit provenance errors.
5. Compact handoff and historical archive remain separate surfaces: compact handoff transfers authoritative current state; archive transfers replay evidence.
6. NEXUS/AION/ARGUS/ATHENA/DAEDALUS/Icarus ownership is unchanged.
