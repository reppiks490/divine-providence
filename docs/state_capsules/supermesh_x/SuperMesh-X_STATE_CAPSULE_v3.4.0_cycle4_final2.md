# SuperMesh-X STATE CAPSULE — v3.4.0 cycle 4 final2

## Version / lineage
- Candidate version: `3.4.0`
- Protected stable baseline: v3.1.0, SHA-256 `1a4a9e24129c88cddc54cf8f046c2051385e8414d4771f62b8989f46ac4f1e24`.
- Immediate worker-local predecessor: v3.3.0 cycle 3.
- Protected promotion rule: no later candidate becomes READY_TO_COMMIT until independently verified by the MASTER LOOP GOVERNOR.
- No Git commit identity is available in this packaged workspace; artifact SHA-256 is the release identity.

## Completed work
- Added versioned Ed25519 witness-policy epochs with thresholds, explicit revocations, duplicate-public-key alias rejection, and authority-bearing metadata rejection.
- Added exactly-one-epoch, dual-threshold key/quorum rotation requiring authorization under both the current and next policy.
- Bound epoch-aware RFC9162 checkpoint signatures to `policy_epoch` and `policy_digest` while preserving legacy v3.3 registry/checkpoint behavior.
- Added crash-consistent hash-chained gossip journal persistence and authenticated replay, including fsync-before-observation ordering, stale-policy rejection for new appends, rollback/equivocation checks, and replay across historical policy epochs.
- Added deterministic `supermesh-json-v1` Ed25519 cross-runtime conformance vectors without exposing private seed/key material.
- Updated executable smoke coverage, manifest version/capabilities, `CHANGELOG_V340.md`, and `references/witness-policy-epochs.md`.

## Test-first / verification evidence
- RED phase observed before implementation: missing-module failures for the new policy/journal/vector modules.
- New v3.4 focused tests: `12 passed`.
- Integrated trust/witness surface: `52 passed`.
- Full source-tree regression: `328 passed`.
- Explicit security/failure-injection selection: `82 passed` across policy rotation, gossip crash/replay, RFC witness behavior, legacy transparency, signed evidence, key rotation, private-source firewalls, execution authority, and workspace isolation.
- Syntax/compile: PASS using external bytecode cache to avoid a read-only extraction-directory artifact.
- Executable smoke: PASS with `package_version=3.4.0` and `witness_policy_epochs=true`.
- Package validator: PASS.
- Cache cleanup: completed before final ZIP creation.
- ZIP integrity: PASS.
- Exact persisted Drive artifact was materialized back and freshly extracted; on that exact artifact:
  - full regression: `328 passed`;
  - compile: PASS;
  - smoke: PASS;
  - package validator: PASS.

## Artifact identity / locations
- Durable artifact: `/Google Drive/Icarus Governance/SuperMesh-X/supermesh_x_v3_4_0_cycle4.zip`
- Drive file id: `external-gdrive:file:1jNwCWZopr4z_TsWecz74VizcjRwWzwvJ`
- Artifact SHA-256: `d7134590b97446e2e0d19943ff9430990a03f6a0b0613131c16d7a549208079e`
- Existing cycle capsule: `/Google Drive/Icarus Governance/SuperMesh-X/SuperMesh-X_STATE_CAPSULE_v3.4.0_cycle4.md`
- Existing post-upload audit capsule: `/Google Drive/Icarus Governance/SuperMesh-X/SuperMesh-X_STATE_CAPSULE_v3.4.0_cycle4_final.md`
- This capsule is a new final verification record and does not overwrite either earlier capsule.

## Interfaces / dependencies
- Python 3.
- `cryptography` Ed25519 APIs.
- Existing v3.3 `RFC9162WitnessedCheckpointLedger` / `GossipReceiptStore` compatibility is preserved.
- New epoch registry extends the existing verification surface with policy epoch/digest and historical-threshold resolution.
- Durable gossip journal stores public checkpoint/cosignature evidence only.

## Research / provenance
Primary-source-oriented research was performed using Tavily, Exa, and Parallel Search against TUF, C2SP transparency checkpoint/witness material, RFC 9162, and transparency-dev witness material. Adopted invariants include sequential policy/root versioning, unique-key threshold counting, old+new threshold authorization for key-set transitions, persistence before trust-state advancement, and append-only witnessed evolution. SuperMesh-X does not claim wire/protocol compatibility beyond its documented adopted invariants.

## Capabilities / providers actually used
- Capability Orchestrator.
- Superpowers: brainstorming, test-driven-development, executing-plans, systematic verification/verification-before-completion.
- Akinator.
- Baton Pass guidance.
- Exa search/deep-research skill surface + Exa web search.
- Tavily research/extraction.
- Parallel Search.
- Google Drive skill.
- Files/File Library listing, materialization, and persistence verification.
- Local Python/container build, regression, compile, smoke, ZIP, integrity, and hashing tooling.

## Exposed but intentionally not invoked
Market/crypto/blockchain/broker/personal-finance/Gmail/calendar/GPU lanes were not required by this trust/persistence change. They were not invoked merely to inflate provider usage. No private-source lane was routed into public research.

## Privacy / authority
- No Gmail, personal-finance, broker, live-order, messaging, or calendar data accessed.
- No trade/order/deployment/external execution action occurred.
- Policy metadata cannot encode execution authority.
- Witness and gossip signatures authenticate evidence only.
- Cross-runtime vectors expose no private key/seed.
- Gossip journal persists public evidence only.

## Risks / assumptions
1. Bootstrap witness policy remains a configured/TOFU trust anchor; compromise of the initial root is outside this module's automatic recovery model.
2. Torn/corrupt journal tails fail closed; automatic quarantine/salvage is deferred.
3. Replay remains O(n); signed compaction/snapshot anchoring is deferred.
4. `supermesh-json-v1` is an internal canonicalization profile, not RFC 8785/JCS.
5. Historical policies are retained for evidence verification; downstream consumers bypassing the journal must enforce their own freshness/downgrade policy.
6. v3.4 is a worker-verified candidate stacked on worker-verified v3.3; neither replaces protected v3.1 without independent governor verification.

## READY_TO_COMMIT
`NOT READY_TO_COMMIT`.

All worker-local scope, focused/full regression, failure-injection, compile/smoke/validator, ZIP integrity, documentation, privacy/authority, artifact identity, and durable persistence gates are green. The exact remaining protected gate is **independent MASTER LOOP GOVERNOR verification**.

## Next evolution target
v3.5:
- signed/anchored gossip-journal compaction;
- explicit quarantine/recovery for torn journal tails;
- policy expiry/freeze and recovery-ceremony semantics;
- policy-aware gossip distribution across independent stores;
- non-Python verification fixture for the cross-runtime vectors;
- explicit downgrade/freshness gates for consumers outside `DurableGossipJournal`.

## Exact resume
1. Read this capsule.
2. Reverify artifact SHA-256 `d7134590b97446e2e0d19943ff9430990a03f6a0b0613131c16d7a549208079e`.
3. Confirm v3.1 stable artifact still hashes to `1a4a9e24129c88cddc54cf8f046c2051385e8414d4771f62b8989f46ac4f1e24`.
4. Do not overwrite v3.1, v3.3 cycle 3, or v3.4 cycle 4.
5. Obtain independent MASTER LOOP GOVERNOR verification before changing promotion status.
6. If continuing evolution first, start v3.5 from v3.4 as a worker-local candidate using RED tests first, then focused/full/security regression, compile/smoke/validator, clean package, fresh extraction, SHA-256, and another versioned capsule.
