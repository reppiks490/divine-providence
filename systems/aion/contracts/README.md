# AION exchange contracts, version 1

These JSON Schema 2020-12 files describe the serialized Python objects passed to
`SourceSpec.from_dict`, `Observation.from_dict`, and the prediction record emitted
by `EventStore.predict`. Serialized dataclass defaults are present as fields.

Validate with the Python constructors and `validate_source_event` before storage.
The schemas check field shapes; cross-field rules (event/availability clocks,
source capability, sequence continuity, OHLC integrity, revisions and frame
membership) are enforced by the Python implementation. Pin a consumer to this
version and review any extension before connecting a sibling system.

No contract grants execution authority. Prediction output always carries
`execution_authorized: false`.
