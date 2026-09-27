# Adaptive Federated Research Workflow

Use this workflow when a single provider is unlikely to be sufficient or when the answer needs independent corroboration.

1. **Compile query families.** Generate baseline, primary-source, temporal/revision, contradiction, and domain-specific queries.
2. **Plan source classes.** Prefer independent classes: primary/official, specialist structured data, scholarly, code/repository, reputable news, public web, archives, and authorized private data.
3. **Resolve runtime state.** Route only to providers that are actually usable now; keep auth/preflight/quota blockers explicit.
4. **Retrieve in waves.** Start with the smallest authoritative set. Escalate only when evidence is incomplete, contradictory, stale, or low-confidence.
5. **Normalize.** Resolve entities, symbols, units, time zones, publication/availability times, revisions, and provider-specific schemas.
6. **Deduplicate by evidence family.** Syndicated copies and mirrors count as one underlying family, not independent confirmations.
7. **Apply temporal guards.** Historical analysis may use only evidence available at the historical decision time.
8. **Fuse claims.** Weight independent evidence by authority, freshness, completeness, and temporal validity. Preserve support and contradiction separately.
9. **Investigate disagreement.** Check methodology, revisions, period definitions, units, geography, corporate actions, symbol mapping, or genuinely conflicting evidence.
10. **Stop on information gain.** Stop expanding when the expected value of another source wave is lower than its cost/latency and remaining sources are likely duplicative.

The runtime may bind these steps to any compatible providers. Provider names are never part of the logical contract.
