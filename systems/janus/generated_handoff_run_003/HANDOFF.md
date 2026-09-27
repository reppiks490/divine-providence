# JANUS Generated Handoff

State digest: `cfec2ddf5765fd9393eaa24982948598adfa901e256bfd5ed38fff3a8aa9865d`

## Current status

```json
{
  "candidates": 4,
  "components": 7,
  "contradictions": 0,
  "current_facts": 4,
  "facts": 5,
  "proof_bundles": 0,
  "quarantined_temporal_conflicts": 1,
  "snapshots": 0,
  "state_digest": "cfec2ddf5765fd9393eaa24982948598adfa901e256bfd5ed38fff3a8aa9865d",
  "temporal_conflicts": 1
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
