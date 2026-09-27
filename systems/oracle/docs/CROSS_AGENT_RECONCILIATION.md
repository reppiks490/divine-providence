# Cross-Agent Reconciliation — ORACLE

Date: 2026-09-23
Owner continuing after reconciliation: SOL

Purpose: prevent duplicate implementation across ChatGPT Work / Codex / Sol Extra High and the local SOL continuation.

## Canonical concurrent tranche detected

During the 50% milestone build, a concurrent ORACLE automation tranche appeared in the shared workspace. It was more complete than SOL's overlapping in-progress `autopilot/routing/replay` path and is therefore canonical.

Canonical files and reconciliation hashes at detection:

- `src/oracle/automation.py` — `e6ff2731110937ad8038038dcde9179573e2e3753bab9df3f7ea86f35be015e6`
- `src/oracle/plans.py` — `59bc714bae6706d7582c15b97fe30a0865d347a2ebb09c171263614f922d8eba`
- `src/oracle/requests.py` — `7ef14b1125352e9dd2f0538027f416600cca3298fc2d604fb05757c1ef1cb15e`
- `src/oracle/journal.py` — `7002babfd71719dbac81cafbfe7f3254fe6274581703230e8bd2aefb6af44d32`
- `src/oracle/outbox.py` — `0c3757db39d8e53605c37b7a0065c344ae3819f27e6ec0067034dade9331df1e`
- `tests/test_autonomous_loop.py` — `1e79f0b28e0e288bff73e3e27e169bb8496445c0f3ec2ef1d4316e2b8d8e530a`

The overlapping SOL-only modules `autopilot.py`, `routing.py`, `checkpoint.py`, and their duplicate tests were removed instead of maintaining parallel APIs.

## Capabilities already present in the canonical tranche

Do not rebuild these under new names:

- deterministic six-task sibling research planning;
- falsification/counterfactual attack-suite attachment;
- structural hypothesis deduplication;
- information-value scheduling and bounded compute budgets;
- durable SQLite persist-before-send research outbox;
- deterministic typed sibling research requests;
- bounded retry/backoff and dead-letter behavior;
- evidence source/kind enforcement and idempotent fan-in;
- hash-chained command journal;
- deterministic command replay verification;
- research-requirement coverage bound into the Research Exchange;
- lifecycle transition into QUEUED/TESTING without execution authority.

## Remaining work after reconciliation

Extend only genuine gaps, especially:

1. automatic thesis assessment when required evidence is complete, while keeping DAEDALUS/ATHENA authority intact;
2. explicit failed/superseded outbox packet state instead of overloading acknowledgement semantics;
3. lifecycle advancement from external promotion evidence with no direct execution authority;
4. financial-state trigger policy, thesis decay/drift, and research reprioritization;
5. tab-facing Financial/Research view models and command graph projections;
6. exact sibling integration tests for the autonomous request/result loop;
7. recovery tests across process restart using the durable journal + outbox.

## Rule

Before each major ORACLE checkpoint, search Work/Codex/Library and the shared workspace for newer overlapping implementations. Prefer the existing verified implementation; merge missing safeguards into it rather than creating another subsystem.
