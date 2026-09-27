# Plugin Evidence and Research Promotion

PROMETHEUS v0.4 turns host plugin execution records into immutable research evidence and binds every eligible DAEDALUS review handoff to a deterministic provenance manifest.

## Evidence boundary

The ChatGPT host remains responsible for discovering and invoking plugins. Selection records the exact `PluginDescriptor.descriptor_id`; evidence normalization rejects any same-ID descriptor drift between selection and normalization. PROMETHEUS receives only a typed execution record and normalizes it into `PluginExecutionEvidence` containing:

- loop run ID;
- plugin ID;
- exact `PluginDescriptor.descriptor_id` content hash;
- execution status;
- input fingerprint;
- output fingerprint and/or external result reference for completed executions;
- failure class for failed executions; and
- explicit contributed artifact IDs, when the host can attribute them.

Each selected plugin maps to one unambiguous host execution record; duplicate same-plugin host records fail closed. Raw plugin responses, OAuth material, API keys, cookies, and other credentials are intentionally absent. The evidence artifact proves what execution record PROMETHEUS received; it does not prove that the plugin's claims are true.

**When not to use this artifact:** do not treat it as a credential store, raw research archive, or source-quality verdict. Fetch/revalidate the original external evidence when the research question requires its actual contents.

**Stale when:** the host execution contract changes, plugin descriptor semantics change, or a future host supplies a stronger signed execution attestation.

## Contribution semantics

`PluginContributionReport` classifies attribution without producing a single ranking score:

- `UNIQUE` — all explicitly attributed artifacts appear only in this plugin's evidence;
- `SHARED` — all attributed artifacts are also attributed to one or more other plugins;
- `UNIQUE_AND_SHARED` — both kinds are present;
- `NO_ATTRIBUTED_ARTIFACTS` — the execution completed but the host did not attribute local research artifacts; and
- `FAILED` — the host execution failed.

Duplicate artifact IDs inside one plugin are de-duplicated before overlap classification, so only attribution from distinct plugins can create `SHARED`. Counts are bookkeeping, not truth. A unique artifact may be wrong; a shared artifact may be high-value corroboration. PROMETHEUS records the structure and leaves scientific validity to the research/replay/adversarial path.

**When not to use this report:** never use contribution class as a proxy for accuracy, source quality, trading edge, or plugin ranking.

**Stale when:** PROMETHEUS gains causal contribution measurement rather than host-declared artifact attribution.

## Provenance manifest

Before an eligible engineering-pass candidate can be handed to DAEDALUS, PROMETHEUS builds `ResearchProvenanceManifest`. The manifest content-addresses the exact loop run, experiment, candidate, selected plugin descriptor identities, normalized plugin-evidence identities, contribution-report identities, observation identities, source/sibling contract identities, and any explicit parent manifest lineage. Identifier collections are canonicalized for deterministic hashing but duplicate or wrong-namespace identifiers fail closed.

For NEXUS-backed runs, the validated release contract snapshot is recorded as a `nexus-contract:<sha256>` source-contract identity. PROMETHEUS does not recompute or reinterpret NEXUS authority; it records the already validated contract identity.

The manifest follows the general provenance principle of binding immutable metadata to the exact artifact/run it describes. It is not a signed host attestation, does not prove external source truth, and contains no raw plugin bodies, credentials, cookies, tokens, or broker state.

**When not to use this artifact:** do not treat its hash as a signature, source-quality score, DAEDALUS acceptance, or proof that a plugin actually executed outside the host record already normalized by PROMETHEUS.

**Stale when:** artifact ID namespaces, loop identity inputs, source-contract semantics, or a future signed host-execution attestation contract changes.

## DAEDALUS review boundary

A successful PROMETHEUS engineering candidate may be wrapped in `ResearchPromotionPacket` only when:

1. the top-level run is `RESEARCH_COMPLETE`;
2. the result is a `CandidateImprovement`;
3. its status is `PROMETHEUS_ENGINEERING_PASS`;
4. the stale-aware `ResearchLineageManifest` is concrete and its `StaleEvidenceReport` is clean and bound to that exact manifest (see `lineage-and-diagnosis.md`); and
5. the current `ResearchProvenanceManifest` matches the live run and has a complete `ProvenanceLineageReport` whose tip is that manifest.

The packet target is fixed to `DAEDALUS`, its only status is `READY_FOR_DAEDALUS_REVIEW`, and `production_authorized` is structurally fixed false. The packet must carry `lineage_manifest_id`, `provenance_manifest_id`, and `provenance_lineage_report_id`, include the provenance manifest and lineage report in its evidence set, and the builder rejects any mismatch between the manifest and the current loop/candidate/experiment/plugin/observation/source-contract/attestation lineage. Neither binding substitutes for the other. Degraded, stale-lineage, deferred/abstained, and rejected runs produce no packet or promotion-bound provenance manifest.

This packet is a handoff request, not a promotion decision. DAEDALUS still owns protected evidence, statistical validation, and any later production-promotion decision; Icarus still owns production execution.

**When not to use this packet:** do not interpret its existence as DAEDALUS acceptance, production readiness, predictive edge, or authorization to change a sibling system.

**Stale when:** DAEDALUS publishes a new authoritative review-ingress contract or the ecosystem authority map changes.
