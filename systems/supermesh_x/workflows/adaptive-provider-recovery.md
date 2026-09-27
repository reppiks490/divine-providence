# Adaptive Provider Recovery

1. Detect a provider/tool surface refresh, failure burst, auth change, or degraded benchmark.
2. Fingerprint the current surface and diff it against the last known snapshot.
3. If compatible, validate and update the snapshot.
4. If breaking, open a replacement search for the same capability.
5. Emit a discovery receipt with exposed/withheld candidates.
6. Apply runtime-state, auth, transport, privacy, circuit-breaker, and action-authority gates.
7. Rank compatible candidates using state health and capability-specific feedback.
8. Route to the highest verified candidate; otherwise degrade safely.
9. Record the replacement reason and new surface fingerprint in provenance/audit state.
10. Never transfer credentials or private payloads between providers during recovery.
