# Sibling Binding Architecture — PROMETHEUS v0.2

## Purpose

PROMETHEUS v0.2 binds the research loop to the recovered NEXUS v0.3 `SiblingInstantBundle` shape without importing NEXUS or any sibling repository at runtime.

The adapter is read-only. It validates one NEXUS same-instant bundle, preserves sibling authority metadata, normalizes only explicit fields, and then delegates to the existing PROMETHEUS plugin/SENTINEL/FORGE path.

## Binding reference

The release-pinned sibling contract snapshot identity is:

`1119ef3d9b561dc89668a9768893a2b1ab09cd542ffd1d7a02dd73f5a81388a2`

This value comes from the recovered NEXUS v0.3 release/verification artifacts. A second recovered snapshot hash, `7732e75d5e47b3b71fe49d99c2d4a9b81abb4730ee37c122d2a3d30c5f69c6ff`, differs because the snapshot identity includes absolute source paths. NEXUS's own final drift report records `raw_drift=false` and `semantic_drift=false` across the AION, ARGUS, ATHENA, and DAEDALUS boundary files. PROMETHEUS therefore pins the release identity and does not recompute it from local paths.

## Read-only flow

```text
NEXUS SiblingInstantBundle
        |
        v
validate_nexus_bundle
        |
        +-- reject production_authorized=true
        +-- verify decision_ns/frame_hash/bundle_hash
        +-- verify release contract snapshot identity
        +-- require mapping-shaped sibling payloads
        |
        v
normalize_nexus_bundle
        |
        +-- NEXUS market-state evidence
        +-- ARGUS CANDLE_PROXY evidence
        +-- ATHENA state_input/advisory evidence
        +-- DAEDALUS RESEARCH_CANDIDATE_ONLY evidence
        |
        v
PrometheusLoop.run
        |
        v
plugin audit -> SENTINEL -> FORGE -> research memory
```

`NexusRunInput` is deliberately thin. It calls the adapter and then constructs the ordinary `RunInput`; it does not fork plugin selection, disagreement detection, adversarial checks, replay comparison, or memory behavior.

## Projection rules

Shared NEXUS context is exposed under common dimension names only when those values already appear in sibling payloads:

- `factor:<name>`
- `quality:<name>`
- `ood:<name>`
- selected scalar `source_health:<name>` fields

This allows PROMETHEUS to detect routing or projection inconsistencies such as ARGUS and ATHENA receiving different values for the same NEXUS factor.

Role-specific fields remain role-specific metadata:

- ARGUS: `evidence_tier=CANDLE_PROXY`, `microstructure_truth=false`.
- ATHENA: `purpose=state_input`, `advisory_only=true`.
- DAEDALUS: `status=RESEARCH_CANDIDATE_ONLY`, `production_authorized=false`.

PROMETHEUS does not translate numeric factor sign into direction, confidence, regime, risk posture, execution feasibility, or any other semantic conclusion that the authoritative payload did not name.

## Availability and causal time

The adapter uses `availability_state=KNOWN` only after the NEXUS bundle has passed same-instant validation and the sibling projections agree with the outer `decision_ns`. It does not create per-source receipt or availability timestamps.

A mismatch in AION, ARGUS, ATHENA, or DAEDALUS decision time is a causal-instant failure. Strict callers receive an exception. `try_bind_nexus_bundle` converts the same condition into an immutable `FailureCase` for quarantine/research tracking.

## Contract drift quarantine

`try_bind_nexus_bundle` produces research-only failure artifacts for:

- `CONTRACT_DRIFT` when the observed release contract identity differs from the pinned v0.3 reference;
- `CAUSAL_INSTANT_MISMATCH` when sibling projections disagree on the same market instant; and
- `BUNDLE_VALIDATION_FAILURE` for other outer-bundle contract violations.

No failure artifact carries a sibling write action or production mutation instruction.

## Code map

- `src/prometheus_loop/adapters/nexus.py` — release pin, strict bundle validation, causal instant validation, quarantine binding.
- `src/prometheus_loop/adapters/siblings.py` — conservative sibling evidence normalization.
- `src/prometheus_loop/sentinel/failure.py` — immutable failure artifact constructors.
- `src/prometheus_loop/orchestration/loop.py` — `NexusRunInput` delegates to the existing loop.
- `tests/fixtures/nexus_v03_same_instant_bundle.json` — deterministic fixture generated from the recovered NEXUS v0.3 code path.

## When not to use this binding

Do not use the v0.2 binding when:

- the authoritative NEXUS release contract snapshot changes;
- `SiblingInstantBundle` changes fields or semantics;
- newly recovered authoritative sibling schemas contradict the current projection rules; or
- a caller needs live writes to AION or DAEDALUS, which this version intentionally does not implement.

**Stale when:** any authoritative sibling boundary or NEXUS same-instant contract changes.
