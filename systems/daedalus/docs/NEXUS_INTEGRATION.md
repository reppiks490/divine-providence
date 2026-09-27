# DAEDALUS — NEXUS Candidate Integration

DAEDALUS now accepts `nexus.daedalus-validation-handoff.v1` only through a fail-closed bridge.

## Safety contract

The bridge rejects a handoff if it attempts to:

- authorize production
- claim a protected holdout has already been safely spent
- mark current NEXUS-scanned history as pristine
- allow confirmatory validation on the same discovery history
- route behavioral candidates without requiring unseen evidence for confirmation

`daedalus nexus-handoff <handoff.json>` validates the contract and returns development-only task counts.

## Retrospective diagnostics

`daedalus nexus-diagnostics <handoff.json> <corpus-root>` evaluates blockwise stability without spending a protected holdout. These diagnostics can reject or deprioritize unstable discoveries, but **cannot confirm** a hypothesis whose selection used the same history.

On the current NEXUS iteration 0007 handoff:

- 13 behavioral candidates diagnosed
- 8 lag-direction candidates are retrospectively direction-stable
- 5 volatility-shift candidates show strong retrospective nonstationarity
- independent confirmation: false for all
- protected holdout touched: false

## Future-evidence readiness

`daedalus nexus-confirmation-readiness <handoff.json> <corpus-root>` checks for genuinely appended unseen rows without reading their return outcomes.

For an append-only continuation to qualify:

1. The updated source must be larger than the discovery source.
2. SHA-256 of the first `discovery_raw_size_bytes` must exactly equal the discovery raw SHA-256.
3. New timestamps must occur strictly after the discovery cutoff.
4. The required minimum number of new rows must exist.

If the historical prefix changed, the gate fails closed and requires reviewed reconciliation rather than pretending rewritten history is new evidence.

Current corpus status: all 13 behavioral candidates are `WAITING_NO_NEW_BYTES`; zero are ready for confirmatory evaluation.

These tools do not confer live execution authority and do not change DAEDALUS's protected-holdout ledger/protocol.
