# V48 Durable Gossip Provenance Index

V48 adds an append-only provenance index binding each witnessed remote-history head admission to the exact durable signed-head-chain entry and independent observer gossip receipt.

Admission verifies the receipt signature and exact remote-head hash, verifies the underlying remote-head chain, and requires the supplied provenance to identify the exact chain entry. Records are predecessor-hash-linked and HEAD-bound. Duplicate chain-entry provenance, receipt/head substitution, entry tamper, underlying head-chain tamper, and HEAD rollback fail closed. Reopen verification revalidates the remote chain and observer receipt rather than trusting stored validation state.

This is evidence-side infrastructure only. It does not authorize infrastructure mutation, promotion, routing, leases, sibling semantics, or trading actions.
