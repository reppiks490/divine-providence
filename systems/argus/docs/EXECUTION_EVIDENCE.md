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

## Lineaged calibration

`calibrate_lineaged_impact` preserves the entire immutable execution receipt
next to the existing impact-calibration observation.

The combined receipt + calibration observation also receives its own
content-addressed `impact-calibration-lineage` ID. Mutating either side of the
pair invalidates that lineage receipt.

Execution identity deliberately does not include `source_repo` or
`source_commit`. Those fields remain mandatory immutable provenance and are
still pinned by prospective study manifests, but changing adapter repository or
revision does not manufacture a new upstream execution when evidence class,
source system, source run, symbol, and source execution ID are unchanged.

Before evidence-stratified aggregation, ARGUS verifies:

- receipt content identity;
- uniqueness of the upstream execution identity within its evidence/source-system/run/symbol namespace, so two different receipt representations cannot double-count one source execution while independent symbols remain distinct;
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

The current ICARUS paper fill record is sufficient to preserve a simulated fill
outcome but not the original pending-order decision timestamp. Until ICARUS
persists that timing directly, the caller must supply decision time from a
separately proven order-decision record.

ARGUS does not infer it from fill time.

## Authority

Neither receipt class grants order authority.

`execution_authorized=false`

`production_decision_authorized=false`

Broker confirmation means the historical execution evidence is broker-backed;
it does not authorize a new order.
