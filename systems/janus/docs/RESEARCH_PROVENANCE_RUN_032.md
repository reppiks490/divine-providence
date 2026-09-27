# Run 032 Public Research Provenance

External research remained read-only and separate from JANUS truth/repository mutation.

| Claim used | Source | Use in Run 032 |
|---|---|---|
| SQLite WAL-mode persistent state can involve the main DB, WAL, and SHM files; WAL frames carry rolling checksums and recovery scans stop at the first invalid checksum. | SQLite `fileformat.html`, `walformat.html`, `wal.html` | Preserves the existing requirement that certified physical storage evidence includes DB/WAL/SHM and remains independently verified during replay. |
| `RLIMIT_FSIZE` limits the maximum file size a process may create; extending past the limit raises `SIGXFSZ`, and a handled signal causes the write/truncate call to fail with `EFBIG`. | Linux `getrlimit(2)` / man7 | Basis for the isolated kernel-enforced file-size fault probe. |

Public source locations:
- https://sqlite.org/fileformat.html
- https://sqlite.org/walformat.html
- https://sqlite.org/wal.html
- https://www.man7.org/linux/man-pages/man2/prlimit.2.html

No private file contents, credentials, proprietary repository material, or JANUS internal artifacts were sent to public retrieval.
