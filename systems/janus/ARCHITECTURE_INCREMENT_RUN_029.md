# JANUS ∞ Run 029 — SHM/WAL Consistency + Kernel Fault Probe + Unified Forensic DAG

Run 029 continues Run 028 without widening JANUS authority.

## Added
- `_classify_shm_bytes()` validates the transient SQLite WAL-index (`-shm`) against the already verified WAL: 32 KiB unit layout, duplicate 48-byte header copies, native-endian header checksum, page size, checksum byte-order flag, salt copy, `mxFrame`, last committed WAL checksum, backfill bounds, and `aPgno` frame-to-page mapping.
- `classify_storage_artifacts()` now snapshots and classifies WAL and SHM before opening SQLite, preserving forensic evidence from diagnostic side effects.
- `run_host_storage_fault_probe()` executes an isolated child process with a kernel-enforced `RLIMIT_FSIZE`; exceeding the limit yields the real host error `EFBIG` rather than a Python-synthesized storage exception. The probe is scratch-only and never points at authoritative JANUS state.
- `build_forensic_proof_dag()` / `verify_forensic_proof_dag()` unify forensic proof links, signed storage-fault audits, quarantine evidence, promotion recovery certificates, and referenced receipt-chain nodes into one content-addressed acyclic evidence graph.

## SQLite consistency rules
Run 029 follows SQLite's WAL-index documentation for Unix/Windows VFSes: the SHM file is transient shared memory persisted through a memory-mapped file, is normally a multiple of 32768 bytes, begins with two copies of the 48-byte WAL-index information header, stores most integers in native byte order, copies WAL salts byte-for-byte, records the committed WAL horizon in `mxFrame`, and maps WAL frame page numbers through the `aPgno` array.

## Invariants
- SHM absence is not itself a corruption finding because SQLite can reconstruct the WAL-index and can omit it in exclusive locking mode.
- A present SHM is accepted as consistent only when its durable-facing horizon agrees with the independently verified WAL.
- A kernel fault probe cannot mutate the authoritative project twin.
- The unified forensic DAG is provenance/integrity evidence only. Its signatures do not grant the signer semantic authority over NEXUS/AION/ARGUS/ATHENA/DAEDALUS/Icarus.
