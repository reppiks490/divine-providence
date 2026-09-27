# V45 Composite Low-Level Recovery + Gossip Evidence

The authority transaction now forwards safe low-level RECORD_WRITTEN and HEAD_WRITTEN failpoints into AuthoritySetStore. Recovery recognizes a valid next authority record with stale HEAD, validates the complete authority chain, repairs HEAD, and resumes the transaction idempotently. Invalid authority records are never repaired.

GossipReceipt binds an observer identity/key to the cryptographic hash of an exact signed remote-history head and receipt time. EquivocationEvidenceBundle requires two distinct configured observers to have valid receipts over conflicting heads for the same peer and sequence. Receipt/head substitution and non-conflicting pairs fail closed. These are evidence surfaces only and confer no mutation authority.
