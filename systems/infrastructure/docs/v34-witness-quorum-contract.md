# V34 Trust-Root Witness and Quorum Contract

## Scope
Witnesses attest recovery trust-root state only. They do not append trust roots, sign infrastructure actions, acquire mutation leases, promote canaries, execute changes, or authorize production.

## Receipt model
Each witness receipt binds:
- witness identity and Ed25519 public-key fingerprint;
- exact trust-root generation;
- exact trust-root generation hash;
- previous receipt hash for that witness;
- canonical receipt hash;
- Ed25519 signature.

Per-witness histories are append-only and hash-linked. A witness cannot occupy the same witness/generation slot twice.

## Quorum
`WitnessQuorumVerifier` accepts the current local trust-root HEAD only when at least N distinct configured public witness identities have valid latest receipts for that exact generation and hash.

Duplicate use of one witness identity cannot inflate quorum. Invalid, missing, substituted, or tampered receipts contribute no vote.

## Rollback/equivocation signal
If a valid witness history contains a later trust-root generation than the locally valid HEAD, the witnessed view rejects the local state as rollback. This catches consistent local truncation that would otherwise leave the local trust-root chain internally valid.

## Runtime integration
`WitnessedTrustRootStore` is a read-only high-assurance view over an existing V33 `RecoveryTrustRootStore`. `MigrationAwareRecoveryAuthenticator` consumes it through the existing trust-root interface. If witness quorum fails, recovery authentication fails; historical proof restoration therefore fails closed while unrelated supervision remains fail-open.

## Offline verification
Witness verification uses only public Ed25519 keys. Offline/public-only verifiers cannot sign receipts and do not require private witness key material.

## Residual risk
V34 witnesses are independently configured but are not yet connected to an external transparency log, network gossip protocol, witness freshness SLA, certificate PKI, or hardware-backed witness keys. A quorum of colluding or simultaneously compromised witnesses can still attest a false root.
