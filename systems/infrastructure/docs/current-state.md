# Infrastructure Current State — V35

Authoritative package target: V35.

V35 adds independent signed witness-set governance, non-decreasing quorum policy, quorum-overlap membership rotation, governed witness verification, and signed transparency/gossip checkpoints.

Recovery trust now layers:
V30 crash-reconcilable dual-chain persistence ->
V31 key-policy epochs ->
V32 asymmetric public verification ->
V33 trust-root generations and algorithm migration ->
V34 independent witness quorum ->
V35 signed witness governance and transparency evidence.

Witness/governance/transparency remain evidence-only and have no infrastructure mutation authority. V3 guard/canary/health-floor invariants remain intact. Positive OutcomeMemory restoration remains disabled.

See `docs/v35-witness-governance-transparency-contract.md` and the versioned STATE CAPSULE for exact verification evidence and resume instructions.
