# OPUS NON-3D ABSOLUTE HANDOFF — 2026-09-26

Purpose: give Opus the broadest recoverable, provenance-aware continuation package for all non-3D work developed so far.

## Read first
1. `control_and_state/CHAT_DERIVED_WORKSTREAM_LEDGER.md`
2. `control_and_state/AUTOMATION_CONTROL_STATE.md`
3. `github_live_snapshot/README_GITHUB_SNAPSHOT.md`
4. `KNOWN_INACCESSIBLE_AND_LIMITATIONS.md`
5. `EXCLUSIONS_AND_QUARANTINE.md`
6. `artifact_corpus/README_FOR_OPUS.md`
7. `ABSOLUTE_MANIFEST.csv` / `ABSOLUTE_MANIFEST.json`

## What this package adds beyond the prior handoff
- live automation/control-loop state and current goals
- chat-derived non-file decisions and chronology
- current GitHub repository inventory
- observed branch inventory
- exact relevant ICARUS PR status summaries and verification evidence
- explicit unreliable-output quarantine
- explicit inaccessible-source ledger
- preserved prior non-3D artifact corpus and prior ZIP baseline
- fresh SHA-256 manifest over the entire superset

## Canonicality rules for Opus
- Repository evidence outranks chat summaries.
- A generated report does not prove implementation.
- A stored design does not prove tests ran.
- Green tests on a branch do not imply merge/deployment/live-trading authority.
- `execution_authorized=false` remains the safe default.
- Treat unresolved identity/provenance/temporal/dependency gaps as fail-closed.
- Re-fetch GitHub before acting on branch/PR state because repository state can change after this snapshot.

## Scope
Included: ICARUS, AEGIS, HELIOS, NEXUS, AION/PARALLAX, ARGUS, ATHENA, DAEDALUS, ORACLE, OMNIVISION, Pulse-related research, OrderBlockPro evidence work, futures/Pine/backtest research, RATE–OMNI MYTHOS, loop/governance/assurance work, and other recoverable non-3D artifacts.
Excluded: all 3D masterbuild/character-builder work.
