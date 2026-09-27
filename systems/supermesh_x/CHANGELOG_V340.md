# SuperMesh-X v3.4.0

- Added versioned witness-policy epochs with explicit threshold and revocation state.
- Added TUF-style dual-threshold, exactly-one-epoch key/quorum rotation.
- Rejected duplicate public-key aliases to prevent quorum inflation.
- Bound RFC9162 checkpoint signatures to policy epoch/digest when using the additive epoch registry.
- Added crash-consistent hash-chained gossip journal with authenticated replay and stale-policy rejection for new entries.
- Added deterministic `supermesh-json-v1` Ed25519 cross-runtime signature vectors.
- Preserved v3.3 checkpoint/signature behavior for legacy registries and preserved all earlier artifacts.
