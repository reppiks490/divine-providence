# ADR 0003 — Normalize plugin execution evidence before research promotion

**Status:** Accepted
**Date:** 2026-09-25

## Context

PROMETHEUS already required every selected plugin to have a host execution record, but the record lived only inside `PluginAudit`. The Deep Research continuation identified the next gap: plugin execution needs durable provenance and contribution attribution before plugin-assisted research can be packaged for downstream review.

## Decision

Every selected plugin execution is normalized into a content-addressed `PluginExecutionEvidence` bound to the exact plugin descriptor hash. PROMETHEUS then creates a separate multi-dimensional `PluginContributionReport`. Only a complete engineering-pass run may emit a `ResearchPromotionPacket` with status `READY_FOR_DAEDALUS_REVIEW`.

PROMETHEUS does not store raw credentials or acquire plugin invocation authority. Contribution classes are not rankings. The promotion packet cannot represent DAEDALUS acceptance or production authorization.

## Alternatives rejected

- **Keep plugin use only inside the audit:** rejected because downstream lineage cannot independently reference one plugin execution.
- **Store raw plugin responses:** rejected because it expands sensitivity, storage, and replay semantics without being necessary for execution provenance.
- **Compute one plugin utility score:** rejected because the design explicitly avoids collapsing heterogeneous evidence into one truth metric.
- **Let engineering-pass imply promotion:** rejected because DAEDALUS owns scientific validation and promotion.

## Consequences

Research lineage becomes more explicit and auditable. The cost is a larger number of small immutable artifacts and the need to keep host attribution honest.

**Stale when:** the host provides signed plugin execution attestations, contribution becomes causally measurable, or DAEDALUS changes its review-ingress contract.
