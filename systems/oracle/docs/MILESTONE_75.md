# ORACLE 75% Milestone — Financial & Research Operating Layer

Owner/signature: **SOL**  
Intended takeover: **Sol Extra High**  
Date: 2026-09-23

## Goal reached

ORACLE now turns the Icarus Financial and Research tabs into a deterministic research operating surface rather than a passive dashboard. The 50% autonomous research loop remains canonical; the 75% layer adds state-triggered research, thesis monitoring, adaptive governance, explainable action recommendations, and stable tab-facing read models without taking authority from sibling systems.

## Added after the 50% checkpoint

- restart-safe financial-state trigger detector with hysteresis and cooldowns;
- feature-dislocation, OOD, and source-health research triggers;
- durable trigger-control state in SQLite so restarts do not duplicate research;
- thesis freshness decay, drift detection, low-health detection, and retest surfacing;
- adaptive causal research-priority overlay that never mutates immutable ResearchJob specs;
- machine-readable priority reasons for every boost/penalty;
- research action board: COLLECT_EVIDENCE / RETEST / EXTERNAL_PROMOTION_REVIEW / REJECTION_REVIEW / RETIREMENT_REVIEW / MONITOR;
- explicit external-authority flag on promotion/rejection/retirement recommendations;
- deterministic Financial tab view, Research tab view, and active command-graph projection;
- stable `icarus.oracle.tabs.v1` snapshot API plus compact delta calculation;
- restart-stable snapshot hashes based only on durable state; ephemeral journal state is never represented as durable truth;
- deterministic command-graph edge ordering across restart;
- adaptive priority multipliers are journaled with dispatch commands so replay remains deterministic;
- operating-layer state preserves NEXUS/ARGUS/AION/DAEDALUS/ATHENA/Icarus ownership boundaries.

## Cross-agent reconciliation

Before this freeze, prior conversation context, Library artifacts, and the shared workspace were checked for overlapping Sol Extra High / Codex / Work ORACLE implementations. No separate newer ORACLE implementation exists. The relevant external work is NEXUS v0.3 and sibling-system infrastructure; ORACLE consumes those boundaries instead of duplicating them.

A previously detected concurrent ORACLE automation tranche was already reconciled at the 50% milestone; its canonical files remain the basis of this build. Do not recreate `autopilot`, `routing`, or duplicate outbox/journal engines.

## Verification

- ORACLE: **34/34 tests passed**.
- `python -m compileall -q src tests`: passed.
- autonomous sibling boundary test passes for NEXUS, AION, ARGUS, ATHENA, and DAEDALUS.
- restart recovery tests pass.
- tab snapshot restart parity passes.
- execution firewall remains active; no ORACLE artifact may set production authorization true.

## What ORACLE owns at 75%

ORACLE owns coordination of:
- causal FinancialState ingestion;
- machine research triggers and deduplication;
- hypothesis lifecycle records;
- research plans/jobs and bounded scheduler control;
- durable research outbox and retries;
- research evidence fan-in;
- conservative thesis assessment;
- thesis freshness/drift monitoring;
- action recommendations and research priority overlays;
- Financial/Research tab read models and command graph;
- counterfactual/falsification specifications sent to DAEDALUS.

ORACLE still does **not** own:
- NEXUS market-data truth;
- ARGUS microstructure truth;
- AION durable evidence-memory authority;
- DAEDALUS scientific promotion authority;
- ATHENA supervisory/abstention authority;
- Icarus broker/order execution authority.

## Final 25% intentionally left for takeover

See `docs/NEXT_TASK_SOL_EXTRA_HIGH.md`. The next model should finish deployment-grade integration, not rewrite ORACLE's completed core.

— **SOL**
