# ASCENSION Sibling Manifest Conformance Kit v0.1

**Lifecycle: CANDIDATE.** This kit is a non-authoritative, read-only transfer-preparation capability. It does not sign artifacts, verify cryptography, create sibling authority, or claim successful Transfer.

## Purpose

The kit attacks ASCENSION's current bottleneck: sibling systems may have strong provenance/attestation contracts but still lack a complete export package that Adapter v0.4 can actually verify. The kit separates three states:

- `NONCONFORMANT`: required structural identity/authority fields are missing or contradictory.
- `STRUCTURALLY_CONFORMANT`: the sibling-owned descriptor and external-verification receipt are structurally complete, but Adapter v0.4 material is absent/incomplete.
- `ADAPTER_READY_UNVERIFIED`: all documented Adapter v0.4 input layers are present and pinned structurally. **This is still not authenticated.** Adapter/Evaluator execution is required next.

`authenticated` is always `false` in this kit by design.

## Main interfaces

- `validate_export(export)` — validates structural conformance and Adapter v0.4 input readiness without performing cryptographic authentication.
- `build_handoff_checklist(sibling_id)` — generates a deterministic authority-handoff checklist for a sibling owner.
- `prometheus_v0_5_declared_profile()` — records the PROMETHEUS v0.5 declared attestation contract as `DECLARED_CONTRACT`; it is explicitly not runtime evidence.

## Target verification chain

`Sibling authority -> signed runtime export -> Conformance Kit -> Adapter v0.4 -> Evaluator trust/v0.8 inclusion/v0.7 transition+witness -> Collision Detector v0.3`

The Conformance Kit stops before cryptographic trust evaluation.

## Important boundary

A sibling owner or its authorized verifier must supply the signed/verified material. ASCENSION must not manufacture a sibling signature, trust root, verification receipt, or authority identity merely to make the package conform.

## Verification

See `test_report.json` and `failure_injection_report.json`. The package must be re-tested from exact clean extraction before any runnable-package claim.
