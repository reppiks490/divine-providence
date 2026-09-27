# JANUS ∞ Run 034 — Resumable Proof-Carrying Acquisition Sessions

Run 034 extends Run 033 selective content-addressed acquisition with deterministic chained session receipts. A receiver may stop after any accepted object subset and resume without retransmitting accepted objects. Every session binds the graph/root, exact accepted object hashes and bytes, exact missing set, round number, and predecessor receipt digest.

Negative gates reject stale-root reuse, receipt rollback/tampering, cache poisoning, content substitution, and retransmission/unrequested objects. Finalization is permitted only after a complete authenticated session and re-runs Run 032 exact closure verification. `winner_selected=false` is invariant; acquisition does not acquire branch-resolution authority.
