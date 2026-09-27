# Change Record — PROMETHEUS v0.4 Lineage + Diagnosis

**Date:** 2026-09-25
**Actor:** ChatGPT / PROMETHEUS build session
**Request:** Continue PROMETHEUS work from the verified v0.3 checkpoint.

## Before

v0.3 could detect typed disagreement, generate research hypotheses, preserve plugin execution evidence, and emit lineage-unbound `READY_FOR_DAEDALUS_REVIEW` packets. It did not classify likely disagreement causes or mark historical research stale when a contract fingerprint changed.

## Change

- added deterministic `DisagreementCause` / `DisagreementDiagnosis` artifacts;
- added conservative disagreement-cause precedence with explicit ambiguity fallback;
- added immutable `ResearchLineageManifest` artifacts;
- added `StaleEvidenceReport` contract-fingerprint checks;
- bound selected plugin descriptor IDs and NEXUS contract identity into lineage;
- persisted diagnoses, lineage and staleness artifacts through the existing research memory;
- made DAEDALUS review packets require a clean lineage manifest;
- stale lineage now suppresses DAEDALUS review handoff;
- updated package metadata and CLI fixture wording to v0.4.
- final review hardened contract provenance: conflicting explicit plugin fingerprints now fail closed, and duplicate current-contract overrides are rejected rather than resolved by last-write-wins.
- final review also binds every staleness report to the exact lineage manifest being considered for DAEDALUS review, rejecting cross-lineage substitution.

## Research/runtime capability record

The requested Deep Research capability was not exposed in this run and was therefore not claimed as invoked. The build used installed Exa, Tavily, and Firecrawl research surfaces for external architecture cross-checks. Local Python continues to model host plugin evidence only; it does not simulate connector execution.

## Authority impact

No production authority was added. NEXUS, AION, ARGUS, ATHENA, DAEDALUS and Icarus ownership boundaries remain unchanged. AION/DAEDALUS remain external systems; v0.4 adds no write connector to either.

## When not to use the diagnosis as truth

Diagnosis is a deterministic research label, not proof of causation. `IRREDUCIBLE_AMBIGUITY` is the required fallback when evidence does not justify a narrower explanation.

**Stale when:** contract-fingerprint semantics, disagreement taxonomy, or sibling authority boundaries change.
