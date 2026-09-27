# Cross-system integration contract — proposed, not yet connected

## Boundary map

| Producer | AION input | Consumer | AION output |
| --- | --- | --- | --- |
| Icarus source collector or replay | Completed bars, scheduled/released macro, authentic trade events, source receipt metadata | Icarus | Read-only shadow preview and linked forecast/outcome evidence; no order command. |
| ARGUS reviewed adapter | Ordered trade/depth snapshots and deltas with source and sequence proof | ARGUS | Evidence-tiered true trade/depth observations and source gaps. |
| DAEDALUS research bridge | Eligible candidate manifest ID/status only, after its own protected protocol | DAEDALUS | Research context and source/representation lineage, without protected-tail contents. |
| ATHENA state producer | Advisory ID, uncertainty and model version after its own review | ATHENA | As-of prices, macro, flow, book quality and replay frame hash. |

`aion.federation.export_views(frame)` returns preview packets for all four. They are **not active adapters**. A consumer implementation must pin its schema version and reject unsupported fields or stale evidence. No component may translate an AION export into a broker instruction by convention.

## Observation contract

See `aion/contracts.py` and `contracts/observation.schema.json`. A registered `SourceSpec` fixes symbol and chart representation, native source hash, maximum evidence tier, provider/license reference and sequence policy. A versioned `Observation` has:

- `event_ns`: when the market event occurred, or for a bar when it **finished**. For a known schedule this can be in the future.
- `published_ns`: documented publication time, when available.
- `available_ns`: earliest verified time a decision process could use this version; the as-of gate.
- `ingested_ns`: actual collector receipt or later historical import, kept separate from availability.
- `source_event_id` and increasing `revision`: one economic/market fact through revisions.
- `sequence`: source-local ordering for equal timestamps and book/trade updates.
- `evidence_tier` and `quality_flags`: source capability and caveats; `synthetic` is mandatory for generated data.

For CSV backfills, catalog the file first. Retain the original archive/member and row position in the source manifest or payload, identify chart mechanics from owner/provider metadata, and prove bar-close availability. If first-known history is unknown, mark the source as unsuitable for strict historical decision replay instead of substituting the observation period or today's import time.

## Read-only flow

1. Provider adapter checks rights, raw hash, source clock and native ordering, then registers a **versioned** source manifest.
2. Adapter appends completed events. A sequence gap persists as invalidity until a provider-verified recovery snapshot, and replay preserves the prior gap in historical frames. Unsequenced corrections append a later revision with strictly later availability. Sequenced corrections await a reviewed adapter.
3. `frame(store, decision_ns)` selects only versions available by that instant. A scheduled event may be present; its outcome waits for its release. It derives confirmed price terrain separately for each representation and true book/flow only from eligible event types.
4. A shadow forecast records the exact frame hash, its cited event hashes, model version, decision horizon, and reason codes. Settlement occurs after the horizon as a separate row with an outcome reference.
5. ATHENA/ARGUS/DAEDALUS/Icarus can consume versioned read-only views. An actual integration must verify source, clocks, version and quality and may abstain.

## Clock and identity examples

| Situation | Required behavior |
| --- | --- |
| FOMC date scheduled before release | `schedule` visible in earlier frame; actual value/surprise hidden until release availability. |
| Revised GDP observation | Earlier decision returns earlier revision; later decision may return the new vintage. |
| Two Renko events with equal clock timestamp | Preserve distinct source event IDs and original source-local sequence. |
| 4-hour bar still forming | No completed bar event and no feature at this boundary. |
| Gap in depth sequence | Mark book invalid and request verified snapshot recovery; no silent carry-forward. |
| Candle-only order block | Keep a labeled, unvalidated `candle_origin_hypothesis`, evidence tier 1. |
| NQ vs QQQ or MNQ | Separate instruments, costs, fills and contract identities; never present one as the other's execution tape. |

## Acceptance before linking a sibling

- Pin current repository commit and review existing contracts with its owner/agent.
- Run determinism, temporal-availability, gaps/recovery, synthetic-tier, revisions and settlement tests using a real source fixture and a synthetic negative fixture.
- Compare the resulting shadow decision record against one independently recorded Icarus session, including session calendar, actual bar completion, costs and source latency.
- Review data rights and keep raw licensed feeds outside this repository.
- Document contract changes as an ADR and record exact commands/results in `docs/CURRENT.md`.
