# JANUS ∞ Architecture Increment — Run 031

Run 031 extends Run 030's signed storage-state certificate with independent receiver replay and signed certificate-chain deltas while preserving JANUS's project-twin temporal truth/conflict/proof synchronization boundary.

## Added interfaces
- `build_receiver_replay_bundle()` exports content-addressed table/proof/storage evidence.
- `import_and_verify_receiver_replay_bundle()` verifies bundle digest and certificate signature, reconstructs state in an isolated stage, verifies the certified storage snapshot and forensic closure, then promotes only after verification.
- `build_storage_certificate_chain_entry()` and `verify_storage_certificate_chain[_entry]()` bind predecessor certificate, predecessor chain digest, deterministic state deltas, and Ed25519 authority.
- `run_host_fd_exhaustion_probe()` uses child-process `RLIMIT_NOFILE` to exercise a real `EMFILE` kernel failure without touching authoritative storage.

## Integrity rulings
The replay evidence snapshot is verified separately from the reconstructed receiver database: reconstruction writes necessarily alter SQLite physical bytes, while the certificate attests the original certified physical snapshot. Project/proof state must reproduce in the stage, and the certified DB/WAL/SHM bytes remain separately content-addressed and non-mutating.

Replay promotion is fail-closed: malformed bundle digest, invalid certificate signature, failed forensic/storage closure, or reconstructed project-state mismatch prevents authoritative receiver promotion.
