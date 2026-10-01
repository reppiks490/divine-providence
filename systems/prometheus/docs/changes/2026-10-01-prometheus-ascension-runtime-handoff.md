# PROMETHEUS -> ASCENSION runtime handoff bridge

## Purpose

PROMETHEUS can now export exact runtime provenance bytes plus the already
recorded external-attestation descriptor and external-verifier receipt in the
structural shape consumed by ASCENSION Sibling Manifest Conformance Kit v0.1.

The bridge is deliberately read-only and fail-closed.

## What is now transferable

For a concrete `ResearchProvenanceManifest` created under
`PluginAttestationPolicy.REQUIRE_VERIFIED`, PROMETHEUS can emit one export per
bound plugin-evidence item containing:

- exact canonical bytes of the runtime provenance manifest;
- SHA-256 bound to those exact bytes;
- a durable research-memory content reference;
- the exact stored `ExternalExecutionAttestation` descriptor;
- the exact stored `AttestationVerificationReceipt`;
- exact PROMETHEUS provenance/attestation IDs and source-contract ancestry;
- explicit nonclaims for authentication, Transfer, production, and execution.

The exporter revalidates runtime content hashes, content-addressed IDs,
attestation-to-plugin-evidence binding, receipt-to-attestation binding, and all
mandatory receipt checks before emitting anything.

## ASCENSION boundary

This closes the prior raw-runtime-manifest and transferable-artifact-byte gap
for strict-attested PROMETHEUS provenance. It does **not** supply or invent:

- an ASCENSION-authorized trust policy;
- raw private signing keys or credentials;
- a new cryptographic signature;
- v0.8 strict inclusion proof;
- v0.7 consistency transition / independent witness evidence;
- a Collision Detector verdict;
- an Adapter v0.4 backend authority decision.

Accordingly, the export intentionally omits `adapter_v0_4_evidence`. The
current ASCENSION v0.1 conformance kit must classify it
`STRUCTURALLY_CONFORMANT`, never `ADAPTER_READY_UNVERIFIED` or
authenticated.

## Authority

PROMETHEUS remains research-only. DAEDALUS review authority, ASCENSION trust
verification, and ICARUS production execution authority are unchanged.
