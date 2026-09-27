# Build Report v3.7.0

Scope: additive witness-policy expiry, explicit trusted-time contracts, durable time rollback floors, and freeze-resistant active trust decisions.

## Design
`WitnessPolicyEpoch.expires_unix` is optional and omitted from legacy serialization. Expiring policies require an explicit `TrustedTimeGuard` for bootstrap, rotation, and active policy use. The guard obtains one already-authenticated sample from a caller-provided source, treats its uncertainty as a closed interval, persists a monotonic lower-bound floor when configured, and rejects expiry when the policy is expired or when uncertainty overlaps the expiry boundary.

Historical verification is intentionally separated from active acceptance. A witness signature or journal entry can still be audited after policy expiry, but new checkpoint creation, active gossip append, compaction, and compacted loading fail closed until a fresh current policy is available.

## Rollback and time-source model
- The local process clock is never trusted implicitly.
- The time adapter is responsible for authenticating external time evidence before constructing `TrustedTimeSample`. Time and uncertainty are strict integer seconds; fractional and string-coerced values are rejected to keep canonical semantics portable.
- `DurableTrustedTimeFloor` rejects local lower-bound rollback across restarts and is published with fsync + atomic replacement + parent-directory fsync where supported. Updates are serialized by an exclusive fail-closed `.update.lock`; after acquiring it, the writer reloads the latest durable floor before comparing/publishing so stale processes cannot lower the floor.
- `minimum_lower_bound_unix` lets callers retain a floor outside the same rollback domain.
- The local floor checksum detects corruption but is not misrepresented as a defense against restoration or malicious rewrite of all local trusted state.

## Test-first evidence
- RED stage 1: trusted-time module discovery failed before `scripts/trusted_time.py` existed; minimal module creation made that contract green.
- RED stage 2: 8/8 v3.7 behavioral tests failed because the trusted-time APIs/expiry behavior did not exist.
- GREEN stage 2: 8/8 passed after the minimum implementation.
- RED stage 3: active gossip append accepted a checkpoint after current-policy expiry; the dedicated test failed first.
- GREEN stage 3: append now checks current-policy freshness before active admission; 9/9 v3.7 behavioral tests passed.
- Packaging contract was introduced RED first against the v3.6 manifest/docs/smoke surface and then made GREEN.
- RED stage 4: two adversarial concurrency tests showed a stale floor writer could race a newer writer and that an existing update lock was not enforced.
- GREEN stage 4: exclusive floor locking plus reload-before-compare made both tests pass; v3.7 behavior reached 11/11.
- RED stage 5: strict-seconds test showed Python coercion accepted fractional/string timestamps and expiries.
- GREEN stage 5: time, uncertainty, and policy expiry now require true integer seconds; v3.7 behavior reached 12/12.
- Final focused trust/gossip regression after concurrency and strict-seconds hardening: 60 passed.

## Research basis
The Update Framework v1.0.35 was used for expiration/freeze/fixed-start-time design principles. RFC 3161 was used for trustworthy-time-source, accuracy/uncertainty, and replay-aware timestamping principles. Exa, Parallel Search, and Tavily Search were read-only research layers. Tavily Research was attempted but provider quota returned status 432. See `references/trusted-time-research-provenance.md`.

Final regression, compile, smoke, package-validator, ZIP-integrity, fresh-extraction results, and final hashes are recorded after packaging in the versioned cycle state capsule.

Stale when: witness-policy expiry, trusted-time floor persistence, time-source authority, or packaging verification changes.

## Final source-tree verification
- Focused trust/gossip regression: **60 passed**.
- Full regression: **351 passed**.
- Python compileall with external bytecode cache: **PASS**.
- Executable smoke: **PASS** with `package_version=3.7.0` and `trusted_time_freeze_guard=true`.
- Package validator: **PASS**.

The distributable is additionally verified from a clean extraction; those package-bound results and final hashes are recorded in the versioned cycle state capsule.
