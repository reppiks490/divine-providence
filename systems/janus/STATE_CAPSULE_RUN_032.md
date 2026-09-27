# JANUS ∞ STATE CAPSULE — Run 032

## Authoritative checkpoint
Run 032: Minimal Object-Addressed Replay Graph + Certificate Fork Evidence + Kernel File-Size Fault.

This capsule continues from the sealed Run 031 artifact without rebuilding prior work. The authoritative offline predecessor ZIP remains `/mnt/data/JANUS_INFINITY_HANDOFF_RUN_031.zip` with SHA-256 `b80770a71af3ea1f06e6443111484efd2a9467e9dc1a5e2d299086e97524c6c4`.

## Completed
- Exact SHA-256-addressed receiver replay graph with explicit root and transitive object references.
- Minimal replay table closure limited to JANUS project-state tables plus certificate-verification rows for promotion journal, recovery certificate, quarantine evidence, and receipt head.
- Exact closure verification rejects missing, unreachable-extra, substituted, schema-drifted, and root-reference-mismatched objects before receiver promotion.
- Fresh receiver reconstruction independently verifies the original signed storage certificate against the certified DB/WAL/SHM evidence snapshot.
- Deterministic `janus-object-reconstruction-receipt-v1` on successful reconstruction.
- Neutral fork detection for multiple cryptographically valid storage-certificate descendants at the same `(previous_chain_digest, previous_certificate_digest)` branch point; JANUS records evidence and selects no winner.
- Kernel-enforced `RLIMIT_FSIZE` child-process probe producing `SIGXFSZ` / `EFBIG` on isolated scratch storage.
- Run 031 test-count lineage discrepancy classified as stale capsule metadata: sealed artifact/test hashes match, while fresh collection is 116 tests rather than the capsule's 115.

## Verification evidence
- Sealed Run 031 baseline hash rechecked: PASS.
- Fresh Run 031 baseline from the sealed bytes before mutation: **116/116 PASS**; `python -m compileall -q src tests`: PASS.
- Run 032 TDD RED: **4/4 focused tests failed** because the new APIs were absent.
- Run 032 focused GREEN: **4/4 PASS**.
- Final full inherited + Run 032 suite: **120/120 PASS**.
- `python -m compileall -q src tests`: **PASS**.
- JSON Schema Draft 2020-12 meta-validation: **56/56 PASS**.
- Live reconciliation gate: `git_repository_unavailable`, `ready_to_commit=false`.

## Hashes
- `src/janus_infinity/core.py`: `8146818af0a425790842c84174d3529eed9162b129700290b4e236d7c7e09a6c`
- `tests/test_janus.py`: `f76c2e5a552ee8f06d2345779bf4d5320e48d507e54b711726d862773a94cc73`
- Final package/content-manifest hashes are external sealing values generated after this capsule to avoid self-referential hashing.

## Interfaces added
- `build_object_replay_graph(certificate, forensic_dag=None)`
- `import_and_verify_object_replay_graph(graph, trust_store)`
- `detect_storage_certificate_forks(entries, certificates, trust_store)`
- `run_host_file_size_limit_probe(root, max_file_bytes=4096)`

## Contracts added
- `schemas/object_replay_graph.schema.json`
- `schemas/object_reconstruction_receipt.schema.json`
- `schemas/storage_certificate_fork_evidence.schema.json`
- `schemas/host_file_size_fault_probe.schema.json`

## Dependencies / boundaries
- Existing Python/SQLite/cryptography stack only; no new runtime dependency added.
- JANUS authority remains project-twin temporal truth/conflict/proof synchronization only.
- No Infrastructure persistence/locking authority, VECTOR intelligence authority, ASCENSION evaluation/trust-policy authority, or NEXUS/AION/ARGUS/ATHENA/DAEDALUS sibling authority was absorbed.
- Fork evidence is descriptive conflict proof only and does not choose a winning branch.

## Research provenance
- SQLite official file-format/WAL documentation was used only as read-only external evidence supporting preservation of DB/WAL/SHM storage-state verification.
- Linux `getrlimit(2)` documentation was used only as read-only evidence for `RLIMIT_FSIZE` → `SIGXFSZ` / `EFBIG` behavior.
- No private repository contents, credentials, secrets, or internal artifacts were sent to public retrieval.

## Blockers / risks / assumptions
- No authoritative live Icarus Git checkout is exposed here; no commit, branch, PR, merge, or repository identity is claimed.
- True block-device power loss, filesystem-wide ENOSPC, torn-sector writes, controller reordering, media I/O errors, and distributed/network filesystem semantics remain unverified.
- Object replay v1 is exact for its declared closure, but a future run should add receiver-side deduplicated fetch/missing-object negotiation rather than transporting the entire reachable object map in one envelope.
- Fork detection proves conflicting valid descendants; branch-resolution policy remains outside JANUS.

## Tools actually used
- Local/container Python, pytest, compileall, SQLite, SHA-256, deterministic packaging utilities.
- Superpowers workflow skills (brainstorming/TDD/debugging/verification/execution guidance).
- Baton Pass continuity skill for resume/handoff discipline.
- Akinator repository-change skill for same-batch code + docs + verification discipline.
- Codex Coordinator skill was inspected for repository coordination applicability; no live Git checkout existed to coordinate.
- Public web research against primary SQLite and Linux manual sources.
- First-party Deep Research was invoked in the immediately preceding continuation step and not restarted during this implementation step.

## Durable locations
- Working tree: `/mnt/data/janus_run032/`
- Prior sealed checkpoint retained unchanged: `/mnt/data/JANUS_INFINITY_HANDOFF_RUN_031.zip`
- Run 032 package and standalone capsule are sealed after this file is written.

## Exact resume instructions
1. Verify the Run 032 package SHA-256 against the external seal reported alongside the artifact.
2. Extract to a fresh directory; do not overlay Run 031.
3. Run `PYTHONPATH=src pytest -q` and require **120/120 PASS**.
4. Run `python -m compileall -q src tests` and require PASS.
5. Validate every `schemas/*.json` with Draft 2020-12 and require **56/56 PASS**.
6. Preserve the Run 031 lineage-reconciliation note; do not rewrite the original Run 031 capsule.
7. Before any commit claim, reconcile against the authoritative live Icarus Git checkout with expected artifact hashes.
8. Next highest-value JANUS work: selective/deduplicated object fetch negotiation and missing-object proofs; branch-conflict propagation/cross-linking into existing temporal conflict evidence; one stronger real filesystem capacity or I/O fault harness if safely exposed.
