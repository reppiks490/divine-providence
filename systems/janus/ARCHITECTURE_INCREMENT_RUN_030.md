# JANUS ∞ Run 030 — Signed Storage-State Certificate + Host Permission Fault + Live Reconciliation Gate

Run 030 continues Run 029 without widening JANUS authority.

## Added
- `build_storage_state_certificate()` emits a non-self-mutating Ed25519-signed certificate binding the logical project-state digest, portable main-DB/WAL/SHM state, session fencing epoch, current receipt-chain head, promotion recovery certificate, session quarantine closure, and optional unified forensic DAG root/digest.
- `verify_storage_state_certificate()` replays the certificate digest/signature and compares the attested state against the receiver's actual project state, recovery/journal/receipt/quarantine closure, forensic DAG, and observed DB/WAL/SHM state.
- `_portable_storage_summary()` removes host-specific paths from storage evidence while retaining file hashes, integrity classifications, WAL horizon/checksum/salt state, and SHM horizon/backfill/frame-map state.
- `run_host_permission_fault_probe()` adds a second real kernel-enforced host-fault class. The probe attempts to write a mode-0444 scratch file; when the harness runs as root the child drops to an unprivileged UID/GID first, so the failure is a genuine kernel `EACCES`/permission denial rather than a Python-synthesized exception.
- `live_reconciliation_gate()` refuses READY_TO_COMMIT unless the supplied location is a Git worktree with a resolvable HEAD, a clean worktree, and an explicit set of expected artifact hashes that all match. Missing repos, missing expected hashes, dirty worktrees, path escapes, missing files, and hash mismatches all fail closed.

## Certificate law
The storage-state certificate is not inserted back into the SQLite database it attests. Persisting the certificate inside that same database would change the database hash and create a self-invalidating proof. The signed certificate therefore travels as an external proof artifact.

When a forensic DAG is supplied, its root forensic link must bind the same session, recovery certificate, receipt head, and quarantine evidence as the storage-state certificate. A valid but unrelated forensic DAG is not accepted as proof closure.

## Ownership
These mechanisms attest storage/proof continuity only. A JANUS signature proves provenance/integrity of the certificate; it does not grant JANUS semantic authority over NEXUS/AION/ARGUS/ATHENA/DAEDALUS/Icarus.
