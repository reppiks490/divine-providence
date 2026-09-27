# JANUS ∞ Architecture Increment — Run 037

Run 037 makes the Run 036 possession/provenance evidence independently portable across a fresh receiver without granting that evidence temporal-truth authority.

A `janus-portable-provenance-replay-bundle-v1` binds the exact object replay graph, compact acquisition receipt chain, descriptive acquisition crosslink, and cache snapshot. Portable verification proves only graph closure, receipt-chain continuity, snapshot integrity, and possession continuity. It explicitly records `temporal_truth_validity_asserted=false` and `requires_independent_truth_revalidation=true`.

Fresh-receiver replay is a separate phase. Only after the receiver independently reconstructs the object graph and verifies the certified storage state may JANUS emit a `janus-replay-truth-revalidation-receipt-v1`. That receipt binds the portable bundle digest, cache-restore proof, independent reconstruction receipt, certificate digest, and resulting project-state digest. Possession evidence itself has `possession_evidence_truth_authority=false`.

Run 037 also adds deterministic semantic corruption schedules for receipt-chain truncation, crosslink-head mismatch, and snapshot-object substitution. Their outer bundle digests are resealed so rejection depends on semantic verification rather than a trivial outer checksum failure.

Authority remains unchanged: JANUS is project-twin temporal truth/conflict/proof synchronization only; no branch winner selection or Infrastructure/AEGIS/VECTOR/NEXUS/SuperMesh/live-trading authority is absorbed.
