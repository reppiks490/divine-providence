# JANUS ∞ Run 029 — Review Record

Independent reviewer subagent: not available in this harness. No independent-review claim is made.

Direct Run 028→Run 029 diff review identified two important issues before final verification:

1. **SHM diagnostic ordering** — initial implementation read WAL before opening SQLite but read SHM afterward. Because SQLite may rebuild, truncate, or otherwise change transient WAL-index state on open, this conflicted with the forensic-preservation invariant. Fixed by snapshotting both `-wal` and `-shm` bytes before opening SQLite.
2. **Forensic DAG semantic closure** — initial verifier checked node digests/signatures and graph acyclicity but did not require every signed digest reference to be represented by its node and semantic edge. A RED test removed the audit node+edge and recomputed the outer DAG digest; verification incorrectly passed. Fixed with reference-closure enforcement across forensic-link, storage-audit, receipt, and prior-chain references.

Final evidence after those fixes: 108/108 tests pass, compileall passes, and 46 JSON schemas parse and pass Draft 2020-12 meta-schema validation.
