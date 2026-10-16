# ICARUS federation instructions for AI units

Every AI unit working in this repository must treat Divine Providence as part of the shared ICARUS evidence fabric, not as an isolated project.

## Central work coordination is mandatory

Before substantial work, use the canonical model-neutral coordination bus in `reppiks490/icarus-owner-actions`: read `coordination/START_HERE.md`, `coordination/ACTIVE.md`, `coordination/collisions.json`, `coordination/owner_status.json`, and applicable directives. Create/resume a unique central session and publish a PLAN/CLAIM event with narrow repo-qualified targets before mutation. Re-read the compiled collision state immediately before changing a reserved path. No task is reserved merely because a particular model or chat historically worked it; overlapping target work requires explicit mutual cooperation. Publish WAITING/UPDATE/BLOCKED/HANDOFF/RELEASE/COMPLETE events as state changes, and continue useful non-conflicting work while dependencies run.

Before making claims about data availability, provider access, freshness, market context, research evidence, or blockers, read the canonical federation state in `reppiks490/Icarus-engine`:

- `config/data_ingestion_manifest.json`
- `docs/agent-handoffs/FEDERATED_DATA_COLLECTION.md`
- `docs/agent-handoffs/DATA_GAP_LEDGER.md`
- `automation_intelligence/sentinel/data_health.json`
- `automation_intelligence/manifest.json`

This repository contributes independent research/evidence surfaces. In particular, `.github/workflows/icarus-institution.yml` researches owned CSV corpora and public official-announcement feeds, while `.github/workflows/icarus-observatory.yml` produces system/observatory evidence. `scripts/institution/sources.py` currently reads official Federal Reserve, ECB, and SEC announcement feeds. Preserve those source identities and first-observation timing rules.

The local `ICARUS_ENGINE_TOKEN` documented in `.env.example` is a loopback engine credential. Do not print, copy, commit, artifact, or move its plaintext into chat or another repository. A local token is not evidence that another AI account can access it.

All AI units must use source-qualified evidence from the wider ICARUS federation when relevant and must publish explicit blockers instead of silently omitting an unavailable source. Do not purchase data, activate trading execution, weaken research-only authority, or relabel missing/denied data as success. Live broker arming follows the central owner status and is currently disabled.
