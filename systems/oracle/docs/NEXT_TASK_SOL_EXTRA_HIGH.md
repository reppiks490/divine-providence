# SOL -> Sol Extra High — ORACLE Final 25% Queue

## Primary goal

Take the verified 75% ORACLE Financial & Research Automation Fabric and make it deployment-grade inside the actual Icarus Financial and Research tabs **without rebuilding the completed automation core**.

Start from tag `oracle-checkpoint-c-75pct` after verifying the packaged commit.

## P0 — actual Icarus tab integration

Wire `OracleTabAPI` (`icarus.oracle.tabs.v1`) into the real Icarus Financial and Research surfaces. Preserve the snapshot/delta schema rather than letting UI components reach directly into ORACLE internals.

Acceptance:
- Financial tab renders causal state, confidence, OOD, source health, warnings, and active-hypothesis counts;
- Research tab renders hypothesis status, evidence coverage, thesis health, pending/completed jobs, action recommendations, and scheduler explanations;
- command graph is navigable/read-only;
- UI cannot call broker/order APIs through ORACLE;
- restart produces the same snapshot for the same durable state.

## P0 — deployed sibling result adapters

The current build validates request-side sibling contracts and research-only boundaries. Add deployed/service result adapters for NEXUS, AION, ARGUS, ATHENA, and DAEDALUS with idempotent correlation back to ORACLE job/packet IDs.

Acceptance:
- duplicate results are idempotent;
- mismatched hypothesis/job/source/kind is rejected;
- DAEDALUS/ATHENA external promotion evidence is translated into existing `PromotionEvidence` only, never invented by ORACLE;
- AION remains evidence-memory authority.

## P0 — maintenance/revalidation waves

Convert action-board `RETEST` / `COLLECT_EVIDENCE` recommendations into a canonical supplemental research-wave abstraction. Do **not** mutate old immutable plans/jobs and do not create a second scheduler.

Acceptance:
- one hypothesis can have multiple versioned research waves;
- wave tasks use the existing scheduler/outbox/runtime/budget path;
- restart recovery includes wave ownership;
- cooldown/dedup prevents runaway revalidation loops;
- stale approved features can be routed to retirement review but ORACLE never retires/promotes production logic without external authority.

## P1 — live tab transport and operations

Add SSE/WebSocket or the Icarus-native equivalent for tab snapshot/delta streaming, plus health/metrics/backpressure/reconnect handling.

Acceptance:
- monotonic decision time;
- idempotent snapshot/delta sequence;
- bounded memory and backpressure;
- durable restart/recovery tests;
- no fabricated receive times.

## P1 — human review / RBAC surface

Promotion, rejection, retirement, or policy changes that require external authority should have explicit review records and actor identity. ORACLE may recommend; it must not silently acquire DAEDALUS/ATHENA/Icarus authority.

## P1 — scenario/digital-twin workspace

Build the previously designed Financial Digital Twin as a separate research-only workspace that perturbs FinancialState/features and launches counterfactual research. Keep scenario state explicitly synthetic and never merge it into observed market truth.

## P1 — load/chaos/security hardening

- concurrent research-job pressure tests;
- outbox crash/retry/late-ack chaos tests;
- SQLite -> production persistence decision if Icarus scale requires it;
- audit/log retention policy;
- schema migration tests;
- malformed sibling payload fuzzing;
- execution-firewall negative tests at service boundaries.

## Do not rebuild

Do not recreate or fork:
- autonomous loop;
- Research Exchange;
- outbox;
- journal/replay;
- retry runtime;
- scheduler;
- trigger detector;
- thesis monitor;
- action board;
- tab snapshot API;
- counterfactual attack-suite definitions;
- sibling ownership rules.

If another Work/Codex/Sol Extra High artifact appears after this package, reconcile it before coding and prefer the verified implementation with broader coverage.

## Takeover verification

Run:

```bash
PYTHONPATH=src python -m compileall -q src tests
PYTHONPATH=src pytest -q
```

Expected at SOL freeze: **34/34 passed**.

— **SOL**
