# Validation

## 1. Candidate-version test matrix (selection evidence)

Every extracted project root in the corpus that ships tests was run once, before any repair
(Windows 11, CPython 3.10.11, `pytest -q -p no:cacheprovider`), 110 roots in total. Raw output:
`_analysis/testmatrix.txt` in the source corpus (outside this repo). The summary below
supports the canonical choices in `PROVENANCE.md`.

| Family | Candidates → result (passed unless noted) | Chosen |
|---|---|---|
| SuperMesh-X | v0.1 5 → v0.2 16/21 → v0.3 49 → … → v0.9 125 → v2.3 219 → v3.0 280 → v3.2 296 → v3.3 316 → v3.4 328 → v3.6 338 → **v3.7 FINAL2 351**; divergent v3.7 "final" 350 | FINAL2 (+ ported Node conformance: 352) |
| Infrastructure | v3 9 → v27 154 (13 failed) → … → v39 261 (29 failed) → v48 307 (34 failed) → **v49 307 (38 failed)**. Every v27+ failure was Windows portability (R8). | V49 → 344 + 1 skip after R8 |
| AEGIS | CP004 8 → CP006 12 → CP007 18 → CP008 31 → **CP009 36** | CP009 |
| NEXUS | v0.1 22 → v0.2 80 → v0.3 117 (zip and git bundle) → CSV loop v1/v1.2 118 → post-continuation 121 → v1.11 144 → **v1.15 153** | v1.15 |
| DAEDALUS | checkpoints 14 → 20 → 23/26 → 35 → 36 → foundation 45 → post-continuation 56 → **NEXUS-integrated 58** | v1.15 receiver |
| PROMETHEUS | v0.1 26, v0.2 26, v0.3 48, v0.4 67 (lineage) / 79 (provenance), v0.5 **77 (experiment-router) / 119 (attestation-lineage)** | merge → 156 → 161 (ADR 0004) |
| JANUS | Run 000 7 → 002 9 → 006 24 → 007 30 → 025 96 → 027–037 growing Windows failures → **Run 038 104 (39 failed, 31 errors)** | Run 038 → 140 + 4 skips after R11 |
| ORACLE | Checkpoint B 20 (6 failed), **Checkpoint C 28 (6 failed: siblings not found)**, same for zip and bundle | C → 34/34 after R4 |
| AION / ARGUS / ATHENA | 11 / 4 / 3 | single canonical versions |
| ASCENSION | Collision 0.2.1: 13; Evaluator 0.3: 15, 0.7: 27, 0.8: 46; Adapter 0.2: 10, 0.3: 68, 0.4: 105; Conformance Kit: 32; Context Distillation: 0 (placeholder) | unified → 150 → 160 after R5 |
| Excluded | 3D character builder: 11 collection errors (needs trimesh/FastAPI; out of scope). Icarus-repo PR workstream snapshots: partial file sets (30 passed; 1 and 17 import errors), kept as evidence only. | — |

## 2. Final build (deployed environment)

`python -m divine_providence.validate` in the repo's `.venv` (CPython **3.11.15**, Windows 11),
2026-09-27 03:12 UTC. The report is written to `provenance/validation_report.json` (git-ignored,
regenerated per machine) and served by the MCP `validation_report` / `list_systems` tools.

| System | Result |
|---|---|
| supermesh_x | 352 passed |
| infrastructure | 344 passed, 1 skipped (Linux `/proc` identity provider) |
| ascension | 160 passed |
| prometheus | 161 passed |
| nexus | 155 passed |
| janus | 140 passed, 4 skipped (3 kernel-`RLIMIT` probes on Windows, 1 pre-existing `/dev/full`) |
| daedalus | 58 passed |
| aegis | 36 passed |
| oracle | 34 passed |
| aion | 11 passed |
| argus | 4 passed |
| athena | 3 passed |
| **total** | **1,458 passed, 0 failed, 5 platform skips** |

- **Compile gate:** every Python file in all 12 systems byte-compiles.
- **ASCENSION adversarial scripts:** conformance failure injection 6,800/6,800 attack cases
  handled as designed; adapter failure injection 3,226 attacks (500/500 dependency-digest
  substitutions rejected, 26/26 provenance deletions detected); hostile v0.8 1,500 malformed or
  reordered proofs rejected; property v0.7 2,016 valid transitions with 1,000/1,000 mutated
  proofs rejected; property v0.8 1,000/1,000 binding attacks rejected.
- **Connections (`dp connect`):** all 5 pass. `nexus-siblings`; `nexus-contract-drift` (no semantic drift against
  the pinned v1.15 baseline); `nexus-oracle`; `nexus-prometheus` (bundle accepted and normalized into
  NEXUS/ARGUS/ATHENA/DAEDALUS observations with their evidence tiers); `prometheus-ascension` (all
  required attestation/receipt fields present, `authenticated=false`, Transfer BLOCKED by design).
- **Hub:** 24/24 tests, including a real stdio MCP handshake.
- **Second interpreter (3.10.11):** every changed subsystem was re-run on 3.10 after its repairs:
  AION 11, SuperMesh-X 352, PROMETHEUS 161, NEXUS 155, JANUS 140 + 4 skips, Infrastructure 344 + 1 skip,
  ASCENSION 160, ORACLE 34.

## 3. Deployment and MCP verification

- `scripts/bootstrap.ps1` from scratch creates `.venv` (it prefers 3.11+), installs, and runs the hub
  tests. `-RegisterMcp` registers `icarus-engine` at user scope, and `claude mcp get icarus-engine` reports
  **✔ Connected**.
- Driving the registered command over MCP stdio lists 16 tools. `list_systems` returns all 12 systems;
  `check_connection(nexus-prometheus)` returns ok with 4 normalized observations.
- Live engine (icarus-bridge on :8791, started by the owner): `engine_health` reports 9 assets warm;
  `engine_status`, `engine_assets`, `engine_trades(NQ)`, `engine_presets` and the token-protected
  `engine_research(status)` all return live data. No state-changing engine route is exposed.

## 4. Not verified here

- **Linux / POSIX:** no Linux runtime is available on this host. Windows fixes are gated
  (`os.name == 'nt'`) or platform-neutral resource releases, and the POSIX branches are unchanged,
  but the Linux suites were not re-run.
- **Real-data smoke:** NEXUS `real_smoke.py` / `loop-once` need the external TradingView CSV
  corpus, which is not in the source corpus.
- **Trading efficacy:** out of scope by design. No result here implies edge, profitability or
  production readiness.

## 5. Re-verification after the independent reviews (R18, R19)

The last full `dp validate` completed green at 2026-09-27 03:12 UTC (section 2). Afterwards, the
review fixes and the SuperMesh-X witness connection changed PROMETHEUS, SuperMesh-X, JANUS
tests and the hub. Each changed part was re-run individually:

| Component | 3.11.15 | 3.10.11 |
|---|---|---|
| prometheus | 162 passed | 162 passed |
| supermesh_x | 352 passed | 352 passed |
| janus | 140 passed, 4 skipped | 140 passed, 4 skipped |
| hub (`tests/`) | 39 passed | — |
| connections (`dp connect`) | 6/6 ok | — |

The other eight subsystems are unchanged since the section 2 run. A final consolidated
`dp validate` was started and **stopped by Claude Code because the machine ran critically low on
memory**. That was not a test failure. Re-run `dp validate` when memory allows; it exits non-zero
if any suite, compile gate, adversarial script or connection fails.
