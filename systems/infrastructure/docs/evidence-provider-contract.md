# V8 Read-Only Attribution Evidence Provider Contract

V8 adds an evidence-acquisition boundary for V7 counterfactual attribution. It is intentionally read-only and has no mutation, authorization, promotion, rollback, or control-discovery method.

## Authority invariants

- The provider supplies observations; it grants no authority.
- Controls are caller-bound explicitly. The collector never discovers or selects a favorable control.
- Provider failure yields unusable attribution evidence and therefore no positive learning credit; it does not crash or authorize the infrastructure mutation path.
- Every mutation event returned inside the requested evidence window is carried forward as contamination evidence. Action fingerprints are not unique event identities and cannot suppress events.
- Protected-scope overlap is carried explicitly into the V7 contamination detector.
- Central Orchestration remains an external sibling contract. This module neither transports nor recovers proof envelopes.

## Current limitations

The included `InMemoryEvidenceProvider` is for deterministic tests/replay only. No production telemetry backend is claimed. There is no automatic control matching, distributed mutation event source, proof signature, or identity attestation.
