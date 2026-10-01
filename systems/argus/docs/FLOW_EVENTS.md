# ARGUS causal aggressive runs and sweep-like descriptors

ARGUS Phase 3 begins with a deterministic event primitive built directly from
causal trade windows: consecutive same-side aggressor runs.

The implementation lives in `argus.flow_events`.

## AggressiveRun

`aggressive_runs` segments the already-validated trade sequence without
reordering it. An unresolved aggressor side breaks the active run.

Each run records:

- aggressor side;
- start/end event time and source-local sequence;
- trade count and total volume;
- volume-weighted average price;
- start/end/min/max price;
- distinct traded price levels;
- side-aligned net travel in ticks;
- total range and path length in ticks;
- directional efficiency;
- duration and maximum interarrival time;
- print-size concentration;
- evidence tier.

The evidence firewall is preserved:

- a run is `TRUE_TRADE` only if every member trade had an explicit aggressor
  side;
- if any member side came from tick-rule inference, that run is
  `INFERRED_TRADE`;
- inference can be disabled entirely.

## Sweep-like filter

`select_sweep_like_runs` is deliberately a descriptive research filter. It
selects multi-print, multi-level same-side runs using explicit thresholds for:

- minimum trade count;
- minimum distinct price levels;
- minimum side-aligned travel;
- minimum directional efficiency;
- optional maximum duration;
- optional TRUE_TRADE requirement.

A selected run is only **sweep-like**. It is not proof that stops were executed,
that a participant intentionally swept liquidity, that manipulation occurred,
or that a particular institution traded.

## Integrity checks

The selector validates the complete `AggressiveRun` object before using it.
Malformed externally constructed runs fail closed if, among other things:

- side, event time, sequence, count, duration, or interarrival fields are
  invalid;
- volume or price fields are non-finite/non-positive;
- VWAP or endpoints lie outside the declared run range;
- side-aligned travel exceeds the run range;
- range exceeds total path length;
- directional efficiency disagrees with aligned travel / path length;
- volume concentration is impossible for the finite number of prints;
- evidence tier is not TRUE_TRADE or INFERRED_TRADE.

This prevents a manually constructed or corrupted run from bypassing the same
invariants applied to runs derived by ARGUS.

## Causal integration

`CausalMicrostructureSnapshot` includes the aggressive runs produced from the
same receipt-time trade window that feeds `FlowDynamics`. Their provenance is
therefore the snapshot's exact trade journal row-hash lineage and source
staleness state.

The run layer grants no execution, broker, or production-decision authority.
