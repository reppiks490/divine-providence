# JANUS ∞ Run 002 — Bitemporal Reconstruction Gate

## Built
- Added `JanusTwin.facts_as_of(valid_at, known_at)`.
- `current_facts(valid_at=...)` now honors explicit validity expiration.
- Supersession is applied only within the eligible bitemporal slice.
- Added two regression tests for late-known facts and expired facts.

## Why
The project twin already stored `valid_from`, `valid_to`, and `known_at`, but its authoritative query did not expose a two-clock reconstruction. That left a gap between the stated temporal-truth model and executable behavior. This increment closes that gap without changing sibling-system authority.

## Verification
See `docs/TEST_REPORT_RUN_002.txt`. This package remains an offline handoff artifact; no live Icarus/GitHub integration is claimed.
