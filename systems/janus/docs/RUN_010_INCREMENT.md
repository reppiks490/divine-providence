# JANUS ∞ Run 010 — Automatic Causal Horizon Discovery

Run 010 advances Run 009 without changing sibling-system authority boundaries.

## Increment

`automatic_causal_horizon(change_id)` discovers the causal replay surface instead of requiring a caller to guess a `valid_at` point or knowledge window. It traverses the historical proof supersession lineage, finds normalization decisions citing any connected proof, derives validity intervals and relevant fact boundaries, derives normalization/proof knowledge transitions, replays affected conflict surfaces before/after each transition, and emits a deterministic causal certificate.

The analysis is read-only. It never mutates source facts, normalization decisions, proof bundles, lifecycle events, or dependency declarations.

## Exposure score

The score is intentionally transparent rather than learned or probabilistic:

`min(100, 25*changed_conflict_boundaries + 10*affected_subject_predicates + 5*downstream_components + 5*normalization_decisions)`

It is an impact-prioritization heuristic, not evidence of market, operational, or business severity. The raw factors and formula travel with every result.

## Important correction discovered during Run 010

Proof lineage must be historical. A later lifecycle state such as `revoked` must not erase an earlier `superseded -> replacement` relation. Run 010 therefore builds causal-chain membership from all supersession events, while effective proof validity remains knowledge-time aware.

## Verification target

Run 010 adds regressions for automatic interval discovery, automatic knowledge-transition discovery, transitive blast radius, proof-chain traversal, deterministic certificates, and preservation of historical supersession lineage after later proof-status changes.
