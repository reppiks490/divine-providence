# JANUS ∞ Run 023 — Temporal Lease/Fencing + Fork Evidence

Run 023 extends Run 022's monotonic fencing with owner-bound temporal leases. A lease binds a session, owner, fencing epoch, acquisition/renewal times, and expiration. Renewal preserves the epoch only while the owner is still current and unexpired; takeover after expiry requires a newer fencing epoch. Receipt-head divergence now emits content-addressed `janus-receipt-fork-evidence-v1` rather than only raising an exception. Atomic joint receipts bind the active lease owner and expiry alongside the fencing epoch and expected receipt head.

Ownership remains unchanged: JANUS verifies temporal project truth/proof synchronization and does not acquire semantic authority from NEXUS/AION/ARGUS/ATHENA/DAEDALUS/Icarus.

Verification: inherited Run 022 baseline 85/85; Run 023 final 89/89; compileall passed. Live repository reconciliation not performed.
