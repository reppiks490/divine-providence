# V36 Multi-Authority Governance and Transparency Contract

V36 removes the single-approval assumption above witness governance by allowing a configured M-of-N set of Ed25519 governance authorities to approve an exact governance epoch/hash. Distinct authority identities are counted once; partial quorum, wrong epoch/hash, duplicate approvals, unknown authorities, key substitution, and signature tamper fail closed.

Independent transparency anchors can sign an exact checkpoint sequence/hash plus observation time. A configured anchor quorum is required. A valid configured anchor producing two different hashes for the same sequence is explicit equivocation evidence.

Received gossip checkpoints are subject to a bounded freshness policy, future-clock-skew limit, and minimum accepted sequence. Expired, future-dated, malformed, or rolled-back checkpoints fail closed.

All V36 objects are evidence/authentication surfaces only. They have no execute, mutate, promote, rollback, lease, routing, or production authority. Network transport, remote transparency hosting, HSM custody, and automatic authority-set governance remain outside V36.
