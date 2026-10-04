# ARGUS receipt-time causal windows

ARGUS feature engines now have a journal-native bridge that binds every feature
window to evidence actually received by the decision instant.

The bridge lives in argus.causal_windows and is intentionally fail-closed.

## Trade windows

trade_window_asof reads only authenticated journal rows with
received_time_ns <= at_received_ns and preserves journal receipt order.

It never sorts a late trade back into history. If an unsequenced source delivers
a print whose event time moves backward inside the selected feature window, the
window is rejected instead of silently rewriting the past.

Raw journal trade evidence remains TRUE_TRADE, but an unknown aggressor side is
preserved as unknown. If the downstream flow engine uses tick-rule inference,
the resulting FlowDynamics packet is downgraded to INFERRED_TRADE.

## Depth windows

depth_window_asof reconstructs book states from authenticated TRUE_DEPTH
snapshots and deltas.

An unresolved contiguous-sequence gap invalidates the window. A
provider_recovery snapshot starts a fresh valid reconstruction segment. Deltas
before any valid baseline snapshot are never promoted into a synthetic book.

Every accepted snapshot or delta after the reconstruction baseline produces one
derived BookSnapshot, so depth dynamics can be computed over the state history
that was causally visible at the decision instant.

Crossed/locked or one-sided reconstructed books fail closed.

## Lineage

TradeWindow and DepthWindow carry the exact journal row SHA-256 identifiers that
fed the window.

CausalMicrostructureSnapshot carries both lineage sets together with:

- exact decision receipt time;
- latest trade-source receipt time;
- latest depth-source receipt time;
- trade-source staleness at decision time;
- depth-source staleness at decision time;
- FlowDynamics;
- AggressiveRun sequence;
- DepthDynamics;
- LiquidityField;
- execution_authorized=false;
- production_decision_authorized=false.

Staleness is measured in nanoseconds as decision receipt time minus the latest
used source receipt time.

## Feature construction

microstructure_snapshot_asof builds the current flow/aggressive-run/depth/
liquidity feature bundle from these causal journal windows. Aggressive runs are
segmented from the exact same receipt-time trade window used by FlowDynamics,
so an inferred side downgrades the affected run to INFERRED_TRADE. The
liquidity-field near-touch window defaults to min(3, depth_levels) and may be
set explicitly.

It does not fetch future rows, reorder late evidence, repair unresolved gaps, or
upgrade evidence tiers. It also does not grant trading, promotion, broker, or
production authority.

The next validation layer can use the row hashes and staleness fields to perform
deterministic replay and source-freshness stress tests without guessing which
evidence existed at the original decision instant.
