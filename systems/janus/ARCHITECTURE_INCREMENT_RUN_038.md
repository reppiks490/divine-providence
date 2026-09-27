# JANUS ∞ Architecture Increment — Run 038

Run 038 adds receiver-local durability and replay-equivalence evidence on top of Run 037 without changing JANUS project-truth authority.

## Receiver-local revalidation ledger
Truth-revalidation receipts now may be appended to a dedicated `truth_revalidation_receipt_chain` table. This ledger is explicitly receiver-local control evidence, not imported project truth. Sender replay exports exclude it, and object-graph promotion preserves the local ledger across certified project-state replacement. Appends require an expected previous head, so stale writers and rollback attempts fail closed.

Each chain entry binds sequence, previous entry digest, truth receipt digest, bundle digest, graph digest, certificate digest, and project-state digest. Independent chain verification detects entry tampering, sequence gaps/splices, and rollback relative to an expected known head.

## Cross-receiver equivalence
Two independently verified truth-revalidation receipts may produce a deterministic cross-receiver equivalence proof only when they bind the same portable bundle, object graph, certificate, and project-state digest. This evidence is descriptive consistency only and retains `winner_selected=false`.

## Forged/stale receipt attacks
Run 038 adds binding verification for truth-revalidation receipts plus deterministic semantic corruptions for stale bundle binding, forged certificate binding, and forged reconstruction-receipt binding. The corruptions are resealed so failure depends on semantic binding verification, not a trivial receipt checksum mismatch.

Authority remains unchanged: JANUS is project-twin temporal truth/conflict/proof synchronization only. Receiver-local durability and cross-receiver consistency do not grant branch-resolution, sibling-system, repository, deployment, or live-trading authority.
