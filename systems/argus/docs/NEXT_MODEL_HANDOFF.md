# NEXT MODEL HANDOFF — ARGUS

1. Keep ARGUS a sibling project. Do not bury it inside Icarus or DAEDALUS.
2. Read `INTEGRATION_MAP.md` and `docs/BLUEPRINT.md` first.
3. Before advanced models, build an append-only event journal and deterministic depth-delta reconstruction/replay engine.
4. Require exchange/source sequence for same-timestamp depth/trade ordering. Surface gaps/resets explicitly.
5. Preserve the EvidenceTier firewall in every feature and export. Candle proxies never become TRUE_TRADE/TRUE_DEPTH.
6. Implement book-map tensors: distance-to-touch buckets, persistence/decay, cancellation, replenishment, convexity, microprice and liquidity migration.
7. Implement flow events: aggressive bursts, sweeps, absorption/exhaustion, large-print concentration, change points and toxicity.
8. Build order blocks as lifecycle hypotheses with event-study/survival validation, not hand-drawn zones.
9. Build impact/queue/fill models and validate against real Icarus fills when available; never claim candle backtests validate execution.
10. Feed ARGUS outputs to ATHENA as state/uncertainty inputs and to DAEDALUS as research features; use explicit versioned schemas.
11. Only after replay + feature causality + calibration tests pass should a shadow Icarus adapter be built. No broker authority.

High-priority tests: event replay determinism, out-of-order handling, book gap invalidation, no future leakage, proxy-tier enforcement, order-block lifecycle invariants, impact calibration, same-time sequencing, venue-clock skew, and missing-depth abstention.
