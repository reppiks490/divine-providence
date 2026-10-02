# ARGUS execution-evidence lineage firewall

ARGUS now distinguishes the source class of execution outcomes before impact
calibration is aggregated.

The implementation lives in `argus.execution_evidence`.

## Why this boundary exists

ICARUS currently exposes paper-emulator fills with fields such as timestamp,
entry ID, side, quantity, price, fill kind, position after fill, and a `live`
flag.

That `live` flag means the paper engine processed the fill during its live
engine epoch. It does **not** mean a broker or exchange confirmed an execution.

Without an explicit evidence boundary, a paper-emulator fill could be
accidentally summarized beside broker-confirmed fills and make a calibration
report look more realistic than its evidence supports.

## Evidence classes

Two execution evidence classes are currently supported:

- `BROKER_CONFIRMED`
- `ICARUS_PAPER_EMULATOR`

A broker-confirmed receipt must carry:

- broker name;
- broker order ID;
- broker fill ID;
- source repository/commit/run identity;
- exact source execution ID;
- decision/completion/observation times;
- requested/filled size and average price;
- SHA-256 of the canonical source payload.

A paper-emulator receipt is forbidden from carrying broker confirmation fields
or claiming market/broker confirmation.

## Content-addressed receipts

Each receipt is content-addressed as
`argus-execution-evidence-v1`.

Changing timing, size, price, source identity, payload hash, evidence class, or
broker lineage changes the receipt ID. Receipt validation recomputes that
identity before calibration.

## ICARUS paper adapter

`receipt_from_icarus_paper_fill` accepts the exact current ICARUS chart/runtime
paper-fill shape:

```text
ts, bar, id, side, qty, price, kind, comment, profit, pos, live
```

Important semantics:

- `ts` is the emulator fill bar/event time in whole seconds and is converted to
  nanoseconds for ARGUS;
- the current fill row does not preserve the original order-decision time, so
  the adapter requires it explicitly rather than inventing it;
- `live=true` remains paper-emulator evidence;
- quantity is treated as the filled instruction quantity of the emulator, not
  proof that equivalent real market size was executable.

## Durable ICARUS journal adapter

`receipt_from_icarus_journal_fill` accepts the current durable
`Journal.fills` row shape from ICARUS:

```text
id, run_id, live, symbol, ts, entry_id, side, qty, price,
kind, comment, profit, position_after
```

This adapter was defined only after inspecting the actual ICARUS runtime
journal/fill structures. It does not reinterpret closed `trades` rows as
execution fills.

Important semantics:

- `run_id` must be a positive runtime identity; legacy rows carrying the
  migration default `run_id=0` fail closed because they cannot prove a unique
  source run;
- `ts` remains the emulator completion/event time in whole seconds and is
  converted to nanoseconds;
- the journal does not persist the original order-decision timestamp, so
  `decision_time_ns` remains a mandatory separately proven input rather than
  being inferred from fill time;
- `observed_time_ns` is also supplied by the ingestion boundary and must not
  precede completion;
- SQLite row `id` is preserved in the source payload but is not treated as the
  execution's semantic identity.

The source execution ID is instead a SHA-256 over the exact fields used by
ICARUS's durable fill uniqueness rule:

```text
run_id, symbol, ts, entry_id, side, qty, price, kind, comment, position_after
```

The in-memory chart/runtime adapter now uses this same canonical identity. Its
extra `bar` field, boolean `live` flag, and profit annotation are treated as
representation metadata rather than independent execution identity. Therefore
the same ICARUS paper fill observed once through `recent_fills` and again
through the durable SQLite journal resolves to one upstream source execution.

If that fill is re-represented with a different SQLite row ID, chart bar index,
live flag, profit annotation, or observation timestamp, its receipt can change
while its upstream source-execution identity remains the same. The
execution-identity firewall therefore rejects double-counting it across either
one representation or both ICARUS surfaces.

As with the in-memory adapter, `live=1` means the paper engine processed the
fill during a live engine epoch. It is still
`ICARUS_PAPER_EMULATOR`, never `BROKER_CONFIRMED`.

## Lineaged calibration

`calibrate_lineaged_impact` preserves the entire immutable execution receipt
next to the existing impact-calibration observation.

The combined receipt + calibration observation also receives its own
content-addressed `impact-calibration-lineage` ID. Mutating either side of the
pair invalidates that lineage receipt.

Execution identity deliberately does not include `source_repo` or
`source_commit`. Those fields remain mandatory immutable provenance and are
still pinned by prospective study manifests, but changing adapter repository or
revision cannot manufacture a new upstream execution.

For `BROKER_CONFIRMED`, upstream identity is keyed from evidence class,
broker name, broker order ID, broker fill ID, and symbol. An adapter-local
`source_execution_id` rename therefore cannot duplicate one externally
confirmed fill.

For `ICARUS_PAPER_EMULATOR`, upstream identity is keyed from evidence class,
source system, source run ID, source execution ID, and symbol.

Before evidence-stratified aggregation, ARGUS verifies:

- receipt content identity;
- uniqueness of the upstream execution identity using broker order/fill lineage for broker evidence and source-system/run/execution lineage for paper evidence, so two receipt representations cannot double-count one execution while independent symbols remain distinct;
- combined calibration-lineage identity;
- execution ID binding;
- side and requested-size binding;
- realized fill-fraction binding;
- snapshot-age binding;
- completion-latency binding;
- no authority escalation.

## No paper/broker pooling

`calibration_by_execution_evidence` always emits separate strata by execution
evidence class.

Paper-emulator observations and broker-confirmed observations are never pooled
into one summary by this safe aggregation path.

That means a low paper-emulator MAE cannot silently be presented as broker-fill
calibration quality.

## Remaining limitation

Both current ICARUS paper representations preserve simulated fill outcomes but
not the original pending-order decision timestamp. The in-memory fill includes
its bar index; the durable journal row does not. Neither field is equivalent to
the order-decision timestamp.

Until ICARUS persists that timing directly, the caller must supply
`decision_time_ns` from a separately proven order-decision record. ARGUS does
not infer it from fill time, bar index, trade close time, or journal row order.

The current ICARUS journal also assigns `run_id = int(time.time())`, so runtime
identity has one-second resolution. ARGUS preserves that durable identity but
cannot reconstruct two process starts that ICARUS itself aliased into the same
second-level run ID. A future ICARUS runtime-provenance change should use a
collision-resistant per-process run identifier; this ARGUS PR deliberately does
not modify the separately owned engine/runtime scope.

## Authority

Neither receipt class grants order authority.

`execution_authorized=false`

`production_decision_authorized=false`

Broker confirmation means the historical execution evidence is broker-backed;
it does not authorize a new order.
