# Provenance and canonical-source selection

Source corpus: `C:\Users\tripl\Downloads\divine providence` (≈414 MB, 421 top-level
files: 250 ZIPs, 18 git bundles, 3 videos, documents). Every archive and nested
archive was extracted (3.8 GB, ~30k files) and every candidate version with tests was
executed (see `docs/VALIDATION.md`). The corpus itself was not modified.

Machine-readable records:
- `provenance/assembly_sources.json`: source archive, archive SHA-256 and identity per subsystem
- `provenance/file_provenance.json`: every file in `systems/` → source (archive path or
  `git:<commit>::path`), source SHA-256, current SHA-256, and `modified`. The rows with
  `modified: true` are exactly the consolidation repairs listed in `docs/REPAIRS.md`.
- `provenance/docs_provenance.json`: every documentation decision (copied / duplicate / excluded)

Selection criteria were completeness, test evidence, hash identity against the
recovered master handoff (§27), lineage, and unique functionality. Newest was not
assumed to be best.

| System | Canonical source | Why | Superseded / alternatives |
|---|---|---|---|
| supermesh_x | `supermesh_x_v3_7_0_cycle7_final(1).zip` (SHA `85556a38…`, byte-identical to `…final2.zip`) | Handoff-canonical hash; 351 tests | `…cycle7_final.zip` (built 5 h later) is a **divergent** v3.7 branch with a different trusted-time design (`trusted_time_policy.py`, Node conformance fixture), 350 tests. It conflicts module-for-module with FINAL2 and was not merged (see VALIDATION open issues). v0.1–v3.6: ancestors. |
| infrastructure | `infrastructure_supervisory_loop_v49.zip` (SHA `70b2f13c…`, matches its own V49 capsule) | Direct lineage successor of the handoff's V39 (`8ed45671…`, verified); 345 tests on Linux per capsule | v3–v48: ancestors; `infrastructure_supervisory_loop.zip`, `…all_current_work.zip`: early snapshots |
| aegis | `AEGIS_Challenger_Forge_Checkpoint_009.zip` (SHA `8199c575…`) | Handoff-canonical; 36/36 | CP001–008: ancestors |
| nexus | `ICARUS_CSV_RESEARCH_v1.15_ITER32_2026-09-25.zip` → `nexus-adaptive-market-fabric` (SHA `c88b3c67…`) | Handoff-canonical; 153/153; superset of v0.1–v0.3 and CSV loop v1–v1.12 | NEXUS v0.3 git bundle (117 tests), CSV loop v1/v1.2 (118), v1.11 (144). Its 1.2 GB `artifacts/` (32 loop iterations of generated JSON) is excluded. `contracts/baselines/sibling_contract_drift_baseline.v0.3.SOL.json` was restored from `ICARUS_CSV_RESEARCH_ALL_CURRENT_WORK_POST_CONTINUATION…zip` because PROMETHEUS pins it. |
| daedalus | same archive → `daedalus-research-os` | Strict superset of the 45/45 foundation (`DAEDALUS_WITH_ATHENA…`, SHA `34a92861…`): identical code plus NEXUS bridge, future-evidence and diagnostics modules; 58/58 | 13 DAEDALUS checkpoints (01–09, repair-start, core-contracts, current-build): ancestors |
| prometheus | **merge** of `PROMETHEUS_v0.5_VERIFIED_2026-09-25.bundle` (experiment-router `444d978`, handoff-canonical zip SHA `6d27cb5a…`, 77 tests) and `PROMETHEUS_v0.5_VERIFIED_2026-09-25(1).bundle` (attestation-lineage `4746f11`, 119 tests) → merge commit `136563e2`, 156 tests | Two parallel v0.5 branches forked at v0.3 `a00db63`, each with unique functionality; ASCENSION's declared profile targets `4746f11` while the handoff named `444d978`. The merge keeps both. | v0.1–v0.4 zips/bundles: ancestors. The merge history is preserved outside Git at `_analysis/PROMETHEUS_v0.5_UNIFIED_2026-09-26.bundle` (SHA `adeedbe3…`). |
| aion | `ICARUS-AION-MARKET-MEMORY-v0.1.zip` (SHA `7af272b7…`) | Handoff-canonical; 11/11 | — |
| argus | `ARGUS-MICROSTRUCTURE-OS_HANDOFF.zip` (SHA `0f9209a7…`) | Handoff-canonical; 4/4 | `(1)` copy is byte-identical |
| athena | `ATHENA-SUPERVISORY-FABRIC_HANDOFF.zip` (SHA `47225305…`) | Handoff-canonical; 3/3 | `(1)` copy is byte-identical |
| oracle | `ORACLE_CHECKPOINT_C_75_SOL.git.bundle`, HEAD `6255339daf80…` = tag `oracle-checkpoint-c-75pct` | Exact handoff identity; 34/34 once siblings resolve | Checkpoint B 50% (26 tests); checkpoint-C ZIP (SHA `712c97d7…`) wraps the same bundle |
| janus | `JANUS_INFINITY_HANDOFF_RUN_038.zip` | Latest run; its capsule records 144/144 on Linux and chains from Run 037 SHA `2f6811e0…` | Handoff's Run 035 ZIP (`9ae662ad…`) is **not** in the corpus; Runs 002–037 are ancestors |
| ascension | union of `ASCENSION_Collision_Detector_v0.2.1`, `Context_Distillation_Engine_v0.1`, `Evaluator_Fabric_v0.8`, `Manifest_Trust_Collision_Adapter_v0.4`, `Sibling_Manifest_Conformance_Kit_v0.1` (SHA `23970729…`) | Flat version-suffixed modules that import each other; all overlapping files are byte-identical (the assembler aborts on any conflict). Per-kit metadata is under `kits/<kit>/`. | Evaluator v0.3/v0.7, Adapter v0.2/v0.3, `ASCENSION_ALL_CURRENT_WORK`, `…EVERYTHING_CURRENT_MASTER`: ancestors/aggregates |

## Material outside this repository

See `docs/REPO_HYGIENE.md`. Everything excluded remains in the source corpus.
