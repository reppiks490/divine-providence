# V47 integrated gossip provenance and deeper transaction failpoints

V47 couples observer-signed gossip receipts to signed remote-head-chain admission: receipt verification occurs before the head can be appended and returned provenance binds the durable chain entry hash to the exact remote-head hash and observer identity.

Authority transaction testing now exposes safe failure boundaries before TXN payload publication, immediately after transition-evidence persistence, and immediately after TXN unlink, in addition to existing phase and authority record/HEAD failpoints. Recovery remains deterministic and idempotent; a failure before atomic TXN publication leaves no pending state, a transition-only torn state is completed from the durable payload, and a failure after TXN unlink is already committed and verifies cleanly.

These are evidence/persistence safety mechanisms only and grant no mutation authority.
