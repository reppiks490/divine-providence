# JANUS ∞ Run 009 — Unified Adjudication Kernel + Proof Impact Graph

Run 009 removes duplicated authority/evidence adjudication logic by routing archival and bitemporal conflict surfaces through `_adjudicate_facts()`. Authority remains lexicographically prior to evidence and missing explicit policy fails closed to quarantine.

`proof_impact_graph(change_id, valid_at, before_known_at, after_known_at)` now traces a proof lifecycle change through proof-backed normalization decisions, affected immutable facts/subjects, before/after bitemporal conflict surfaces, conflict deltas, and transitive subsystem blast radius. The graph is explanatory only: it does not mutate source facts, policies, proof bundles, or sibling-system ownership.

The knowledge window is ordered and reversed windows fail closed. Unknown proof IDs fail closed with `KeyError`.
