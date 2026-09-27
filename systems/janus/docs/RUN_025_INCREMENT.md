# JANUS ∞ Run 025 — Subprocess Crash Recovery + WAL Promotion Hardening

Run 025 hardens the Run 024 promotion journal against abrupt process death.

## Added
- `hard_crash_at` subprocess-only fault boundary for `after_prepare` and `after_promotion_backup` using immediate process termination.
- Prepared promotion intent is copied into the staging database before authoritative backup, so a process death after database promotion retains an unresolved durable journal.
- `recover_pending_promotions()` restart sweep resolves all prepared intents exactly once.
- SQLite `PRAGMA integrity_check` assertions after abrupt subprocess death.
- Post-prepare crash proves abort/no receipt; post-backup crash proves committed state by receipt presence and idempotent recovery certificate.

## Invariants
- No prepared-but-unpromoted crash invents a receipt.
- A promoted database containing its joint receipt is recovered as committed even if the process died before journal resolution.
- Recovery is idempotent.
- Existing authority boundaries remain unchanged.

## Scope boundary
This is local SQLite/WAL process-death evidence, not proof of distributed filesystem, disk-full, torn-sector, or live-repository behavior.
