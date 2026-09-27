# JANUS ∞ State Capsule — Run 036

Checkpoint: Run 036 descriptive acquisition-provenance lineage + adversarial chain schedules + possession-continuity snapshot proofs.

Predecessor: persisted Run 035 ZIP SHA-256 `9ae662ad45b0810a2d1a33b2d147442fbfb125d2db3f0ee216d7e71dc3dda563`. Reconciliation before changes: all 245 entries in `CONTENT_MANIFEST_RUN_035.json` hash/size matched exact extracted bytes; `PYTHONPATH=src python -m pytest -q` reproduced 132/132; compileall PASS. The inherited generic `PACKAGE_SHA256SUMS.txt` was stale for four Run 035-updated files; it is preserved as `PACKAGE_SHA256SUMS_RUN_035_LEGACY.txt` in this candidate and replaced by a current Run 036 verifier without modifying the Run 035 artifact.

Run 036: `crosslink_compact_acquisition_provenance` binds a valid compact acquisition receipt chain to graph/certificate proof lineage as descriptive-only evidence with `temporal_truth_validity_asserted=false`, `authority=descriptive_only`, and `winner_selected=false`. `generate_compact_receipt_chain_adversarial_schedules` deterministically creates splice, out-of-order and duplicate-round chains that the verifier must reject. `build_compact_cache_snapshot` and `restore_compact_cache_snapshot` verify exact content-addressed possession continuity while emitting a restore proof that requires independent temporal-truth revalidation.

Verification: focused increment included in full suite; final 136/136 PASS; compileall PASS; 67/67 Draft 2020-12 schemas valid. No repository adoption or production authorization is asserted.

Authority: JANUS remains project-twin temporal truth/conflict/proof synchronization only. Acquisition/cache provenance is subordinate descriptive evidence. No certificate winner selection; no Infrastructure/AEGIS/VECTOR/NEXUS/SuperMesh/live-trading authority absorbed.

Blocker: authoritative Git checkout remains unavailable in the recovered package context; READY_TO_COMMIT=false until repository reconciliation is performed against the actual JANUS repository.

Resume: Run 037 should add portable replay of the new provenance/snapshot proofs across a fresh receiver, bind snapshot restore proofs to explicit replay-time truth revalidation receipts, and extend generated corruption schedules without turning possession evidence into truth authority.
