# PROMETHEUS v0.4 — Provenance Attestation

PROMETHEUS v0.4 hardens the research-only handoff into DAEDALUS by requiring a deterministic, immutable provenance manifest for every `READY_FOR_DAEDALUS_REVIEW` packet.

## Added

- `ResearchProvenanceManifest` with content-addressed `research-provenance:` identity.
- Exact binding of loop run, experiment, candidate, selected plugin descriptors, plugin execution evidence, plugin contribution reports, observations, source contracts, and parent manifest lineage.
- Canonical tuple ordering with duplicate rejection.
- Identifier namespace validation to prevent cross-artifact type confusion.
- `provenance_manifest_id` on `ResearchPromotionPacket`, required in the packet evidence set.
- Fail-closed promotion validation for stale/tampered manifest fields.
- `source_contract_ids` and `parent_manifest_ids` in orchestration lineage and deterministic loop identity.
- Automatic `nexus-contract:<snapshot-hash>` binding for validated NEXUS runs.

## Preserved boundaries

- PROMETHEUS still cannot authorize production.
- DAEDALUS acceptance and protected statistical validation remain external.
- NEXUS remains authoritative for causal/sibling contract identity.
- No sibling runtime imports or writes were added.
- No broker/order path was added.
- Raw plugin bodies and credentials remain outside research artifacts.
- A content hash is not represented as a host/plugin cryptographic signature.

## Behavioral result

An engineering-pass candidate is handoff-eligible only when its provenance manifest exactly matches the evidence being handed to DAEDALUS. Any loop/candidate/experiment/descriptor/evidence/contribution/observation/source-contract/parent-lineage mismatch raises before a packet is created.
