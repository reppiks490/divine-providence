# Icarus/JANUS STATE CAPSULE — Run 025

- Authoritative offline checkpoint: JANUS ∞ Run 025
- Parent: Run 024 package `b457eeddba1fb6eca71286198a36eda8043ea60887c0f326b0527bb2178963ef`
- Completed: subprocess hard-crash fault injection at post-prepare and post-authoritative-backup boundaries; staging-carried prepared promotion journal; SQLite/WAL integrity verification after abrupt death; restart commit/abort inference; idempotent pending-promotion recovery sweep.
- Verification: inherited Run 024 93/93 passed before mutation; Run 025 tests were RED before APIs/hooks; final full suite 96/96 passed; `python -m compileall -q src tests` passed.
- Key interfaces: `atomic_joint_sync(..., hard_crash_at=...)`, `recover_pending_promotions()`; existing `recover_promotion()` remains certificate source.
- Dependency: Python stdlib + `cryptography>=41`; SQLite WAL.
- Ownership: JANUS remains limited to project-twin temporal truth/conflict/proof synchronization. No NEXUS/AION/ARGUS/ATHENA/DAEDALUS/Icarus authority absorption.
- Live repo: not reconciled; no commit ID claimed.
- Remaining risks: disk-full/I/O error matrix, torn/corrupt staging artifacts, distributed filesystem semantics, external time authority, live-repo parity.
- Tools actually used: capability discovery, Plugin Management search for exact Deep Research, Superpowers skills, Baton Pass skill, Codex Coordinator skill, Akinator skill, container/Python/pytest/compileall/SQLite, Files persistence attempt.
- Deep Research: exact first-party capability not exposed; ACTUALLY INVOKED=NO / UNAVAILABLE.
- Resume: verify package hash, extract, run `PYTHONPATH=src python -m pytest -q` and `python -m compileall -q src tests`; continue with Run 026 storage-fault matrix + corrupt-stage quarantine + transactional recovery audit, without changing sibling authority boundaries.
