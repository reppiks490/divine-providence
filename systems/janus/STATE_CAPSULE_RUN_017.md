# Icarus/JANUS State Capsule — Run 017

Authoritative offline checkpoint: JANUS ∞ Run 017, continuing Run 016.
Completed: constrained direct temporal delegation; non-transitive-by-default enforcement; same-authority key rotation lineage; authorization decision lineage includes satisfied principals, delegation edges, rotation edges.
Verification: 68/68 pytest tests pass; `python -m compileall -q src tests` passes.
Interfaces: `record_authority_delegation(...)`, `record_key_rotation(...)`, enhanced `verify_authorized_merkle_root_at(...)`.
Dependencies: Python; cryptography>=41; SQLite.
Ownership: JANUS temporal project-twin truth/authorization verification only. NEXUS/AION/ARGUS/ATHENA/DAEDALUS/Icarus authority scopes remain external and explicit.
Blockers: live Git repo reconciliation unavailable; first-party Deep Research unavailable. No live-repo adoption claim.
Tools actually used: Plugin/capability discovery attempt; Files/Google Drive listing; container/Python/pytest/compileall.
Next: delegation revocation + delegation proof bundles; rotation-chain cycle prevention and full predecessor-chain reconstruction; bind lineage into sync receipts and selective evidence closure.
Resume: load Run 017 package/capsule, rerun `PYTHONPATH=src pytest -q` and compileall, then implement Run 018 without restarting baseline.
