# V30 Dual-Chain Recovery Transaction Contract

V30 coordinates only recovery evidence persistence. It has no adapter execution, mutation, promotion, rollback, lease, or production authority.

For authenticated recovery generations the durable order is: acquire `RecoveryChainLock`; verify/reconcile older transaction history; persist a hash-bound intent; append the integrity checkpoint if absent; append authenticated evidence if absent; verify exact checkpoint alignment; persist a commit marker binding the intent hash, integrity-chain hash, and authenticated-entry hash; then evaluate restoration/advance eligibility.

An incomplete intent is recoverable only when the prior integrity head and every surviving partial side exactly match the intent. Missing sides may then be completed idempotently. A both-sides-complete state may receive its missing commit marker. Any conflicting surviving evidence fails closed and writes a diagnostic quarantine marker without deleting or rewriting the original evidence.

A committed generation is trusted by this layer only if its intent and commit hashes verify, both recovery chains independently verify, both sides contain the same checkpoint, and the commit marker binds the observed integrity and authenticated entry hashes. Missing V30 transaction history is never synthesized for legacy generations.
