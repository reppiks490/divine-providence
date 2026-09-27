# JANUS ∞ STATE CAPSULE — Run 031

## Checkpoint
Run 031: Independent Receiver Storage-Certificate Replay + Certificate Chain + Host FD Fault.

## Completed
- Fresh-receiver replay bundle with bundle-level SHA-256 closure.
- Staged replay of all JANUS tables and independent verification against the sender's certified DB/WAL/SHM evidence snapshot.
- Ed25519 storage-certificate chain entries with predecessor-chain continuity and deterministic deltas.
- Isolated kernel `RLIMIT_NOFILE` / `EMFILE` host-fault probe.
- Strengthened replay fixture to carry a non-empty project-state marker, proving receiver state actually changes during successful replay.

## Verification
- Run 030 inherited baseline before Run 031 mutation: 111/111 PASS; compileall PASS.
- Run 031 RED: 4/4 focused tests failed on missing APIs only.
- Final focused Run 031: 4/4 PASS.
- Final full suite: 115/115 PASS.
- `python -m compileall -q src tests`: PASS.

## Authority
JANUS remains limited to project-twin temporal truth/conflict/proof synchronization. No sibling authority absorbed. No live-repository reconciliation or commit identity claimed.

## Blockers / risks
True block-device power-loss, filesystem-wide ENOSPC, torn-sector, controller reorder, and distributed-filesystem semantics remain unverified. Live Icarus Git checkout remains unavailable to this checkpoint.

## Resume
Start Run 032 from this capsule/package. Reproduce full tests and compileall first. Next highest-value work: independent replay from a minimal object-addressed evidence graph (not whole-table snapshot), branch/fork semantics for certificate chains, and a real filesystem/container fault harness where safely available.
