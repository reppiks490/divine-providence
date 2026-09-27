# H4 — SOURCE ECONOMY & ACQUISITION MESH

H3 owns the question. H4 owns the acquisition path.

## Source states
Access: AVAILABLE, AUTHORIZATION_BLOCKED, ENTITLEMENT_BLOCKED, RATE_LIMITED, TEMPORARILY_UNAVAILABLE, PROVIDER_FAILURE, CONNECTION_FAILURE, POLICY_CHANGE_PENDING, CREDENTIAL_REQUIRED, UNKNOWN_ACCESS.
Timing: EXPLICIT_EVENT_TIME, EXPLICIT_PROVIDER_ASOF, EXPLICIT_QUOTE_TIME, CURRENT_UNTIMESTAMPED, DATE_ONLY, UNKNOWN_TIME, CONFLICTING_TIMESTAMPS.

## Probe protocol
Separate SchemaState from SemanticState. Record request/completion time, access/timing/schema/semantic states, provider timestamp, payload hash, quality flags and reason codes. Never substitute request time for source knowledge time.

## Health and economics
Health is empirical history, not one boolean. Track availability/success ratios, latency, schema/semantic failures, stale ratio and sample count. Economics stays vectorized: money, quota, latency, freshness, timing, semantics, provenance, availability, independence, historical reliability, rights friction and auth friction. Unknown quality never defaults to perfect.

## Semantic substitution
Compare instrument, asset class, venue, representation, currency, unit, event-time semantics, revision semantics, history depth and evidence family. Qualifications: EXACT, DEGRADED, NOT_SUBSTITUTABLE. Gold spot is not exact MGC futures; BTC/USD is not BTC/USDT.

## Access-policy decay
Represent known future provider policy changes without rewriting historical readiness.

## Acquisition routing
Capability -> access -> rights -> semantics -> timing -> provenance/independence -> health -> cost -> latency -> historical information yield.

## Realized source value
Track expected vs realized information, cost/latency, independent-evidence yield, semantic/timing/provider failure. Keep action families and estimator versions separate.

## Source Pareto tournament
Maximize realized information, freshness, timing, semantics, provenance, independence, reliability. Minimize cost, quota, latency, rights/auth friction and failure probability.

## Synthetic worlds
Entitlement trap; correlated duplicate; spot/futures mismatch; stale perfect provider; access-policy decay; misleading zero fields; operational failure; exact substitution during outage; degraded-only substitute; restart.

## H3↔H4 boundary
H4 may return infeasible/degraded acquisition results. It never changes the H3 research question itself.
