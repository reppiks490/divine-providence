# Provider registry

## Capability contracts

Every provider advertises capabilities, not privileged status. Example capabilities:

- `research.search`, `research.crawl`, `research.extract`, `research.academic`
- `market.quote`, `market.ohlcv`, `market.fundamentals`, `market.news`, `market.factors`, `market.macro`
- `crypto.market`, `crypto.news`, `chain.address`, `chain.transaction`, `chain.contract`
- `repo.search`, `repo.issue`, `repo.commit`, `repo.write`
- `media.youtube.transcript`
- `skills.discover`, `gpu.nvidia`

## Selection score

Score providers on: availability, authentication, capability match, freshness, authority, point-in-time fitness, historical depth, schema quality, latency, cost/quota, and independence from already-selected evidence.

## Escalation and failover

1. Choose the strongest available provider for the requested capability.
2. If confidence is low or the claim is important, add an independent provider.
3. If structured data is insufficient, use broad search/crawl.
4. If search finds a primary source, retrieve the primary source directly when practical.
5. If a provider fails, retry only according to documented semantics; otherwise switch provider.
6. Preserve provider-specific raw evidence separately from normalized fields.

## Dynamic discovery

At runtime, inspect available tool/plugin/skill catalogs. Unknown providers can join if they expose a capability description and obey runtime permissions. Never invent a provider name or tool schema.
