# V33 Anchored Trust-Root and Algorithm Migration Contract

## Scope
V33 governs recovery-evidence trust roots and cryptographic migration only. It does not grant infrastructure execution, mutation, canary promotion, rollback, routing, or lease authority.

## External anchor boundary
A separately provisioned Ed25519 anchor authority signs every trust-root generation. The anchor may run with a private signer or as a public-only verifier. Its public key is the root-of-roots supplied through a trusted channel; V33 does not bootstrap trust in that key from the files it verifies.

## Append-only trust-root generations
Each `RecoveryTrustRootGeneration` binds:
- a monotonically increasing trust-root generation;
- the previous generation hash;
- a strictly increasing effective recovery generation;
- a complete V32 public `RecoveryTrustRootManifest`;
- a recovery algorithm migration mode.

The store writes immutable `trust-root-<generation>.json` records plus a rollback/replay-sensitive `HEAD` binding the latest generation and generation hash. Signature tamper, manifest substitution, linkage changes, generation gaps, producer substitution, stale/rolled-back HEAD, and malformed records fail closed.

## Algorithm migration state machine
Migration modes are ordered and monotonic:

`HMAC_ONLY -> DUAL -> ED25519_ONLY`

Remaining in the same mode is allowed for ordinary trust-root/key rotation. Moving backward is rejected. Skipping directly from HMAC-only to Ed25519-only is rejected so the transition window must be explicit and auditable.

## Per-generation enforcement
`MigrationAwareRecoveryAuthenticator` selects the trust-root generation whose `effective_recovery_generation` applies to the recovery checkpoint being signed or verified.

- `HMAC_ONLY`: only HMAC-SHA256 envelopes verify and new evidence is HMAC-signed when allowed.
- `DUAL`: historical/new HMAC or Ed25519 evidence may verify, but new evidence is preferentially signed with Ed25519.
- `ED25519_ONLY`: only Ed25519 envelopes verify; an otherwise valid HMAC envelope is a downgrade and fails closed.

Every migration-aware envelope is bound to the applicable `trust_root_generation` and `trust_root_hash`. Ed25519 signatures are additionally verified against the exact public keys in the applicable anchored manifest.

## Signing capability
Signing capability is evaluated against the trust root applicable to the specific recovery generation, not simply the newest trust-root file. This prevents a future-dated migration epoch from disabling a still-valid earlier signing path.

## Startup restoration
The existing V30/V32 startup recovery path accepts `MigrationAwareRecoveryAuthenticator` through the normal authentication interface. Mixed HMAC/Ed25519 history is therefore independently reverified generation by generation. Post-migration HMAC downgrade, stale trust-root replay, or root-history corruption prevents historical proof restoration and chain advancement while unrelated supervision remains fail-open.

## Residual risks
- The external anchor public key still requires separately trusted provisioning and rollback protection outside this local package.
- HMAC verification during the legacy/dual phases still depends on shared-secret material.
- V33 does not implement multi-authority/quorum trust.
- Hardware-backed/remote signing and transparency-log witnessing remain future work.
