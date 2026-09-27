# Infrastructure STATE CAPSULE v32

Authoritative checkpoint: Infrastructure Supervisory Loop V32 (verified
offline/package checkpoint).

Artifact: `infrastructure_supervisory_loop_v32.zip` SHA-256:
`c265ed428e8179acd560e0142cc22d500ee49be7fd3ce80034082941a98a4ec1`
Parent V31 SHA-256:
`01fb2c331011aeacea6f6e8ce3220db97ed72495b0670fb11a75f669e2674c17`

## Completed

V32 introduces an asymmetric recovery-authentication boundary using
Ed25519 and explicit signer/verifier separation. `Ed25519RecoverySigner`
contains private signing capability; `Ed25519RecoveryVerifier` contains
only a public key. `Ed25519RecoveryKeyring` supports signing mode or
verification-only mode and binds each recovery envelope to producer
identity, key ID, algorithm, canonical payload hash, and a
domain-separated SHA-256 public-key fingerprint included inside the
signed payload.

`Ed25519RecoveryKeyPolicyAuthority` applies the same signer/verifier
separation to V31 key-policy epochs. A policy store can therefore be
written by a private policy signer and later independently verified by a
public-only authority.

`RecoveryTrustRootManifest` externalizes only public trust material:
producer identity, recovery producer public keys, policy-authority
public key, purposes, algorithms, key IDs, fingerprints, and a canonical
manifest hash. It contains no private key material and can construct
public-only recovery verification and policy-authority objects.

V32 also separates startup restoration from recovery-chain advancement.
A public-key-only recovery verifier may restore already committed
historical proof without private signing material, but it cannot
bootstrap an empty authenticated history or append a new authenticated
generation. Failure to sign new evidence no longer erases an otherwise
valid historical verification result in read-only mode.

Existing HMAC paths remain available for compatibility. The stronger V32
path depends on `cryptography>=46,<47`.

## Verification

V31 parent SHA-256 verified exactly before changes. V31 clean baseline:
211 passed. TDD RED observed: `ModuleNotFoundError` for the
not-yet-existing `recovery_asymmetric` module. Focused V32 asymmetric
trust suite: 12 passed. V32 full development suite: 223 passed. Fresh
extracted V32 package: 223 passed. 20 executable Python modules passed
`py_compile`. ZIP compressed-data integrity passed.

Failure/negative coverage includes: - private signer/public-only
verifier roundtrip; - verification-only runtime cannot sign; - wrong
public key rejection; - algorithm-confusion rejection; - public-key
fingerprint substitution rejection; - stale trust-root manifest cannot
verify a newly rotated key absent from the manifest; - trust-root
fingerprint tamper rejection; - public trust manifest contains no
private key material; - asymmetric policy authority sign/verify
separation; - policy store reopening with public-only authority; - V31
policy-bound Ed25519 key rotation; - V32 public-only startup restoration
without new authenticated append; - asymmetric components expose no
infrastructure mutation authority; - all V31 signed key-policy, V30
dual-chain transaction, and earlier safety regressions remain passing.

## Interfaces/dependencies

New module: `recovery_asymmetric.py`. New types:
`Ed25519RecoverySigner`, `Ed25519RecoveryVerifier`,
`Ed25519RecoveryKeyring`, `Ed25519RecoveryKeyPolicyAuthority`,
`TrustRootKey`, `RecoveryTrustRootManifest`. Updated
`PolicyBoundRecoveryAuthenticator` with a `can_sign` capability surface.
Updated `InfrastructureSupervisoryLoop` startup path to distinguish
verified historical restoration from ability to append new signed
recovery evidence. New documentation:
`docs/v32-asymmetric-trust-contract.md`. New runtime dependency
declaration: `cryptography>=46.0.0,<47`.

## Tools/skills actually used

Capability discovery and installed-skill inventory; Superpowers
test-driven-development, systematic-debugging, and
verification-before-completion; Akinator; Baton Pass; Codex Coordinator;
Python/container engineering; pytest; py_compile; ZIP packaging/clean
extraction/integrity verification; SHA-256; File Library/Google Drive
persistence workflow.

## Blockers/risks/assumptions

DEEP RESEARCH ACTUALLY INVOKED = NO --- DEEP RESEARCH UNAVAILABLE. V32
trust-root manifests are canonical-hash protected but are not
self-authenticating; they must be distributed/anchored through a
separately trusted channel. No transparency-log anchoring,
certificate-chain semantics, multi-authority quorum, hardware-backed
signer, remote signer protocol, or automated trust-root rotation
distribution exists yet. Existing HMAC compatibility paths remain
present and may be weaker than the Ed25519 path. Private-key
generation/import exists but V32 intentionally does not export or
persist private keys. Recovered proof still does not repopulate positive
OutcomeMemory. Distributed mutation leases/events and production
canary/telemetry remain absent. READY_TO_COMMIT is not asserted for
production/live adoption.

## Next action

V33: add trust-root anchoring and migration controls. Bind a monotonic
trust-root manifest generation to recovery/key-policy history, add
manifest rollback/replay detection, explicit algorithm migration policy
from HMAC to Ed25519, and optional multi-verifier quorum semantics. Add
trust-root substitution, stale-manifest replay, downgrade-to-HMAC,
mixed-algorithm history, and partial migration failure injection.

## Exact resume

1.  Verify V32 ZIP SHA-256 exactly
    `c265ed428e8179acd560e0142cc22d500ee49be7fd3ce80034082941a98a4ec1`.
2.  Clean extract and require 223 passing tests before modifications.
3.  Preserve V3-V32 gates and sibling authority boundaries.
4.  RED/GREEN V33 trust-root anchoring, rollback/replay protection, and
    explicit HMAC→Ed25519 migration policy.
5.  Repackage, clean-extract, compile, retest, hash, and create V33
    capsule without overwriting V32.
