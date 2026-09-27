# JANUS ∞ Run 022 — Fenced Promotion, Receipt-Fork Detection, Crash-Recovery Proof

Run 022 strengthens the Run 021 synchronization control plane without expanding JANUS ownership.

## New invariants
- Promotion fencing epochs are monotonically increasing and single-writer: any newer acquired epoch invalidates an older writer.
- Each promotion guard captures the accepted receipt head; promotion fails if the head changes before commit.
- The fencing epoch and expected receipt head are bound into the joint proof receipt.
- A pre-promotion crash/failure leaves project-domain truth unchanged; durable verified chunk inventory is reusable on retry.
- NEXUS/AION/ARGUS/ATHENA/DAEDALUS/Icarus semantic authority remains external and explicit; fencing controls synchronization concurrency only.

## Interfaces
- `acquire_promotion_fence(session_id)`
- `assert_promotion_guard(session_id)`
- `atomic_joint_sync(..., crash_at="before_promotion")` test hook

## Limits
This is SQLite/offline proof. It is not a distributed lease service and has not been reconciled with the live Icarus repository. Crash injection is deterministic in-process failure injection, not OS kill/WAL corruption testing.
