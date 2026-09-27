# V35 Witness Governance and Transparency Contract

## Scope
This layer governs trust witnesses and exports audit evidence. It does not grant witness, governance, or transparency components any infrastructure mutation, canary promotion, rollback, routing, lease, or execution authority.

## Signed witness-governance epochs
Each epoch binds:
- monotonic governance epoch;
- previous governance epoch hash;
- effective trust-root generation;
- quorum threshold;
- exact witness public keys, identities, key IDs, and fingerprints.

An independent Ed25519 governance authority signs each epoch. Public-only governance verification is supported.

## Membership and threshold invariants
- Witness subject IDs are unique within an epoch.
- Threshold must fit the configured witness set.
- Threshold may not decrease.
- Effective trust-root generation must strictly increase.
- A new witness set must retain exact identity/key overlap of at least the previous quorum.
- Governance history is append-only and HEAD rollback/replay sensitive.

These rules make witness replacement gradual and auditable instead of allowing silent wholesale substitution.

## Governed trust-root view
`GovernedWitnessedTrustRootStore` validates:
1. the V33 trust-root chain;
2. the signed governance chain;
3. the governance epoch applicable to the current trust-root HEAD;
4. the V34 witness quorum using exactly that epoch's membership and threshold.

Failure of any layer denies trust-root access to recovery authentication. Historical proof restoration therefore fails closed while unrelated supervision remains fail-open.

## Verified transparency checkpoints
`TransparencyCheckpointStore.append_current(...)` derives a checkpoint only from a currently valid trust-root HEAD, valid applicable governance epoch, and a verified quorum of witness receipts.

Each signed checkpoint binds:
- checkpoint sequence and previous checkpoint hash;
- trust-root generation/hash;
- governance epoch/hash;
- exact hashes of verified current witness receipts.

The transparency chain is signed, hash-linked, and rollback/replay-sensitive.

## Gossip export and split-view detection
`export_digest()` produces a compact checkpoint digest for independent transport. `compare_transparency_gossip()` distinguishes:
- matching equal-sequence checkpoints;
- equal-sequence differing hashes: split-view/equivocation evidence;
- differing sequences: stale-peer state.

V35 does not itself provide a network gossip transport; it defines deterministic portable evidence that an external transport can exchange.

## Residual risk
The governance authority is a single configured root. V35 does not yet implement multi-governance-authority quorum, remote transparency services, witness freshness SLAs, PKI, or hardware-backed witness/governance keys. A compromised governance authority can authorize future membership changes subject to the overlap and non-decreasing-threshold rules.
