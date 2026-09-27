# Change Record — PROMETHEUS v0.5 Unified Merge

**Date:** 2026-09-26
**Branch:** `work/prometheus-v0.5-unified`
**Request:** Merge the two divergent v0.5 lineages into one build that keeps all functionality of both.

## Inputs

| Lineage | Tip | Path from common v0.3 ancestor `a00db63` | Suite at tip |
| --- | --- | --- | --- |
| A — experiment router | `444d978` (`work/prometheus-v0.5-experiment-router`) | v0.4 lineage + diagnosis (`2659350`) → v0.5 stale-aware experiment routing | 77 passed |
| B — attestation lineage | `4746f11` (`work/prometheus-v0.5-attestation-lineage`) | v0.4 provenance attestation (`22c2aae`) → v0.5 external attestation + provenance lineage | 119 passed |

The merge is a `--no-ff` merge of B into a branch cut from A. Git reported conflicts in `AGENTS.md`, `README.md`, `docs/VALIDATION_STATUS.md`, `src/prometheus_loop/cli.py`, `contracts.py`, `lineage.py` (add/add), `orchestration/loop.py`, `policy/promotion.py`, `tests/test_lineage.py` (add/add) and `tests/test_promotion_packet.py`. Every other file merged cleanly: `attestation.py`, `provenance.py`, `memory/store.py`, B's specs/plans/change records, `tests/test_cli.py`, `tests/test_loop.py` and `tests/test_sibling_loop.py` came from B or merged automatically; `policy/experiments.py`, `sentinel/diagnosis.py`, A's architecture docs and A's routing/lineage/diagnosis tests came from A.

## Resolution per conflicting file

### `src/prometheus_loop/lineage.py` (add/add) → two modules

The two branches created modules with the same name and different meanings:

- A: stale-aware research lineage — `build_lineage_manifest`, `detect_stale_lineage` over `ResearchLineageManifest` / `StaleEvidenceReport` (contract-fingerprint staleness).
- B: provenance ancestry — `ProvenanceLineageReport`, `verify_provenance_lineage`, which walks the `parent_manifest_ids` DAG of `ResearchProvenanceManifest` records in `ResearchMemory`.

Resolution: `prometheus_loop.lineage` keeps A's code unchanged. B's code moved unchanged to the new module `prometheus_loop.provenance_lineage`. Each module has a docstring that points to the other. `lineage.py` does not re-export anything, so the two concepts cannot be confused through one import path. Imports in `policy/promotion.py`, `orchestration/loop.py` and B's tests now use `prometheus_loop.provenance_lineage`.

### `src/prometheus_loop/contracts.py`

All new contracts from both sides are kept: `DisagreementCause`, `ExperimentRouteAction`, `ResearchPriorityBand`, `DisagreementDiagnosis`, `ExperimentRouteDecision`, `DeferredExperiment`, `ExperimentSpec.routing_context_id`, `ResearchLineageManifest` and `StaleEvidenceReport` from A, and `ResearchProvenanceManifest` with the attestation fields from B.

`ResearchPromotionPacket` now carries all three binding IDs: `lineage_manifest_id` (A), `provenance_manifest_id` and `provenance_lineage_report_id` (B). These fields default to `""` only so the packet can be built from keyword arguments. `__post_init__` rejects an empty or wrong-namespace value for each one, so every binding stays mandatory. The checks run in this order:

1. target is `DAEDALUS`, status is `READY_FOR_DAEDALUS_REVIEW`, and `production_authorized` is false (`production_authorized=True` is still structurally rejected);
2. evidence is non-empty;
3. B's checks: the provenance manifest and lineage report IDs have the right prefixes and both appear in `evidence_ids`;
4. A's check: `lineage_manifest_id` is non-empty.

### `src/prometheus_loop/policy/promotion.py`

`build_research_promotion_packet` takes the union of both signatures as keyword arguments. The binding inputs (`lineage_manifest_id`, `stale_report`, `provenance_manifest`, `provenance_lineage_report`, `loop_run_id`, `selected_plugin_descriptor_ids`, `observation_ids`, …) default to `None` or `()`. That way a non-eligible run can return `None` without fabricating evidence. For an eligible candidate, a missing binding still fails closed. The gate runs in this order:

1. A: if a staleness report is supplied, it must be bound to `lineage_manifest_id`. This check is unconditional, as in A.
2. The builder returns `None` when the run is not `RESEARCH_COMPLETE`, the lineage is stale, the result is not a `CandidateImprovement`, or the candidate is not an engineering pass.
3. A: the candidate must have a lineage manifest ID and a staleness report (`ValueError` otherwise).
4. B: the candidate must have a provenance manifest and a lineage report (`ValueError` otherwise). The manifest must match the live loop, experiment, candidate, descriptors, evidence, contributions, observations, source contracts, parents, attestations, receipts and policy. The lineage report must be complete, its tip must be the current manifest, and it must verify the manifest and its direct parents.
5. The packet's evidence is the union of both branches' evidence sets: candidate, candidate evidence, plugin evidence and contributions, attestations and receipts, lineage manifest, staleness report, provenance manifest and lineage report.

Neither binding can substitute for the other.

### `src/prometheus_loop/orchestration/loop.py`

- `HostPluginResult` gains B's `external_attestation` and `attestation_verification`.
- `RunInput` has the union of fields: A's `contract_fingerprints` and `current_contract_fingerprints`, and B's `source_contract_ids`, `parent_manifest_ids` and `plugin_attestation_policy`. `NexusRunInput` likewise has A's `current_contract_fingerprints` and B's `parent_manifest_ids` and `plugin_attestation_policy`. `run_nexus` binds the NEXUS snapshot as the A contract fingerprint `("NEXUS", hash)` and as the B source contract `nexus-contract:<hash>`.
- `LoopRunResult` has the union of fields: A's `diagnoses`, `route`, optional `hypothesis`/`experiment`, `DeferredExperiment` results, `lineage_manifest_id` and `stale_evidence_report`, and B's attestation IDs, coverage gaps, `provenance_manifest_id` and `provenance_lineage_report_id`.
- **Loop identity** uses B's inputs: run kind, objective, observations, plugins, candidate fingerprint, source contract IDs, parent manifest IDs, **and the attestation policy**. A's loop identity never included contract fingerprints, and this build keeps it that way.
- The order follows B: plugin evidence is normalized first, then external attestations are validated, and only then is status finalized. As a result, a strict-policy failure degrades the run.
- A's diagnosis and routing replace B's "first disagreement, fixed five checks" experiment construction, because routing is exactly what A's v0.5 added. The universal `leakage`, `missingness` and `reproducibility` guardrails are preserved by A's route policy.
- Attestation and receipt artifacts are persisted along with the other evidence before routing, so B's "persist before handoff" property holds. Their IDs are also recorded in A's preflight and final `ResearchLineageManifest`. This is the one new integration choice in this merge: the stale-aware lineage covers every participating artifact, so negative-result reuse is also scoped to the same attestation evidence set. This is conservative and never widens reuse.
- Deferred, abstained and reused-negative paths report attestation IDs and coverage gaps, and they expose no provenance manifest or lineage report.
- On the replay path, A's final lineage and staleness report are built first. The provenance manifest is then built only for a promotion-eligible result: a complete run, an engineering pass, **and** a clean final lineage. After that the provenance lineage report is verified, and the builder receives both bindings.

### `src/prometheus_loop/cli.py`

The CLI offers both commands: `demo` (A's route observability plus B's OPTIONAL-attestation fields) and `demo-strict-attested` (B). Git merged the `_demo` payload automatically, so it contains both A's `route` block and B's attestation and provenance keys. The only manual resolution was the `demo` help text, which is now "run the deterministic local v0.5 OPTIONAL-attestation fixture".

### `tests/test_lineage.py` (add/add)

The two suites are combined in one file and every test ID is preserved: A's 5 staleness-lineage tests come first, followed by B's 7 provenance-ancestry tests. The test bodies are byte-identical to the branch tips. The only change is consolidated imports: `verify_provenance_lineage` is now imported from `prometheus_loop.provenance_lineage`.

### `tests/test_promotion_packet.py`

Every test ID from both branches is kept. No assertion was removed or weakened. The changes are limited to the following:

- `ProvenanceLineageReport` is imported from `prometheus_loop.provenance_lineage` (relocated symbol).
- B's `_build_packet` helper additionally supplies A's now-mandatory inputs `lineage_manifest_id="lineage:1"` and a clean `StaleEvidenceReport`. Without them, the unified gate correctly refuses the packet.
- A's `test_complete_engineering_pass_emits_daedalus_review_packet` additionally supplies B's now-mandatory provenance inputs (manifest, complete lineage report, loop run ID, selected descriptor, observation and source-contract IDs). All of A's assertions are unchanged.
- Both branches define `test_promotion_packet_cannot_authorize_production`, with different bodies. The unified test builds a packet whose other bindings are all valid (the evidence includes A's `evidence:1` plus B's manifest and lineage IDs, and it carries all three binding IDs) and sets `production_authorized=True`. It keeps both branches' assertions: the only `PromotionStatus` is `READY_FOR_DAEDALUS_REVIEW`, and the constructor raises `production authorization`.
- All other tests (A's degraded/rejected and cross-lineage staleness tests, and B's tamper/policy/lineage/degraded/evidence tests) are byte-identical to their branch versions.

These input additions are needed because the merged gate enforces both branches' requirements at once. A test from one branch that builds an eligible packet from only its own branch's inputs could not pass without them.

### New merge-specific tests: `tests/test_unified_promotion_gate.py`

The file has 6 tests covering behavior that exists only in the merged build:

- valid provenance cannot replace a missing lineage manifest or staleness report;
- a clean lineage cannot replace a missing provenance manifest or lineage report;
- stale lineage suppresses the packet even when provenance is complete;
- the packet's evidence binds both lineages;
- the packet structurally requires a lineage manifest ID even when the provenance bindings are valid;
- a live strict-attested loop produces a packet bound to the route lineage, staleness report, provenance manifest, lineage report and attestations, and its lineage manifest records the attestation and receipt IDs.

### Documentation

- `README.md`: describes both v0.5 feature sets, the dual-binding packet, both lineage modules, both demos, and all design and plan references.
- `AGENTS.md`: union of both invariant lists and reading lists, plus new invariants for the dual binding and for keeping the lineage modules separate.
- `docs/VALIDATION_STATUS.md`: rewritten for the unified build with fresh gate results. Each branch's verified behavior and its unverified/absent list are kept.
- `CLAUDE.md`, `CODEX.md`, `docs/architecture/lineage-and-diagnosis.md`, `docs/architecture/plugin-evidence-and-promotion.md`: short additions describing the dual binding.

## Behavioral differences from either tip (intentional)

- A run's loop ID now also hashes B's identity inputs. With identical inputs, the loop ID differs numerically from branch A's value, and so do the plugin-evidence IDs derived from it. No test or doc hard-codes these hashes.
- B-style runs now go through A's router. Their `ExperimentSpec` carries `routing_context_id` and route-specific checks, so experiment IDs differ numerically from branch B's values. Runs whose only disagreements defer or abstain now yield a `DeferredExperiment` and no provenance manifest; before the merge, B would have replayed them.
- The promotion packet requires both bindings, as described above.

## Authority impact

None. No production, broker, sibling-write, or cryptographic-verification authority was added. `production_authorized=True` remains structurally rejected, and PROMETHEUS still emits only `READY_FOR_DAEDALUS_REVIEW`.

**Stale when:** either lineage's promotion requirements, loop-identity inputs, lineage/provenance schemas, or routing policy change.
