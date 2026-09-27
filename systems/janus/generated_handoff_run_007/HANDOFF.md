# JANUS Generated Handoff

State digest: `bf7298ae5d40fb00348cc7a85195efa6722ca983fe8b1ba531f428ce20e04bab`

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
  "proof_lifecycle_events": 0,
  "quarantined_temporal_conflicts": 1,
  "snapshots": 0,
  "state_digest": "bf7298ae5d40fb00348cc7a85195efa6722ca983fe8b1ba531f428ce20e04bab",
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
