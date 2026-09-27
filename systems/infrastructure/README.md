
# Infrastructure Supervisory Loop

A fail-open, adapter-driven control plane that sits **around** infrastructure rather than becoming a hard dependency inside it.

## Core loop

`OBSERVE → MODEL → PROPOSE → GUARD → SNAPSHOT → ACT → VERIFY → ROLLBACK? → LEARN → JOURNAL`

The intent is to let one reusable loop supervise many systems without blocking their normal operation.

## Design properties

- **Outer-loop architecture:** components keep working if the loop stops.
- **Shadow mode first:** generate decisions without applying them.
- **Bounded autonomy:** mutation count, cooldowns, confidence floors, risk ceilings.
- **Low blast radius:** prefers tune / route operations before restart / repair.
- **Snapshot + rollback:** every mutation gets a pre-action snapshot.
- **Canary-style verification:** health is checked after every action.
- **Outcome learning:** realized gains update future action utility.
- **Drift / anomaly detection:** rolling z-score detector included.
- **Fail-open observer errors:** telemetry problems do not become target outages.
- **Adapter boundary:** Kubernetes, Docker, databases, queues, CI, model workers, data pipelines, etc. can all be integrated without changing the loop core.
- **Journal:** every proposal, approval, execution, verification, rollback, and cycle summary is append-only JSONL.

## Start safely

Keep:

```python
LoopConfig(shadow_mode=True)
```

Run it against real telemetry first. Inspect the journal and verify that its proposed actions make sense. Only then enable mutations.

## Production adapter contract

Each infrastructure target implements:

```python
class InfraAdapter(Protocol):
    name: str
    async def collect_signals(self) -> Sequence[Signal]: ...
    async def health(self) -> HealthReport: ...
    async def snapshot(self) -> Dict[str, Any]: ...
    async def execute(self, action: ProposedAction) -> Tuple[bool, str]: ...
    async def rollback(self, snapshot: Dict[str, Any], action: ProposedAction) -> Tuple[bool, str]: ...
```

That separation is the important part: the loop has **authority through adapters**, but it is not embedded in the service itself.

## Recommended infrastructure layers

1. **Telemetry plane**
   - latency
   - error rate
   - queue depth
   - CPU / RAM / disk / GPU
   - dependency health
   - saturation
   - model-worker throughput
   - data freshness
   - CI failure rate

2. **State model**
   - per-component health score
   - confidence
   - dependency graph
   - recent incidents
   - change history
   - capacity headroom
   - regime / drift state

3. **Action planner**
   - tune
   - reroute
   - shed load
   - scale
   - restart
   - repair
   - isolate
   - rollback

4. **Safety governor**
   - mutation budget
   - action-specific risk ceilings
   - cooldown
   - reversibility requirement
   - blast-radius constraints
   - maintenance windows
   - deny lists
   - approval escalation for high-risk actions

5. **Verification / learning**
   - pre/post health
   - causal attribution confidence
   - rollback triggers
   - realized utility
   - action success history
   - decaying memory to avoid stale behavior

## Suggested next extensions

- Dependency graph and causal propagation.
- Multi-objective optimizer for latency, cost, reliability, and throughput.
- Change-point detector in addition to z-score anomaly detection.
- Separate fast/slow loops:
  - fast loop: seconds, only low-risk reversible actions
  - slow loop: minutes/hours, optimization and capacity planning
- Consensus planner: rules + optimizer + learned policy must agree before high-risk actions.
- Git-aware configuration rollback.
- Kubernetes adapter with namespace / deployment blast-radius limits.
- CI/CD adapter that freezes risky deployments during degraded infrastructure.
- Chaos/simulation environment so policies can be trained away from production.
- Human approval queue for medium/high-risk actions.


## v2 safety hardening

- Observer failures are now treated as **uncertainty, never target degradation evidence**.
- Planner confidence can no longer be artificially raised above the health report's confidence.
- `max_concurrent_collectors` is now enforced with a semaphore, bounding telemetry fan-out.
- Regression tests cover observer-failure fail-open behavior, confidence gating, and collector concurrency.

## v3 safety hardening

- Outcome memory remains **advisory**: historical success can adjust expected utility but cannot raise confidence in current telemetry.
- `canary_required_above_risk` is now an active fail-closed gate. Because no genuine staged-canary executor exists yet, above-threshold actions are denied rather than mislabeled as canaries.
- `critical_health_floor` is now an active guard: high-impact autonomous `RESTART`, `SCALE`, `REPAIR`, and `ISOLATE` actions require explicit current health context and are denied below the floor, while low-impact reversible recovery actions may remain eligible.
- The cycle passes current component health into the guard so the health-floor policy is enforced in real loop operation.
- See `docs/safety-contract.md` for the contract future agents and adapters must preserve.

## V4 topology-aware blast-radius safety

V4 adds an optional, operator-supplied topology safety layer in `topology_governor.py`. It is a **constraint layer only**: it cannot propose actions or acquire authority that the planner/guard did not already have.

When a `TopologyModel` is supplied, locally approved mutations are additionally checked for explicit authority ownership, transitive downstream impact, critical downstream dependencies, redundancy-group minimum healthy capacity, failure-domain conflicts, and process-local mutation leases. High-impact actions against components missing from the topology fail closed. Low-impact reversible actions may remain eligible with unknown topology, preserving bounded fail-open behavior.

`MutationLeaseManager` is deliberately process-local. It prevents correlated mutations inside one supervisor process/cycle; it is **not** a distributed lock and must not be represented as cross-controller protection. A future distributed lease backend may implement that contract without weakening these local rules.

V3's canary and critical-health gates remain unchanged. V4 does not provide a genuine staged-canary executor; above-threshold actions remain fail-closed.

## V5 proof-carrying staged canaries

V5 adds `canary_executor.py`. Above-threshold actions can proceed only when an explicit `StagedCanaryExecutor` is installed **and** the target adapter implements the stage/promote/abort contract. Promotion follows independent health verification; regression or telemetry loss aborts the staged change. Every attempt emits a SHA-256 `CanaryProof` journal record. The default remains fail-closed and no production canary adapter is bundled.

## V6: proof integrity + conservative causal eligibility

V6 separates "execution succeeded" from "the learner may credit this action." Canary proof hashes are independently recomputable for integrity, and positive OutcomeMemory learning requires proof-backed causal eligibility. Flat or regressing canary outcomes receive no positive learning credit even if a permissive canary policy allowed promotion. Proof hashes are integrity checks, not signatures.

## V7 counterfactual attribution foundation

`attribution.py` introduces deterministic counterfactual evidence evaluation for learning. Positive OutcomeMemory credit now requires V6 causal proof plus V7 attribution eligibility. Explicit controls are preferred; a conservative stable pre-trend fallback is available; contaminated, malformed, low-confidence, or insufficient evidence earns no positive learning credit. The module has no mutation authority.

## v8 evidence acquisition boundary

V8 adds `evidence_provider.py`: a read-only provider/collector boundary that can assemble V7 attribution observations from bounded telemetry windows, explicitly bound controls, mutation events, and protected-scope events. It never selects a control and has no mutation authority. Provider failures fail closed for positive learning while leaving target infrastructure fail-open. The in-memory provider is for tests/replay only; no production telemetry adapter is claimed.

## v9 proof-envelope integrity

V9 adds a pure `proof_envelope.py` evidence-binding layer. It requires and orders guard, topology, lease, canary, evidence, and attribution stages; binds them to one action identity; detects omission, duplication, reordering, substitution, tampering, stale/future envelopes; and provides an independent verifier with no mutation authority. SHA-256 is used only for integrity detection, not signing or attestation. Main-loop envelope emission is intentionally deferred to the next integration increment so evidence is captured at source rather than reconstructed.

## V10 source-native proof receipts

V10 adds `source_receipts.py`. Decision-boundary evidence can now be emitted as immutable,
hash-bound `DecisionReceipt` objects and assembled into the V9 proof envelope without
reconstructing missing stages. Assembly requires exactly one receipt in canonical order
for guard, topology, lease, canary, evidence, and attribution; one action identity;
intact receipt hashes; and monotonic source chronology. The assembler has no mutation
or lease authority. This is offline integrity plumbing, not signing, attestation, live
repository adoption, or production execution.

### V11 checkpoint

V11 integrates source-native decision receipts into the supervisory cycle and emits an
independently verified Guard→Topology→Lease→Canary→Evidence→Attribution proof envelope.
Optional read-only evidence acquisition can now feed V7 attribution directly; absence
of evidence prevents positive learning without becoming an infrastructure outage
source. SHA-256 envelope integrity is not a signature or authorization credential.

## V12 — Unique Intervention Identity

V12 separates action content identity from execution occurrence identity. `ProposedAction.fingerprint`
continues to identify *what* action was requested, while each candidate receives a UUIDv4
`intervention_id` identifying *which exact occurrence* is being processed. Lease ownership and
read-only attribution evidence requests carry this intervention identity.

Mutation evidence may suppress only an event carrying the exact same non-empty intervention ID.
Matching action fingerprints, event IDs, component names, or timestamps are never sufficient to
classify an event as self-mutation. Legacy/missing intervention IDs therefore remain conservative
contamination evidence. This prevents repeated identical actions from being conflated while allowing
a production event provider to distinguish the supervisor's own mutation from truly concurrent
mutations.

The intervention ID is correlation metadata, not authorization, authentication, or attestation.


## V13 — immutable mutation lifecycle receipts
V13 binds each exact intervention occurrence to an append-only hash-chained mutation lifecycle receipt: creation, lease disposition, mutation start, completion/failure, and lease release disposition. The verified receipt hash is attached to ActionResult and the full receipt is journaled. Receipts are integrity/correlation evidence only; they grant no mutation authority, authentication, signing, or attestation.

## V14 — receipt-bound mutation-event correlation
V14 hardens causal contamination handling: a provider mutation event is excluded as this supervisor's own intervention only when both the exact intervention ID and exact V13 mutation-receipt hash match the EvidenceRequest. Intervention identity alone is no longer sufficient. Missing, legacy, forged, or mismatched receipt bindings remain conservative contamination evidence. This binding is correlation/integrity evidence, not authentication or authorization.

## V15 — atomic proof journal transaction + replay verifier
V15 adds `proof_journal.py`. For executed actions with a verified proof envelope, the supervisor now emits one canonical `proof_transaction` JSONL record containing the complete `ActionResult`, `ProofEnvelope`, and `MutationReceipt`, bound by a transaction SHA-256. An independent replay verifier rejects transaction tampering, cross-intervention substitution, action mismatch, result/envelope/receipt hash mismatch, invalid receipt chains, and invalid/expired proof envelopes. The transaction/verifier are integrity and recovery evidence only and expose no mutation authority. Existing individual journal records remain for observability/backward compatibility; the transaction is the complete replay unit.

## V16 — crash-resilient durable proof journal
V16 adds a framed, checksummed append-only durable journal with optional fsync on append, startup recovery scanning, last-good-offset identification, truncated/corrupt-tail detection, duplicate-intervention detection, and explicit tail quarantine/truncation. Recovery accepts only complete SHA-256-verified frames. Corrupt or partial evidence is excluded from proof/positive learning rather than converted into mutation authority or infrastructure downtime. This is an offline persistence primitive; production filesystem/disk semantics still require deployment-specific validation.

## V17 — durable proof sink integration and restart replay
V17 optionally wires V16 `DurableProofJournal` into the verified proof-transaction path. A transaction is framed only after V15 replay verification succeeds. Startup/recovery can scan complete frames, reconstruct typed proof transactions, and independently replay-verify each before restoring proof status. Invalid transactions and corrupt/truncated tails do not regain proof status; durable-sink failure is journaled and does not manufacture mutation authority or stop unrelated infrastructure operation. The durable sink remains opt-in through `LoopConfig.durable_proof_journal_path`.


## V18 — startup recovery policy
Corrupt/truncated tails are quarantined at the last verified frame boundary. Recovered transactions are independently replay-verified; duplicates, replay failures, or any originally damaged tail keep restored proof and positive-learning eligibility fail-closed. Recovery decisions are hash-bound and grant no mutation authority.

## V19 — opt-in startup recovery integration
V19 wires the V18 recovery policy into `InfrastructureSupervisoryLoop` construction behind `startup_recovery_enabled`. Clean independently replay-verified transactions may be restored into the in-memory recovered-proof set. Damaged tails, duplicates, replay rejection, or recovery exceptions restore no proof; recovery exceptions remain fail-open for unrelated supervisory operation. `startup_recovery_now` exists for deterministic/offline replay testing and should normally remain unset.

## V20 — atomic recovery-decision checkpoint
V20 can persist the startup RecoveryDecision as a separate atomic, checksummed checkpoint. The checkpoint binds the journal path, recovery decision hash, last-good byte offset, original file size/tail state, proof-restoration eligibility, and exact accepted proof-transaction hashes. It is written via temp-file + fsync + atomic replace and can be independently verified against the in-memory RecoveryDecision. Tampered, truncated, stale/substituted checkpoints are rejected. Checkpoint persistence failure is evidence-side only and does not stop unrelated infrastructure supervision.

## V21 — recovery-history continuity
When a recovery checkpoint path is configured, restored proof now requires a valid prior checkpoint whose journal identity, last-good boundary, and accepted transaction sequence are a monotonic prefix of the current independently verified recovery. Missing prior checkpoints bootstrap the continuity chain but restore no historical proof on that startup. Rollback, substitution, fork/divergence, or checkpoint-read failure fail closed for restored proof while unrelated infrastructure supervision remains fail-open.

## V22 — append-only recovery checkpoint chain
V22 preserves recovery checkpoints as immutable generation files linked by `previous_checkpoint_hash`, with an atomically advanced HEAD pointer. Full-chain verification rejects generation gaps, stale HEAD replay, tampered historical entries, and forked linkage. This strengthens recovery continuity without adding infrastructure mutation authority or enabling recovered positive learning.

## V23 — startup chain integration and serialized advancement
The V22 append-only recovery chain is now an opt-in startup trust path via `LoopConfig.recovery_chain_dir`. Complete-chain verification precedes historical proof restoration. The first clean startup is bootstrap-only; subsequent startup restores proof only when the prior chain head continuously extends into the current independently replay-verified recovery. Stale HEAD, gaps, tamper/fork, or append-lock contention fail closed for restored proof and do not stop unrelated supervision. Chain advancement is serialized with an interprocess lock file. Positive-learning restoration remains disabled.

## V24 — lease-identity recovery-chain lock
Recovery-chain serialization now uses nonce-bound owner metadata and conservative stale-owner reclamation. A lock may be reclaimed only after its age threshold and only when the recorded PID is definitively absent. Malformed or unverifiable locks fail closed. Release is compare-before-delete against the exact nonce-bound owner, preventing an old owner from deleting a successor/substituted lock. This mechanism serializes recovery evidence only and grants no infrastructure mutation authority.


## V25 — boot/process identity lock hardening
Recovery-chain lock owners now carry format version 25, boot identity, process-start identity, nonce, and a canonical owner fingerprint. Stale reclamation requires age plus definitive death or identity mismatch; malformed/legacy/tampered ownership fails closed. Future wall-clock timestamps are never reclaimed.


## V26 — pluggable process identity
Recovery serialization now consumes a ProcessIdentityProvider. Linux uses /proc boot ID and process-start ticks; unsupported/unavailable identity fails closed for lock acquisition and never proves stale-owner mismatch. Provider injection enables deterministic portability and failure testing without weakening V25 ownership checks.


## V27 — identity assurance and recovery producer authentication
Process identity providers now advertise explicit assurance. Recovery evidence can be wrapped in an HMAC-SHA256 producer-authentication envelope whose API has no infrastructure mutation authority. This is an authentication foundation, not production key management or authorization.


## V28 — authenticated recovery-chain evidence
Adds an opt-in authenticated recovery evidence chain binding each RecoveryCheckpoint to a versioned HMAC-SHA256 producer envelope. Verification rejects signature tamper, wrong producer/key, unsigned downgrade, generation mismatch, and checkpoint-binding corruption. This is evidence authentication only: it grants no mutation authority and is not yet wired as a mandatory startup-restoration gate.

## V29 — authenticated startup restoration gate and key rotation
When `LoopConfig.recovery_authenticator` is configured together with `recovery_chain_dir`, startup proof restoration now requires both the V22 integrity chain and the V28 authenticated evidence chain to be complete, valid, generation-aligned, and checkpoint-aligned before historical proof can be restored. Wrong producer/key, unknown key ID, signature tamper, version/algorithm mismatch, unsigned downgrade, authenticated/integrity-chain divergence, or authentication append failure fail closed for restored proof while unrelated infrastructure supervision remains fail-open. `HMACRecoveryKeyring` allows old trusted key IDs to verify historical entries while exactly one configured active key signs new entries. Authentication remains evidence-only and grants no mutation authority.

## V30 — crash-reconcilable dual-chain recovery transaction
Authenticated recovery advancement is now wrapped in a write-ahead intent/commit protocol via `RecoveryDualChainCoordinator`. Under the existing `RecoveryChainLock`, each new checkpoint first persists a hash-bound intent, then advances the integrity and authenticated evidence chains, and finally persists a commit marker binding the exact integrity-chain hash and authenticated-entry hash. On restart, incomplete intents are deterministically reconciled: a missing side may be completed only when the surviving side and prior head exactly match the intent; both-complete/no-commit states receive the missing commit marker; mismatches fail closed and receive a durable quarantine marker while preserving original evidence. Intent/commit writes use temp-file + flush/fsync + atomic replace + directory fsync. Legacy authenticated V29 chains with no V30 transaction history fail closed rather than silently fabricating commit history. These mechanisms mutate recovery evidence only and grant no infrastructure mutation authority.


## V31 — signed recovery key-policy epochs
V31 separates recovery-producer keys from a policy-authority trust root. Append-only signed policy epochs bind an effective recovery generation to exactly one active signing key while explicitly recording trusted historical keys, retired keys, and monotonic revocations. `PolicyBoundRecoveryAuthenticator` injects the applicable `policy_epoch` and `policy_hash` into every newly signed recovery envelope and rejects policy rollback/replay, unknown epochs, producer mismatch, revoked keys, policy/history divergence, and use of a retired/non-active key for new recovery evidence. These components authenticate evidence only and expose no infrastructure mutation authority.


## V32 — asymmetric recovery trust boundaries
V32 introduces Ed25519 signer/verifier separation for recovery evidence and key-policy authority. Private signing capability is optional and isolated from public verification. `Ed25519RecoveryKeyring` may run in verification-only mode with no private key and can restore already committed authenticated history without appending a new generation. Every Ed25519 recovery envelope binds its public-key fingerprint inside the signed payload. `RecoveryTrustRootManifest` externalizes only public keys, fingerprints, purposes, producer identity, and a canonical manifest hash.

The asymmetric layer depends on `cryptography>=46,<47`. Existing HMAC paths remain supported for compatibility, but V32 establishes the stronger path for future migration.

## V33 — anchored trust-root generations and HMAC→Ed25519 migration
V33 adds an externally verified Ed25519 anchor over append-only trust-root generations. Each generation binds the complete public trust manifest, previous generation hash, effective recovery generation, and a monotonic migration mode. The allowed migration is `HMAC_ONLY -> DUAL -> ED25519_ONLY`; rollback or skipping the transition is rejected. `MigrationAwareRecoveryAuthenticator` binds each recovery envelope to the exact applicable trust-root generation/hash and rejects post-migration HMAC downgrade while preserving independently verifiable mixed-algorithm history during the explicit transition window.


## V34 — witnessed trust-root checkpoints and N-of-M quorum
V34 adds externally witnessable trust-root receipts. Independent Ed25519 witness identities attest exact trust-root generation/hash pairs in append-only per-witness histories. `WitnessQuorumVerifier` can require a configurable N-of-M distinct public witness identities to agree on the current trust-root HEAD before a witnessed trust-root store exposes history to the recovery authenticator.

A newer valid witness history detects local rollback even when the local trust-root files and HEAD are consistently truncated to an older valid generation. Partial quorum, signer substitution, signature tamper, receipt-linkage breakage, and mismatched generation/hash fail closed. Public-only witness verifiers require no private signing material and gain no infrastructure mutation authority.


## V35 — signed witness-set governance and transparency checkpoints
V35 governs the V34 witness layer with an independent Ed25519-signed append-only witness-governance chain. Governance epochs bind an effective trust-root generation to an exact public witness set and quorum threshold. Threshold reduction is rejected, witness subjects are unique, and witness-set rotation requires overlap of at least the prior quorum using exact identity/key fingerprints, preventing silent full-set substitution.

`GovernedWitnessedTrustRootStore` derives its public verifier set and threshold from the governance epoch applicable to the current trust-root HEAD. Governance rollback/replay therefore fails closed for recovery trust even when trust-root and witness receipt files remain intact.

V35 also adds signed, hash-linked transparency checkpoints that bind the current trust-root HEAD, applicable witness-governance epoch, and the exact verified witness receipt hashes that satisfied quorum. Checkpoints can be exported as compact gossip digests. Comparing equal-sequence checkpoints with different hashes produces explicit split-view/equivocation evidence; differing sequences are reported as stale-peer state rather than falsely labeled equivocation.


## V36 — multi-authority governance approval and external transparency anchors
V36 adds configurable M-of-N Ed25519 approval for witness-governance epoch hashes, duplicate/substitution resistance, independent M-of-N transparency anchor receipts, explicit same-sequence fork/equivocation detection, and received-checkpoint freshness/rollback policy. These components authenticate governance/transparency evidence only and expose no infrastructure mutation authority.

## V38 — crash-reconcilable composite governance
V38 binds witness-governance persistence and M-of-N approval admission through a durable intent/reconciliation protocol. Quorum is checked before writes; torn states after either component write are deterministically reconciled and recovery is idempotent. Composite verification requires matching epoch/hash across both chains. V38 also gates imported transparency checkpoints on freshness/anti-rollback policy plus independent transparency-anchor quorum.

## V39 — journaled governance transaction state machine
V39 introduces an append-only transaction journal with explicit PREPARED → GOVERNANCE_WRITTEN → ADMISSION_WRITTEN → COMMITTED phases. Every phase is hash-linked, HEAD-bound, and directory-fsynced when durability is enabled. Phase skipping, regression, stale HEAD replay, and journal tamper fail closed. The journal remains evidence/persistence safety infrastructure only and grants no mutation authority.

## V40 — journal-integrated composite governance
V40 replaces the V38 simple intent coordinator with the V39 PREPARED → GOVERNANCE_WRITTEN → ADMISSION_WRITTEN → COMMITTED journal. M-of-N approval is checked before PREPARED; durable recovery payload permits deterministic restart completion; journal tamper and pending state fail closed; recovery is idempotent.

## V41 — governance-authority epochs and remote transparency history
V41 governs the governance-authority set itself with non-decreasing threshold and prior-quorum exact-key overlap, and adds append-only per-peer remote transparency histories with rollback and cross-log disagreement detection.

## V42 — recursive authority governance + verified remote transparency history
V42 requires each non-genesis authority-set epoch to be approved by the previous authority quorum and adds verified-only admission into append-only remote transparency histories. Partial prior quorum, authority substitution, transition tamper, stale evidence, anchor partial quorum, sequence rollback/gaps, and cross-log disagreement fail closed.

## V43 — crash-reconciled authority transitions and signed remote-history heads
V43 composes recursive previous-quorum authority transition approval with base authority-set persistence through a durable recovery payload. It also adds signed remote transparency history heads with monotonic sequence/time verification. Both remain evidence-side only.

## V44 — low-level authority durability and signed remote-head chains
V44 adds safe authority record/HEAD failpoints with validation-gated HEAD repair, plus append-only signed remote transparency-head histories with temporal split-view comparison. Evidence-side only.

## V45 — composite low-level authority recovery and cross-signed gossip evidence
V45 integrates V44 authority record/HEAD torn-write repair into the crash-reconciled authority transaction and adds cross-signed remote-head gossip receipts plus portable two-observer equivocation evidence bundles. Evidence-only authority boundaries remain unchanged.

## V48 — durable witnessed-head provenance
`recovery_provenance_index.py` persists a predecessor-linked, HEAD-bound index connecting each signed remote-history-head chain entry to the independently signed gossip receipt that witnessed it. Reopen verification revalidates both the underlying head chain and receipt, and fails closed on substitution, duplicate provenance, tamper, or rollback.

## V49 atomic witnessed provenance
V49 adds `AtomicWitnessedProvenanceStore`, crash-reconciling signed remote-head admission with the durable provenance index through an integrity-bound TXN payload. Recovery completes only missing state and verifies exact head/provenance agreement before commit; pending/tampered state fails closed.
