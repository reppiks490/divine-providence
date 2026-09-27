# JANUS Generated Handoff

State digest: `c5365be18c9c8cd4322e2659c15cdf181393e5ae71cccb88405a5462f2c09e7e`

## Current status

```json
{
  "active_normalization_overlays": 0,
  "candidates": 4,
  "components": 7,
  "contradictions": 0,
  "current_facts": 4,
  "facts": 5,
  "normalization_decisions": 0,
  "proof_bundles": 0,
  "quarantined_temporal_conflicts": 1,
  "snapshots": 0,
  "state_digest": "c5365be18c9c8cd4322e2659c15cdf181393e5ae71cccb88405a5462f2c09e7e",
  "temporal_conflicts": 1,
  "temporal_normalization_proposals": 0,
  "verified_normalization_overlays": 0
}
```

## Top next action

**C002 — Proof-carrying cross-model handoff round-trip**

Priority score: `2.221033`

## Receive rule

Verify the live project state before mutation. Treat this handoff as evidence with a content digest, not as a substitute for reconciliation.

## Authority rule

JANUS owns project-twin/reconciliation/handoff logic only. Preserve declared sibling authority boundaries.

## Contradictions requiring attention

- None detected under the current strict same-valid-boundary rule.

## State digest reproduction

Import `handoff.json` into a fresh JANUS instance and require an equivalent authoritative-state digest after normalization.
