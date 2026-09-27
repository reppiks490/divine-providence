# ADR 0002 — Pin the recovered NEXUS v0.3 sibling contract

**Date:** 2026-09-24  
**Status:** accepted

## Context

PROMETHEUS needs a real sibling input without taking a runtime dependency on NEXUS, AION, ARGUS, ATHENA, or DAEDALUS source trees. The recovered NEXUS v0.3 handoff already contains a validated same-instant sibling bundle and release-time boundary fingerprints.

The release artifacts identify sibling-contract snapshot `1119ef3d9b561dc89668a9768893a2b1ab09cd542ffd1d7a02dd73f5a81388a2`. A later path-bearing snapshot has a different aggregate hash because absolute paths changed, while the NEXUS drift report shows every raw and AST boundary fingerprint unchanged.

## Decision

PROMETHEUS pins the NEXUS v0.3 **release snapshot identity** and treats it as an externally supplied contract identity. It validates the recovered `SiblingInstantBundle` shape and normalizes explicit sibling payload fields into PROMETHEUS observations.

PROMETHEUS does not import sibling repositories at runtime and does not recompute the aggregate release snapshot hash from local paths.

## Alternatives rejected

1. **Runtime-import NEXUS/sibling code.** Rejected because it couples research execution to sibling filesystem layout and risks authority leakage.
2. **Accept any structurally similar bundle.** Rejected because semantic contract drift could silently enter research history.
3. **Recompute the aggregate snapshot hash locally.** Rejected because the NEXUS snapshot includes absolute paths, making the aggregate identity environment-dependent even when raw/semantic fingerprints are unchanged.
4. **Infer missing sibling semantics.** Rejected because direction, regime, risk, confidence, and execution meaning belong to authoritative sibling contracts.

## Consequences

The binding is portable and fail-closed, but it must be refreshed when the authoritative release identity or bundle semantics change. Contract drift becomes a research failure artifact rather than a best-effort parse.

**Stale when:** NEXUS publishes a new authoritative sibling contract release or a path-independent semantic contract identity replaces the current release pin.
