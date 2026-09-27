# Trusted-time freeze guard (v3.7)

SuperMesh-X v3.7 adds an **explicit trusted-time contract** for witness-policy freshness. It never treats the process wall clock as trusted by default.

## Contract

`scripts/trusted_time.py` defines:

- `TrustedTimeSample`: an already-authenticated time assertion supplied by an external adapter. It carries a Unix-second center, an uncertainty interval, a public source identifier, and optionally a public evidence digest.
- `DurableTrustedTimeFloor`: a crash-consistent local monotonic floor over the sample's **lower bound**. It rejects samples whose lower bound moves backward, uses an exclusive per-floor update lock, reloads the latest durable state inside that lock before comparison, and can also enforce an independently retained `minimum_lower_bound_unix`.
- `TrustedTimeGuard`: captures one fixed sample for a guarded decision, enforces uncertainty/floor constraints, and checks an expiring witness policy against that fixed interval.

The adapter that creates a `TrustedTimeSample` is responsible for authenticating its source evidence first. SuperMesh does not fetch a TSA token, contact NTP, or bless the local wall clock implicitly. This keeps time-source trust outside the evidence-verification code and avoids silently expanding network or credential authority. Time and uncertainty values are strict integer seconds; floats and string-encoded numbers are rejected instead of being coerced, preventing cross-runtime canonicalization drift.

## Expiring witness policies

`WitnessPolicyEpoch.expires_unix` is optional. When absent, the serialized public policy is unchanged from v3.6 and earlier, so legacy policy digests remain stable. When present:

- bootstrap requires a `TrustedTimeGuard` and rejects an already-expired policy;
- rotation samples time once and checks both the current and next policy against the same fixed sample;
- current-policy checkpoint creation, active gossip admission, compaction, and compacted loading require a fresh policy;
- historical signature verification and strict forensic journal replay remain time-neutral so evidence that was valid when produced can still be audited after policy expiry.

## Uncertainty and expiry

A sample represents `[lower_bound_unix, upper_bound_unix]`. A policy is accepted only when its expiry is **strictly later than the entire interval**. If expiry falls inside the uncertainty interval, the guard fails closed instead of guessing which side of the boundary is correct.

This mirrors the fixed-start-time principle used by secure metadata systems: one reference time governs the whole decision rather than allowing later clock movement inside the operation to change the result.

## Rollback boundary

The durable time floor catches local backward movement of trusted time across process restarts. Like every purely local trust floor, it cannot prove that *all* local state was not restored to an older internally consistent image. Use `minimum_lower_bound_unix` from an independent trust domain when that attack is in scope.

The floor file's checksum detects corruption; it is not claimed to be a substitute for an independently authenticated time source or an external rollback pin. Concurrent writers are serialized with a same-directory `.update.lock`, and every writer reloads the floor after acquiring it before making the monotonic comparison. A stranded lock fails closed and requires operator verification before removal; age alone is never treated as proof that a writer is dead.

## Authority separation

Time evidence authenticates **freshness only**. It never grants execution, broker/order, external-write, credential, routing, filesystem, or permission authority. Public research providers are not used as trusted-time providers by this module.

## Operational guidance

Use an adapter that verifies time evidence before returning `TrustedTimeSample`. Keep uncertainty bounded with `max_uncertainty_seconds`. Persist `DurableTrustedTimeFloor` on durable storage. For high-assurance rollback detection, retain a minimum time floor outside the same rollback domain as the SuperMesh package/state.

Stale when: the trusted-time sample schema, witness-policy expiration semantics, floor persistence protocol, or active-vs-historical verification boundary changes.
