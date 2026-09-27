# Infrastructure STATE CAPSULE v31

Authoritative checkpoint: Infrastructure Supervisory Loop V31 (verified
offline/package checkpoint).

Artifact: `infrastructure_supervisory_loop_v31.zip` SHA-256:
`01fb2c331011aeacea6f6e8ce3220db97ed72495b0670fb11a75f669e2674c17`
Parent V30 SHA-256:
`105fd24a681d09d45653b9667589edaf0a97274129eab5dd6378e843764566f7`

## Completed

V31 adds append-only signed recovery key-policy epochs with a trust root
separate from recovery producer keys. `RecoveryKeyPolicy` binds a
monotonically increasing policy epoch to the stable producer identity,
effective recovery generation, one active signing key, trusted
historical keys, retired keys, and monotonic revoked keys.
`HMACRecoveryKeyPolicyAuthority` signs policy epochs with a separate
policy-authority secret. `RecoveryKeyPolicyStore` verifies sequential
epochs, previous-policy linkage, stable producer identity, strictly
increasing effective generations, irreversible revocation, and a
rollback/replay-sensitive HEAD binding the latest epoch and policy hash.

`PolicyBoundRecoveryAuthenticator` binds every newly signed recovery
authentication envelope to the exact `policy_epoch` and `policy_hash`
applicable to its recovery generation. New evidence may be signed only
with that epoch's active key. Historical retired keys remain valid only
for evidence issued under policy epochs in which they were trusted.
Revoked/untrusted keys, unknown future epochs, policy/history
divergence, producer mismatch, policy tamper, and stale/rolled-back HEAD
fail closed. Because the existing startup path verifies the supplied
authenticator for every authenticated recovery entry, policy corruption
automatically prevents restored historical proof and further
authenticated advancement while unrelated supervision remains fail-open.

All new policy components remain evidence-side only and expose no
infrastructure mutation, execute, promote, rollback, acquire, or release
authority.

## Verification

V30 parent SHA-256 verified exactly before changes. V30 clean baseline:
199 passed. TDD RED observed: `ModuleNotFoundError` for the
not-yet-existing `recovery_key_policy` module. Focused V31 key-policy
suite: 12 passed. V31 full development suite: 211 passed. Fresh
extracted V31 package: 211 passed. 19 executable Python modules passed
`py_compile`. ZIP compressed-data integrity passed.

Failure/negative coverage includes: - signed genesis and multi-epoch
rotation; - policy signature tamper; - replay of a previously valid
older HEAD; - revoked-key resurrection attempt; - retired key cannot
sign a later generation; - historical retired-key verification under the
original applicable epoch; - revoked key rejected under revoked epoch; -
unknown future policy epoch rejection; - producer/key-policy mismatch; -
startup policy tamper fails closed without chain advancement; -
policy/authentication components have no infrastructure mutation
authority; - all V30 write-ahead dual-chain crash reconciliation and V29
authentication regressions remain passing.

## Interfaces/dependencies

New module: `recovery_key_policy.py`. New types: `RecoveryKeyPolicy`,
`SignedRecoveryKeyPolicy`, `HMACRecoveryKeyPolicyAuthority`,
`KeyPolicyVerdict`, `RecoveryKeyPolicyStore`,
`PolicyBoundRecoveryAuthenticator`. New documentation:
`docs/v31-key-policy-contract.md`. README updated with V31 trust model.
No new third-party runtime dependency; Python standard-library
HMAC/SHA-256 only.

## Tools/skills actually used

Capability discovery and installed-skill inventory; Superpowers
brainstorming, test-driven-development, systematic-debugging, and
verification-before-completion; Akinator; Baton Pass; Codex Coordinator;
Python/container engineering; pytest; py_compile; ZIP packaging/clean
extraction/integrity verification; SHA-256; File Library/Google Drive
persistence workflow.

## Blockers/risks/assumptions

DEEP RESEARCH ACTUALLY INVOKED = NO --- DEEP RESEARCH UNAVAILABLE.
Policy and producer authentication are still HMAC/shared-secret based
rather than asymmetric signatures or hardware-backed identities. V31 has
signed activation, retirement, and monotonic revocation semantics but no
multi-authority quorum, external trust-root distribution, or emergency
revocation broadcast protocol. Removing historical key material from the
runtime keyring can intentionally make old evidence unverifiable even if
policy history still trusts that key. Policy HEAD is
rollback/replay-sensitive inside this local durable model but not
anchored to an external transparency service. Recovered proof still does
not repopulate positive OutcomeMemory. Distributed mutation
leases/events and production canary/telemetry remain absent.
READY_TO_COMMIT is not asserted for production/live adoption.

## Next action

V32: move producer and policy authentication from shared-secret HMAC
toward asymmetric verification boundaries. Introduce signer/verifier
interfaces, key fingerprints/public-key IDs, offline-verifiable
signatures, and an externalizable trust-root manifest while preserving
V30 transaction semantics and V31 policy epochs. Add
algorithm-confusion, key-substitution, wrong-public-key, stale
trust-root, and signature-format failure injection.

## Exact resume

1.  Verify V31 ZIP SHA-256 exactly
    `01fb2c331011aeacea6f6e8ce3220db97ed72495b0670fb11a75f669e2674c17`.
2.  Clean extract and require 211 passing tests before modifications.
3.  Preserve V3-V31 gates and sibling authority boundaries.
4.  RED/GREEN V32 asymmetric signer/verifier interfaces and
    externalizable trust-root manifest.
5.  Repackage, clean-extract, compile, retest, hash, and create V32
    capsule without overwriting V31.
