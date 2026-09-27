# PROMETHEUS v0.4 — Lineage and Disagreement Diagnosis

PROMETHEUS v0.4 adds two research-safety surfaces to the existing loop: deterministic disagreement diagnosis and append-only research lineage with contract-staleness detection.

## Disagreement diagnosis

`sentinel/diagnosis.py` classifies a `DisagreementCase` only from evidence already present in the case and its `ObservationEnvelope` participants. The precedence is intentionally conservative:

1. differing availability state -> `AVAILABILITY_MISMATCH`;
2. `source_health:*` dimension -> `SOURCE_HEALTH_ISSUE`;
3. `representation:*` dimension -> `REPRESENTATION_MISMATCH`;
4. `regime` / `regime:*` -> `REGIME_BOUNDARY`;
5. known sibling-role fields such as contract/data-plane/purpose/status -> `INTENTIONAL_SPECIALIZATION`;
6. shared NEXUS `factor:*`, `quality:*`, or `ood:*` disagreement -> `EVIDENCE_MISMATCH`;
7. everything else -> `IRREDUCIBLE_AMBIGUITY`.

The classifier does not infer `MODEL_BLIND_SPOT` without stronger model-specific evidence. Healthy specialization is allowed to remain disagreement.

## Append-only lineage

`ResearchLineageManifest` records:

- the root research artifact;
- every content-addressed artifact participating in the result;
- predecessor artifacts representing the causal research chain; and
- the exact contract/plugin fingerprints used by the run.

The manifest is immutable and content-addressed. Input ordering and duplicate artifact IDs are canonicalized before identity is computed.

`StaleEvidenceReport` compares a historical manifest to current contract fingerprints. A changed or missing dependency marks the lineage stale by creating a new report. The original lineage ID never changes.

## Promotion boundary

`ResearchPromotionPacket` is now lineage-bound. A packet can be created only when:

- the top-level run is `RESEARCH_COMPLETE`;
- the result is `PROMETHEUS_ENGINEERING_PASS`;
- the lineage has a concrete manifest ID; and
- the staleness report is clean.

In the unified v0.5 build the packet must additionally carry the provenance-attestation binding (`ResearchProvenanceManifest` plus a complete `ProvenanceLineageReport`, see `plugin-evidence-and-promotion.md`). That provenance-ancestry verifier lives in `prometheus_loop.provenance_lineage`; the stale-aware lineage described here lives in `prometheus_loop.lineage`. The two are complementary and neither substitutes for the other.

A stale lineage emits no DAEDALUS review packet. This remains a research handoff only; `production_authorized=True` is still rejected by construction.

## Contract fingerprints

For ordinary runs, callers may provide explicit sibling/service contract fingerprints. Selected plugin descriptor IDs are automatically added as `plugin:<plugin_id>` contract dependencies.

For `NexusRunInput`, PROMETHEUS automatically binds the pinned NEXUS v0.3 contract snapshot hash. Optional current-fingerprint overrides can mark a run stale at handoff time without altering the historical manifest.

## External research used for this design

The design was cross-checked against provenance and event-lineage patterns from W3C PROV, OpenTelemetry, CloudEvents, and mature data-lineage systems. The implementation deliberately stays much smaller: no external lineage database, broker, or production service is introduced.

**Stale when:** disagreement taxonomy, NEXUS payload semantics, plugin descriptor hashing, lineage identity rules, or DAEDALUS review-ingress requirements change.
