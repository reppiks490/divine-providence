# Infrastructure STATE CAPSULE v29

Authoritative checkpoint: Infrastructure Supervisory Loop V29 (verified
offline/package checkpoint).

Artifact: `infrastructure_supervisory_loop_v29.zip` SHA-256:
`eedb168c2941d7a4200db9fba43d8831b28367e83709f3ff15309a94e4e2e817`
Parent V28 SHA-256:
`c02bd9029e24c0447f4de6c210bd8634fd93d34ecbb5da1e49577bd6ecc779c0`
Commit ID: none; this checkpoint was built and verified as a packaged
local artifact, not committed to an attached repository.

## Completed

V29 wires authenticated recovery evidence into opt-in startup proof
restoration through `LoopConfig.recovery_authenticator`. When
authentication is configured with `recovery_chain_dir`, historical proof
restoration requires the append-only integrity chain and authenticated
sidecar chain to both verify, match generation-for-generation, and bind
the same recovery checkpoints before continuity can restore proof. Wrong
producer/key, unknown key ID, signature tamper, algorithm/version
mismatch, unsigned downgrade, authentication/integrity-chain divergence,
or authenticated append failure fail closed for restored proof while
unrelated supervision remains fail-open.

V29 also adds explicit key IDs and `HMACRecoveryKeyring`. The keyring
verifies historical entries signed by any configured trusted key ID
while exactly one active signing key signs new recovery evidence,
enabling controlled key rotation. Authentication remains evidence-only
and exposes no infrastructure mutation authority.

## Verification

V28 parent SHA-256 verified exactly before changes. V28 clean baseline:
171 passed. TDD RED observed: V29 tests failed at collection because
`HMACRecoveryKeyring` did not exist. Focused V29 startup/authentication
suite after implementation: 15 passed. A full regression initially
exposed a nondeterministic legacy tamper test that could leave a
signature unchanged when its final nibble was already `0`; root cause
was confirmed and the test was corrected to guarantee a changed
signature. V29 full development suite: 182 passed. Fresh extracted V29
package: 182 passed. 17 executable modules passed `py_compile`. ZIP
compressed-data integrity passed.

## Interfaces/dependencies

Updated `recovery_auth.py`: versioned envelope now carries `key_id`;
`HMACRecoveryAuthenticator(..., key_id=...)`; new
`HMACRecoveryKeyring(producer_id, keys, signing_key_id=...)`. Updated
`recovery_chain.py`: authenticated entries persist key IDs and
`AuthenticatedRecoveryChain.verify_against()` enforces one-for-one
alignment with the append-only checkpoint chain. Updated
`infrastructure_loop.py`: new `LoopConfig.recovery_authenticator`;
authenticated startup restoration gate and authenticated advancement
under the existing recovery-chain lock. Updated `README.md`,
`docs/current-state.md`, and `config.example.yaml`. No new third-party
runtime dependency.

## Blockers/risks/assumptions

DEEP RESEARCH ACTUALLY INVOKED = NO --- first-party Deep Research was
not exposed. Superpowers TDD/Systematic Debugging/Verification,
Akinator, Baton Pass and Codex Coordinator were actually invoked/read
for workflow guidance. HMAC provides shared-secret producer
authentication, not asymmetric identity, authorization, revocation,
hardware-backed signing, or compromise-resistant multi-party trust. Key
removal acts as revocation but there is no signed revocation ledger or
explicit activation/retirement epoch yet. Cross-file advancement of the
integrity chain and authenticated sidecar is serialized but not a single
atomic filesystem transaction; partial advancement fails closed on the
next startup. Recovered proof still does not repopulate positive
`OutcomeMemory`. Distributed mutation leases/events and production
canary/telemetry remain absent. READY_TO_COMMIT is not asserted for
production/live adoption.

## Tools actually used

Capability discovery; installed-skill discovery; Superpowers
systematic-debugging, test-driven-development and
verification-before-completion; Akinator; Baton Pass; Codex Coordinator;
local/container Python engineering; pytest; py_compile; ZIP
packaging/clean extraction/integrity verification; SHA-256; artifact
generation; Files/Google Drive persistence workflow.

## Next action

V30: make integrity-chain plus authenticated-sidecar advancement
recoverable as one logical transaction. Add a small write-ahead
intent/commit record or deterministic reconciliation protocol so process
death between integrity append and authenticated append can be safely
completed or quarantined without operator guesswork. Add failure
injection at every write/rename/fsync boundary and preserve fail-closed
restored trust plus fail-open unrelated supervision. Then extend key
rotation with explicit activation/retirement epochs and a signed
trust-policy manifest.

## Exact resume

1.  Verify V29 ZIP SHA-256 exactly
    `eedb168c2941d7a4200db9fba43d8831b28367e83709f3ff15309a94e4e2e817`.
2.  Clean extract and require 182 passing tests before modifications.
3.  Preserve V3-V29 safety gates, startup authentication gate, and
    sibling authority boundaries.
4.  RED/GREEN V30 logical two-chain transaction/reconciliation plus
    key-policy epoch tests.
5.  Repackage, clean-extract, compile, retest, hash, and create V30
    capsule without overwriting V29.
