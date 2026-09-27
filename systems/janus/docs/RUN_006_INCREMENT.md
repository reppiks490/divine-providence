# JANUS ∞ Run 006 — Bitemporal Overlay Reconstruction + Proof Integrity

Run 006 connects the immutable normalization ledger to bitemporal reconstruction without mutating source facts. `facts_as_of(valid_at, known_at)` now applies an approved interval-closure overlay only when the decision was known by the requested knowledge boundary, had not yet been revoked at that boundary, and every proof reference is integrity-bound to a stored proof bundle whose canonical SHA-256 matches and whose status is `proved` or `integrated`.

Proof references use `proof:<change_id>:<bundle_hash>`. Legacy/unbound references remain auditable ledger evidence but cannot alter reconstructed truth. Hash mismatch, missing bundle, or non-accepted proof status fail closed for the overlay only. Revocation is knowledge-time aware: historical reconstructions before revocation still see the approved interpretation; later reconstructions do not.

Safety invariant: source observations remain immutable; only integrity-verified, knowledge-time-valid interpretation overlays can affect reconstructed project truth.
