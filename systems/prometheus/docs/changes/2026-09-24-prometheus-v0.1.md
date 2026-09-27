# Change record — PROMETHEUS v0.1 vertical slice

**Date:** 2026-09-24  
**Actor:** OpenAI ChatGPT, at the user's direction  
**Request:** continue the PROMETHEUS loop build and ensure every new run uses every materially beneficial plugin, including Deep Research.

## Before

The repository contained the approved architecture spec only. A previous checkpoint had correctly preserved the design commit but no executable research loop existed.

## Change

Added immutable research contracts, plugin inventory/selection/audit, SENTINEL same-instant disagreement detection, append-only negative research memory, FORGE hypothesis/adversarial/replay evaluation, a top-level orchestrator, deterministic fixtures, and a demo CLI.

## Now

The v0.1 slice can prove the following locally:

- selected beneficial plugins require host execution evidence;
- Deep Research is mandatory when available for top-level research runs;
- irrelevant plugins remain visible with a skip reason;
- causal-instant mismatches and unknown availability fail closed;
- adversarial guardrails override headline metric gains;
- exact failed experiments are reused from research memory; and
- candidate status cannot exceed `PROMETHEUS_ENGINEERING_PASS`.

## Why

The system needs a testable scientific loop before adding autonomous code mutation, distributed scheduling, direct sibling service integration or production-facing capabilities. The plugin rule must be structural rather than dependent on conversational memory.

## Verification

Verification commands and exact results are recorded in `docs/VALIDATION_STATUS.md` after the final gate.

## Operational consequence

None. v0.1 is an offline research package and deterministic demo. No service deployment, broker connection, migration or restart procedure is introduced.

## Rollback

Revert the feature-branch commits. No external system or persistent production state is mutated by this repository.

**Stale when:** later PROMETHEUS versions add real sibling service adapters, a host plugin SDK, distributed scheduling, or a production promotion interface.
