# Infrastructure STATE CAPSULE v33

Authoritative checkpoint: Infrastructure Supervisory Loop V33 (verified
offline/package checkpoint).

Artifact: `infrastructure_supervisory_loop_v33.zip` SHA-256:
`b75fa74151d405411493c43a424234ef9bc6e543a0aefce79ed807274b881723`
Parent V32 SHA-256:
`c265ed428e8179acd560e0142cc22d500ee49be7fd3ce80034082941a98a4ec1`

## Completed

V33 adds an independently Ed25519-anchored, append-only trust-root
generation chain and explicit recovery-algorithm migration policy.
`RecoveryTrustRootGeneration` binds generation number, previous
generation hash, effective recovery generation, complete V32 public
`RecoveryTrustRootManifest`, migration mode, and canonical generation
hash. `RecoveryTrustRootAnchorAuthority` signs each generation with a
separately provisioned Ed25519 anchor key and can operate as a
public-only verifier. `RecoveryTrustRootStore` verifies signatures,
sequential linkage, stable producer identity, strictly increasing
effective recovery generations, and a rollback/replay-sensitive HEAD.

Migration modes are monotonic: `HMAC_ONLY -> DUAL -> ED25519_ONLY`.
Same-mode trust-root rotation is permitted; backward migration and
skipping the DUAL transition are rejected.
`MigrationAwareRecoveryAuthenticator` selects the root applicable to
each recovery generation, binds every envelope to
`trust_root_generation` plus `trust_root_hash`, permits HMAC only under
HMAC_ONLY/DUAL, preferentially signs Ed25519 in DUAL, and rejects HMAC
after ED25519_ONLY becomes effective. Ed25519 evidence is verified
against the exact public keys in the applicable anchored manifest.

Signing capability is generation-aware via `can_sign_for_generation`,
preventing future-effective root epochs from incorrectly disabling the
currently applicable signing path. `InfrastructureSupervisoryLoop`
consults this generation-specific capability before appending
authenticated recovery evidence.

The actual startup recovery flow was verified across a three-generation
HMAC -\> DUAL/Ed25519 -\> ED25519_ONLY history. Replacing the
generation-3 Ed25519 envelope with a syntactically valid HMAC envelope
causes restored proof to fail closed without advancing the integrity
chain.

## Verification

V32 parent SHA-256 verified exactly before changes. V32 clean baseline:
223 passed. TDD RED observed: `ModuleNotFoundError` for not-yet-existing
`recovery_trust_root`. Focused V33 trust-root/migration suite: 11
passed. V33 full development suite: 234 passed. Fresh extracted V33
package: 234 passed. 21 executable Python modules passed `py_compile`.
ZIP compressed-data integrity passed.

Failure/negative coverage includes: - independently signed trust-root
generation chain; - replay of a previously valid stale HEAD; -
trust-root manifest substitution; - recovery-algorithm downgrade
rejection; - mandatory explicit DUAL transition; - mixed HMAC/Ed25519
historical verification; - HMAC rejection after ED25519_ONLY; - wrong
trust-root generation/hash rejection; - public-only migration verifier
cannot sign; - public-only anchor verification; - future-effective root
does not disable earlier applicable signing; - end-to-end startup
HMAC-\>DUAL-\>Ed25519-only migration and downgrade tamper rejection; -
trust/authentication components expose no infrastructure mutation
authority; - all V32 asymmetric, V31 key-policy, V30 dual-chain
transaction, and earlier safety regressions remain passing.

## Interfaces/dependencies

New module: `recovery_trust_root.py`. New types:
`RecoveryAlgorithmMode`, `RecoveryTrustRootGeneration`,
`SignedRecoveryTrustRootGeneration`, `RecoveryTrustRootAnchorAuthority`,
`RecoveryTrustRootVerdict`, `RecoveryTrustRootStore`,
`MigrationAwareRecoveryAuthenticator`. Updated
`InfrastructureSupervisoryLoop` to use
`can_sign_for_generation(next_generation)` when exposed. New
documentation: `docs/v33-trust-root-migration-contract.md`.
`docs/current-state.md` updated to V33. README updated with V33
migration model. No new third-party dependency beyond V32
`cryptography>=46,<47`.

## Tools/skills actually used

Capability discovery and installed-skill inventory; Superpowers
test-driven-development, systematic-debugging, and
verification-before-completion; Akinator; Baton Pass; Codex Coordinator;
Python/container engineering; pytest; py_compile; ZIP packaging/clean
extraction/integrity verification; SHA-256; File Library/Google Drive
persistence workflow.

## Blockers/risks/assumptions

DEEP RESEARCH ACTUALLY INVOKED = NO --- DEEP RESEARCH UNAVAILABLE. The
anchor public key remains an externally provisioned root-of-roots and is
not self-authenticated by local trust-root files. No
transparency-log/witness anchoring, multi-authority quorum,
hardware-backed signing, remote signer protocol, or automated external
trust-root distribution exists yet. HMAC remains supported during
explicit legacy/DUAL generations and still depends on shared-secret
material. The current DUAL policy is verification-compatible with both
algorithms but always prefers Ed25519 for new signatures. Recovered
proof still does not repopulate positive OutcomeMemory. Distributed
mutation leases/events and production canary/telemetry remain absent.
READY_TO_COMMIT is not asserted for production/live adoption.

## Next action

V34: add externally witnessable trust-root checkpoints and optional
multi-authority quorum verification. Bind selected trust-root HEADs to
durable witness receipts, require configurable N-of-M independent
verifier agreement for high-assurance trust-root admission, and test
witness rollback/equivocation, partial quorum, signer substitution, and
offline verifier operation while preserving V30-V33 recovery semantics.

## Exact resume

1.  Verify V33 ZIP SHA-256 exactly
    `b75fa74151d405411493c43a424234ef9bc6e543a0aefce79ed807274b881723`.
2.  Clean extract and require 234 passing tests before modifications.
3.  Preserve V3-V33 gates and sibling authority boundaries.
4.  RED/GREEN V34 external witness receipts and optional N-of-M
    trust-root quorum.
5.  Repackage, clean-extract, compile, retest, hash, and create V34
    capsule without overwriting V33.
