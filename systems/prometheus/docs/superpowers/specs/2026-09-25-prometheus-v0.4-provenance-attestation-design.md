# PROMETHEUS v0.4 — Provenance Attestation Design

**Date:** 2026-09-25  
**Status:** approved in chat for implementation  
**Scope:** research-only provenance binding for the DAEDALUS review boundary

## Purpose

PROMETHEUS v0.4 makes a `READY_FOR_DAEDALUS_REVIEW` handoff replayable and tamper-evident at the application-contract level. A review packet must identify one immutable manifest that binds the exact PROMETHEUS loop run to the candidate, experiment, source observations, selected plugin descriptors, normalized plugin execution evidence, plugin contribution reports, source/sibling contract identities, and any explicit parent provenance manifests.

The manifest is content-addressed with the existing deterministic `content_id` mechanism. It is an application-level provenance record, not a cryptographic signature or claim that the host/plugin itself was independently attested.

## Hard authority boundaries

- PROMETHEUS remains research-only.
- `production_authorized` remains structurally false.
- DAEDALUS alone owns protected validation and later promotion/acceptance.
- NEXUS remains authoritative for causal market identity and sibling contract identity.
- No runtime import or write dependency on sibling repositories is added.
- Raw plugin response bodies, credentials, cookies, tokens, and secrets are excluded.
- Host execution fingerprints/references remain evidence that PROMETHEUS received a record, not proof that external claims are true.

## Contract

Add immutable `ResearchProvenanceManifest` with:

- `loop_run_id`
- `experiment_id`
- `candidate_id`
- `selected_plugin_descriptor_ids`
- `plugin_evidence_ids`
- `plugin_contribution_ids`
- `observation_ids`
- `source_contract_ids`
- `parent_manifest_ids`

All identifier collections are canonical, duplicate-free tuples. Required identifiers must be non-empty. The manifest exposes a deterministic `artifact_id` with prefix `research-provenance:`.

## Promotion gate

`ResearchPromotionPacket` gains `provenance_manifest_id`. The packet constructor requires that identifier and requires it to be included in `evidence_ids`.

The promotion builder must fail closed when the supplied manifest does not exactly match the current:

- loop run;
- candidate and experiment;
- selected plugin descriptors;
- plugin execution evidence IDs;
- contribution report IDs;
- observation IDs; or
- source contract IDs.

A degraded run, rejected hypothesis, or non-engineering-pass candidate still produces no review packet.

## Orchestration

`RunInput` accepts explicit `source_contract_ids` and `parent_manifest_ids`, both empty by default. These identities become part of the deterministic loop-run identity.

`NexusRunInput` carries optional parent lineage and automatically binds the validated NEXUS contract snapshot identity into `source_contract_ids` before delegating to `run`.

For a promotion-eligible result, the loop builds and persists the provenance manifest before building the review packet. `LoopRunResult` exposes `provenance_manifest_id`; non-promoted/reused-negative paths expose `None`.

## Threat model / fail-closed cases

The implementation must reject:

1. duplicate identifiers inside a provenance collection;
2. malformed or empty required identities;
3. stale manifests from another loop run;
4. manifests binding a different candidate or experiment;
5. descriptor/evidence/contribution/observation/source-contract drift;
6. promotion packets that omit or disagree with their provenance manifest; and
7. any attempt to set production authorization true.

## Verification

TDD must cover deterministic IDs, canonical ordering, duplicate rejection, stale/tampered manifest rejection, NEXUS source-contract binding, end-to-end persistence, degraded/rejected behavior, and the pre-existing production-authority negative test.

Final gates: compileall, full pytest suite, deterministic CLI/demo, production-authority literal scan, broker/credential scan, sibling runtime-import scan, bytecode scan, and `git diff --check`.
