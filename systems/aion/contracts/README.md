# AION exchange contracts

These JSON Schema 2020-12 files describe the serialized Python objects passed to
`SourceSpec.from_dict`, `Observation.from_dict`, and prediction records. Serialized
dataclass defaults are present as fields. New predictions use
`prediction.v2.schema.json`; the v1 schema is retained only to identify legacy
records without reconstructible ledger cutoffs.

Validate with the Python constructors and `validate_source_event` before storage.
The schemas check field shapes; cross-field rules (event/availability clocks,
source capability, sequence continuity, OHLC integrity, revisions and frame
membership) are enforced by the Python implementation. Pin a consumer to this
version and review any extension before connecting a sibling system.

No contract grants execution authority. Prediction output always carries
`execution_authorized: false`. Version 2 also carries
`performance_eligible: false` until independent source and outcome review.
