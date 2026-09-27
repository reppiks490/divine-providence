# V32 Asymmetric Recovery Trust Contract

## Scope
This layer authenticates recovery evidence and key-policy history only. It grants no infrastructure mutation, canary promotion, rollback, lease, routing, or execution authority.

## Algorithms
V32 uses Ed25519 through `cryptography>=46,<47`.

## Capability separation
- `Ed25519RecoverySigner` contains private signing capability.
- `Ed25519RecoveryVerifier` contains only a public key and cannot sign.
- `Ed25519RecoveryKeyring` may be signing-capable or public-verification-only.
- `Ed25519RecoveryKeyPolicyAuthority` may likewise operate with a private signer or public-only verifier.

A verification-only runtime can restore already committed authenticated proof without obtaining private key material. It cannot bootstrap or append a new authenticated generation.

## Public-key identity
Every recovery signature binds:
- producer identity;
- key ID;
- algorithm;
- public-key fingerprint;
- canonical payload hash;
- canonical payload.

The public-key fingerprint is SHA-256 over the domain-separated raw Ed25519 public key. Key substitution, wrong-public-key verification, algorithm confusion, payload substitution, and fingerprint substitution fail closed.

## Trust-root manifest
`RecoveryTrustRootManifest` is an externalizable public trust anchor containing:
- stable producer identity;
- one or more producer public keys;
- policy-authority public key;
- key purposes;
- key IDs;
- algorithms;
- fingerprints;
- canonical manifest hash.

The manifest contains no private key material. It is intended to be distributed through a separately trusted channel. V32 does not claim the manifest is self-authenticating merely because it contains a hash.

## Policy integration
`PolicyBoundRecoveryAuthenticator` can wrap an Ed25519 recovery keyring. V31 policy epochs still determine which key ID is active, trusted, retired, or revoked for each recovery generation. Public-key verification enforces the same policy history without requiring the corresponding private signing key.

## Startup behavior
When authenticated history is valid but the configured authenticator is verification-only:
- historical proof may restore;
- no new authenticated generation is appended;
- an empty authenticated history cannot be bootstrapped without a private signer;
- unrelated supervisory behavior remains fail-open.

## Residual risk
V32 introduces an externalizable public trust root but does not yet provide:
- transparency-log anchoring;
- multi-authority/quorum trust;
- hardware-backed private keys;
- remote signer protocols;
- certificate-chain semantics;
- automated trust-root rotation/revocation distribution.
