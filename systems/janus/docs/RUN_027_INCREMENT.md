# JANUS ∞ Run 027 — External SIGKILL + WAL Classification + Signed Storage-Fault Audit

Run 027 extends Run 026 without changing sibling-system authority boundaries.

## Added
- External parent-issued SIGKILL verification at the prepared-promotion boundary via a deliberate wait hook used only by crash tests.
- `classify_storage_artifacts(db_path)`: snapshots WAL/SHM evidence before opening SQLite, classifies invalid WAL headers, and records content hashes plus main DB integrity.
- `sign_storage_fault_evidence(...)` / `verify_storage_fault_audit(...)`: Ed25519 domain-separated, hash-chained forensic audit records anchored to Run 026 quarantine evidence.

## Invariants
- External process death after prepare creates no receipt and recovers as aborted.
- Diagnostic opening of SQLite must not destroy the only WAL evidence before classification.
- Audit signing authenticates forensic provenance only; it does not grant semantic authority over NEXUS/AION/ARGUS/ATHENA/DAEDALUS/Icarus.
