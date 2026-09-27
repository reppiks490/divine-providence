# JANUS ∞ Run 032 Increment

## Scope
- Exact content-addressed receiver replay closure instead of unrestricted whole-table transfer.
- Neutral cryptographic fork evidence for multiple valid storage-certificate descendants.
- Kernel-enforced file-growth failure using `RLIMIT_FSIZE` on isolated scratch storage.
- Reconciliation of stale Run 031 test-count metadata.

## Knowledge delta by path
- `src/janus_infinity/core.py`: object replay graph build/verify/import, fork detection, RLIMIT_FSIZE probe.
- `tests/test_janus.py`: four Run 032 acceptance/negative tests.
- `schemas/object_replay_graph.schema.json`: graph envelope/object contract.
- `schemas/object_reconstruction_receipt.schema.json`: deterministic successful reconstruction receipt.
- `schemas/storage_certificate_fork_evidence.schema.json`: neutral branch evidence contract.
- `schemas/host_file_size_fault_probe.schema.json`: kernel file-size fault evidence contract.
- `ARCHITECTURE_INCREMENT_RUN_032.md`: architecture and authority boundary.
- `docs/RUN_031_LINEAGE_RECONCILIATION.md`: sealed-artifact/test-count discrepancy record.
- `docs/RESEARCH_PROVENANCE_RUN_032.md`: public-source claim mapping kept separate from private implementation state.

## Acceptance evidence
- Run 032 RED: 4/4 focused tests failed because the four new APIs were absent.
- Run 032 focused GREEN: 4/4 PASS.
- Full inherited suite after implementation: 120/120 PASS before sealing.
- Python compileall: PASS before sealing.

## Non-goals
- No branch winner selection.
- No distributed consensus or lease ownership.
- No claim of real ENOSPC, torn-sector, controller-reorder, power-loss, or distributed-filesystem coverage.
- No live Git reconciliation or commit identity claim.
