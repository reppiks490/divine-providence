# JANUS ∞ Run 003 Increment — Authority-Aware Temporal Conflict Core

## Built

Run 003 advances the Run 002 bitemporal truth model with a conservative authority-aware temporal conflict core:

- detects differing unsuperseded facts whose validity intervals overlap, even when `valid_from` differs;
- introduces explicit, persisted authority-precedence policy scoped by subject prefix + predicate + authority;
- never invents authority ordering: missing policy quarantines the conflict;
- ties at the highest configured authority rank remain quarantined;
- a unique explicit authority winner is marked resolved;
- computes transitive downstream blast radius from the component dependency graph;
- marks unresolved conflicts `proof_required=true`;
- carries authority policy through handoff export/import and state digests;
- adds a JSON Schema for temporal conflict artifacts.

## Verification

The reference suite contains 13 tests. Run 003 added tests for interval-overlap detection, explicit authority resolution + blast radius, authority ties/quarantine, proof requirement, and authority-policy handoff round-trip.

## Deliberately not claimed

This increment does not yet implement evidence-quality ranking, multi-fact interval partitioning, automatic source trust, live repository reconciliation, or production integration. Those remain future work. Authority ranks are explicit policy only; JANUS does not infer them from names or confidence labels.
