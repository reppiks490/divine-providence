# Agent rules for NEXUS

Read `docs/NEXT_MODEL_HANDOFF.md`, `docs/BLUEPRINT.md`, and `docs/CAPABILITY_CROSS_REFERENCE.md` before modifying code.

Do not weaken these invariants:
- no silent timestamp sort/deduplication
- no filename-only identity assumptions
- no candle proxy presented as L2/order-flow truth
- no current-row/future fitting in a synthetic point
- no production order authority
- no DAEDALUS protected-holdout access

When extending cross-system adapters, inspect the sibling's current contracts first rather than guessing schema fields.
