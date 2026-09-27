# VERIFIED REPOSITORY INTERFACE SNAPSHOT

## AION @ 12a7cb8...
`aion/contracts.py`: EvidenceTier, SourceSpec, Observation, integer ns clocks, event/available/ingested/published constraints, synthetic retention, explicit trade/book/bar semantics.
`aion/replay.py`: deterministic as-of frame, stale-depth degradation, execution_authorized=False.
`aion/federation.py`: read-only sibling packet schema with production_authorized=False and execution_authorized=False.

## DAEDALUS @ 74ad941...
`identity.py`: unknown mapping -> UNLABELED/research-only; outside-root paths rejected.
`validation.py`: walk-forward and protected holdout evidence.
`promotion.py`: passed/failed scientific gates, not trading authority.
`holdout.py`: persistent exposure protocol accounting.
`registry.py`: mutable operational registry; not immutable evidence.
`bridge.py`: research-only ICARUS candidate export.

## ICARUS @ 007e701...
`ASTRA_DO_NOT.md`: explicit no-live/execution constraints for protected research work.
`icarus_bridge/models.py`: order-shaped TradingView alert schema; HELIOS must not reuse it.
`icarus_bridge/executor.py`, brokers, webhook: prohibited HELIOS imports/surfaces.
`icarus_engine/advisory.py`: isolated research ledger; export_candidate emits execution_authorized=False but module also contains provider network and strategy-patch logic, so HELIOS consumes serialized artifacts only.
`icarus_engine/server.py`: safe public/read endpoints include GET /healthz and GET /status/public.
