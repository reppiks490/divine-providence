# ADR 0004: Pin the NEXUS v1.15 path-independent sibling contract snapshot

Status: accepted (2026-09-26, Divine Providence consolidation). Extends ADR 0002.

## Context

ADR 0002 pinned the NEXUS v0.3 release snapshot `1119ef3d…` and was declared stale
"when NEXUS publishes a new authoritative sibling contract release or a
path-independent semantic contract identity replaces the current release pin".
Both happened:

- NEXUS v1.15 (iteration 32) is the canonical NEXUS in the monorepo. Against the v0.3
  baseline, its sibling boundaries show AION contracts/store, ARGUS contracts and
  ATHENA contracts **byte-identical**. The DAEDALUS bridge changed **additively only**:
  166 lines added (the `nexus.daedalus-validation-handoff.v1` receiver), none removed
  or modified. `SCHEMA_VERSION` and `export_candidate`, which shape the bundle's
  DAEDALUS payload, are unchanged.
- NEXUS `ContractDriftSnapshot.capture(..., relative_to=...)` now records repo-relative
  paths. The snapshot `systems/nexus/contracts/baselines/sibling_contract_drift_baseline.v1.15.monorepo.json`
  has identity `b394df6cf80ddbac014f4024222469b169178fadd7c26f4a597aed58671b5bb3`
  and embeds no machine-specific path.

Before this change PROMETHEUS correctly quarantined every fresh NEXUS bundle as
`CONTRACT_DRIFT`.

## Decision

- Add `NEXUS_V115_CONTRACT_SNAPSHOT_HASH` and bind under the pinned set
  `{v0.3, v1.15}`. `CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH` is v1.15.
- Keep v0.3 accepted **only** for recorded historical bundles
  (`HISTORICAL_V03_BUNDLE_HASHES`, today the recovered v0.3 same-instant bundle). A new bundle
  presented under the v0.3 identity is refused, so provenance can never record a fresh bundle
  against the historical contract.
- Drift failures report the current pin as the expected identity.
- The identity is still externally supplied (ADR 0002). The Divine Providence hub supplies it
  only when NEXUS's own drift comparison against that recorded baseline shows no semantic drift.

## Consequences

- Fresh NEXUS v1.15 bundles bind and normalize (`tests/test_nexus_v115_pin.py`). Unpinned
  identities are still quarantined, and `production_authorized=True` is still rejected.
- Any further **semantic** change to a sibling boundary produces drift against the v1.15
  baseline and quarantines input again until a new baseline is reviewed and pinned by a new
  ADR. A byte change that leaves the AST unchanged (comments, formatting) is reported as
  `nonsemantic_change` and does not quarantine input.
- PROMETHEUS still imports no sibling code at runtime.

**Stale when:** a sibling boundary file changes semantically, or NEXUS publishes a new
authoritative contract release.
