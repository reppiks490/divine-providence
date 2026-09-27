# JANUS ∞ Run 033

Adds selective/deduplicated acquisition over the Run 032 exact object-addressed replay closure. A receiver advertises only cryptographically valid cached objects, obtains a deterministic missing-object proof, and accepts only the exact missing set before the inherited full closure/certificate/promotion verification executes. Missing-proof tampering, omission, overdelivery, substitution and equivocation fail closed.

Certificate forks are cross-linked into descriptive JANUS temporal conflict evidence with `winner_selected=false` and `external_branch_resolution_required`; JANUS does not acquire branch-resolution policy.

Adds a safe real kernel capacity-failure probe using `/dev/full` when exposed, producing ENOSPC without touching authoritative JANUS storage.
