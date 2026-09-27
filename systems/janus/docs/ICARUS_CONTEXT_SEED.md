# Icarus / NEXUS Context Seed for JANUS

This file is deliberately a **seed, not an unquestionable truth source**. The receiving model must re-verify live repository state before mutation.

## Current architectural shape inferred from preserved handoffs

NEXUS is described as the source-agnostic market-data substrate beneath the wider Icarus intelligence stack. Its pipeline is represented as:

`raw sources -> forensic manifest -> reviewed identity/clock policy -> causal native event fabric -> integrity/source-health gate -> representation-family consensus -> symbol plane -> adaptive factors/topology/OOD -> derivation/run hashes -> same-instant sibling packets`

Ownership boundaries repeatedly stated in the preserved handoffs:
- NEXUS: market-data operating fabric.
- AION: durable evidence memory / historical atlas.
- ARGUS: true microstructure / order-flow / execution-physics authority.
- ATHENA: supervisory world-state, risk, confidence, abstention and routing.
- DAEDALUS: research validation and promotion.
- Icarus: production execution.

JANUS must not collapse these roles.

## Latest preserved verification state to treat as a candidate fact until live re-check

A later NEXUS takeover handoff reports:
- NEXUS: 117/117 passed.
- AION: 11/11 passed.
- ARGUS: 4/4 passed.
- ATHENA: 3/3 passed.
- DAEDALUS: 45/45 passed on a fresh rerun.
- compileall passed.
- sibling contract validation passed.
- zero raw/semantic contract drift versus the sealed sibling baseline.

Earlier handoffs contain smaller NEXUS baselines (22, 80, 112), so the twin must represent these as historically valid/superseded claims rather than a contradiction that deletes history.

## Corpus facts preserved in the latest handoff

The currently accessible archive was reported as:
- 476 physical `.csv` members,
- 238 AppleDouble/resource-fork sidecars,
- 238 usable market CSV members,
- 1,970,753 usable rows,
- 231 distinct byte/logical market contents,
- 7 exact duplicate usable entries,
- 12 fractional-time streams,
- 47 filename-vs-observed-cadence mismatches,
- 64 cadence/quality-ambiguous streams withheld by the default factor gate,
- 174/238 admitted by default integrity policy.

A prior AION audit was reported as 626 usable entries / approximately 12,588,290 rows across nine ZIPs. Therefore full-corpus coverage is explicitly unresolved and must not be claimed until manifests/hashes prove it.

## Preserved non-negotiable data/causality rules

- Do not infer data identity solely from filenames.
- Do not silently sort, deduplicate, aggregate or forward-fill raw streams to make modeling easier.
- Preserve repeated timestamps and source-local order.
- Distinguish event time, availability time and ingestion/receipt time.
- Do not invent historical availability times.
- Do not call candle-derived proxies true L2/order flow.
- Do not let duplicate downloads or multiple representations silently overweight a symbol.
- Avoid future-aware normalization and centered transforms in historical evaluation.
- Exact duplicates may share compute but must retain lineage.
- NEXUS outputs remain non-production-authorizing.

## High-value unfinished areas reported in handoffs

- recover/reconcile the authoritative full corpus,
- finish reviewed representation-specific clock/identity policies,
- prove Arrow/Parquet replay parity at 12M+ scale,
- deploy same-instant sibling integration rather than only local validation,
- authenticated live source adapters and health telemetry,
- futures contract/roll identity and venue/session metadata,
- worker-count determinism,
- CI prefix-invariance certification,
- durable AION write-through of source-health/derivation/run manifests,
- representation-family consensus calibrated against the full corpus,
- live backpressure/restart/exactly-once/idempotency tests.

## Why JANUS should exist above this architecture

The preserved project already has strong domain subsystems. The expensive remaining problem is increasingly **coordination epistemology**:
- which handoff is current,
- what was actually verified,
- what changed after a handoff,
- which subsystem owns a claim,
- where duplicate work is happening,
- what next change has the highest cross-system leverage,
- what evidence would justify promotion,
- how to pass work across models without restarting.

JANUS targets that layer and should therefore improve every subsystem without replacing any of them.

