# JANUS ∞ Run 028 — Full WAL Integrity + Post-Backup SIGKILL + Forensic Cross-Link

Run 028 continues Run 027 without changing sibling-system authority boundaries.

## Added
- `classify_storage_artifacts()` now follows SQLite's WAL file-format rules through header checksum, frame layout, per-frame salt equality, and rolling frame checksum validation. It reports the first invalid frame and separates header, layout, salt, and checksum failures.
- `hard_wait_at='after_promotion_backup'` exposes an external-process kill boundary after authoritative SQLite backup but before promotion-journal resolution. Restart recovery classifies the promotion as committed because the joint receipt is already present in the promoted database.
- `sign_forensic_proof_link()` / `verify_forensic_proof_link()` create an Ed25519-signed, content-addressed bridge from a signed storage-fault audit to the promotion recovery certificate, session receipt (when one exists), current receipt-chain head, and fencing epoch.

## WAL validation rules
The implementation follows the SQLite WAL format documented at https://sqlite.org/fileformat.html: 32-byte header; 24-byte frame headers; frame size `24 + page_size`; salt values copied from the WAL header; checksum byte order selected by the WAL magic; checksum words stored big-endian; and cumulative checksums computed across the WAL header followed by each frame's first 8 header bytes plus page data.

## Invariants
- A WAL with a valid header but corrupted page data is not classified as healthy merely because SQLite can ignore an invalid trailing frame.
- Diagnostic classification snapshots the WAL before opening SQLite so diagnosis does not erase the evidence it is trying to inspect.
- External death after authoritative backup but before journal resolution recovers as committed exactly when the promoted DB contains the matching joint receipt.
- A forensic proof link authenticates provenance and continuity only; its signer does not acquire semantic authority over NEXUS/AION/ARGUS/ATHENA/DAEDALUS/Icarus.
