# Market-Mover Intelligence Network

This subsystem tracks only lawfully accessible public communications and actions. It does not track private location, private communications, or non-public personal activity.

## Inputs

Public social posts, official statements, speeches, interviews, press releases, regulatory/executive actions, company announcements, public video/transcripts, and reputable reporting that preserves the original publication time.

## Entity model

Two named seed profiles are included because they were explicitly requested: Donald Trump and Elon Musk. Additional figures are discovered by role rather than frozen names so the watchlist stays current: central-bank leadership, Treasury/economic officials, mega-cap technology leadership, semiconductor leadership, energy leadership, and crypto ecosystem leadership.

## Event pipeline

1. Capture canonical source plus `event_time`, `published_time`, `available_time` when known, and `retrieved_time`.
2. Deduplicate reposts, mirrors, screenshots, and downstream news stories against the original content family.
3. Extract topics, named assets, policy/company entities, directional claims, uncertainty, novelty, and surprise.
4. Map the event to affected assets/sectors/macro factors.
5. Measure pre-event movement for anticipation/leakage.
6. Measure post-event price, abnormal return, volatility, volume, liquidity where available, and cross-asset response over multiple windows.
7. Compare against matched controls, synthetic controls, or factor-adjusted returns when data permits.
8. Search for competing events in the same window.
9. Score the association conservatively. Never convert the score into an unqualified statement of causation.
10. Store the event, reaction vector, evidence lineage, decay profile, and attribution tier for later learning.

## Social acquisition

Prefer a direct authorized public-social connector when the runtime provides one. Otherwise use search/crawl/official-page/video/news fallbacks and preserve source provenance. Search-engine copies or media quotations are lower-confidence than a canonical original post and must not be silently upgraded to original-source status.

## Reaction vector

Track NQ/ES/YM/RTY, VIX/VXN, DXY, Treasury yields, sector/industry baskets, directly named securities, commodities, and crypto where relevant. The exact set is event-dependent.

## Guardrails

A price move after a post is not proof that the post caused it. Penalize simultaneous macro releases, central-bank events, earnings/company news, geopolitical headlines, open/close effects, prior price movement, timestamp uncertainty, and syndicated evidence. Preserve inconclusive results.

## Impact fingerprints

Use `scripts/impact_memory.py` to aggregate historical event records by entity × topic × asset. Fingerprints store sample count, mean association score, mean absolute abnormal return, median peak latency, and direction balance. Historical fingerprints can prioritize monitoring resources but are explicitly non-predictive and must respect an `as_of` availability cutoff.
