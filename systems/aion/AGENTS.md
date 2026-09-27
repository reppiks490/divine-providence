# AION instructions for every model and contributor

1. Read `README.md`, `docs/CURRENT.md`, `docs/DECISIONS/ADR-0001.md`, `docs/INTEGRATION.md`, then the relevant `docs/CODE_ATLAS/` entry. `docs/CURRENT.md` is the turn state; verify it against git before acting.
2. Keep AION a sibling of Icarus, DAEDALUS, ATHENA, and ARGUS. AION has research/shadow authority only. Do not add broker endpoints, order routing, implicit model promotion, or automatic holdout spending.
3. Preserve source file SHA-256, instrument/contract, representation identity, original row position or venue sequence, event/publish/availability/ingestion clocks, revisions, evidence tier, and source quality. Never sort away repeated timestamps or infer chart mechanics from an ambiguous filename.
4. A candle may support price structure and a **labeled hypothesis**. It cannot become an authenticated trade, queue, book, or order-flow record. Require real source evidence and review for higher tiers. Synthetic scenes must stay visibly synthetic in every export and UI.
5. An as-of feature requires verified availability at or before decision time. A scheduled release can be known in advance; its actual figure and surprise cannot. Higher-timeframe bars and pivots wait for their true confirmation boundary.
6. Freeze predictions and their cited source hashes before outcomes. Settlement is append-only. Protected DAEDALUS holdouts remain in DAEDALUS; AION may reference an authorized status, never enumerate protected outcomes for selection.
7. Every change must update `docs/CURRENT.md` with exact files, commands/tests and unresolved risks, and add a dated ADR if an interface or scientific rule changed. Record source repo commit hashes in `docs/CODE_ATLAS/` after verifying them. Do not claim the current Claude working tree was reviewed from an archived handoff.
8. Review the change against failure modes: future-data access, sequence gaps/recovery, revisions, duplicate identity, repeated timestamps, synthetic evidence labels, scenario-vs-empirical labeling, settlement immutability, and a broker-free export.
9. The cockpit binds `127.0.0.1`, serves read-only routes, and does not collect provider credentials. Keep raw licensed data and secrets outside git.

This is the canonical shared instruction. `CLAUDE.md` points here; sibling repos should carry a short, version-pinned pointer to this repo after their owners review the integration.
