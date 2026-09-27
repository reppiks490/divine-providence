# Current Geopolitical Market Impact

Use this lane for fast-moving public geopolitical events that may transmit into financial markets. It is descriptive and analytical, not political advocacy.

## Priority order

1. Earliest verifiable public event timestamp: official statement, public social post, regulatory release, military/diplomatic release, or company/industry primary source.
2. Independent confirmation: reputable wire/news source and, where useful, a second independent source family.
3. Physical/operational confirmation where available: shipping traffic, pipeline/refinery status, energy flows, sanctions lists, exchange/market status, or public on-chain evidence.
4. Market tape: synchronized price, volatility, volume, rates, FX, sector, commodity, and crypto observations.
5. Historical analogues: used for calibration only; never allowed to override current evidence.

## Event clock

Preserve separately:
- `event_time`: when the public action/post/release occurred.
- `published_time`: when a source made it public.
- `available_time`: when the system could lawfully have known it.
- `retrieved_time`: when SuperMesh-X acquired it.
- `market_observation_time`: timestamp of each price/volume observation.

Reject future-known evidence from historical analysis.

## Iran / Strait of Hormuz transmission map

Potential channels to measure, not assume:
- physical oil/LNG supply and tanker transit
- freight/insurance/shipping risk
- sanctions and sanctions-evasion enforcement
- military escalation/de-escalation
- diplomacy/ceasefire/negotiations
- inflation expectations and rates
- safe-haven demand and USD
- equity risk appetite and volatility
- defense/energy sector response
- digital-asset and sanctions-evasion narratives

Default cross-asset set: WTI, Brent, natural gas, XLE/energy proxies, gold, DXY, Treasury yields, VIX, VXN, NQ, ES, YM, RTY, BTC and ETH. Add directly exposed securities only when the event has a documented exposure channel.

## High-frequency windows

Use pre-event checks and multiple post-event horizons. Typical intraday windows: -10m, -5m, -2m, -1m; +1m, +2m, +5m, +10m, +30m, +60m. Extend to hours/days when the transmission mechanism is slower or markets are closed.

## Attribution guardrails

Penalize confidence for:
- significant pre-event movement
- overlapping macro/Fed releases
- simultaneous earnings/company news
- another geopolitical shock in the same window
- uncertain or syndicated timestamps
- illiquid/off-hours pricing
- stale or revised data

Prefer matched controls or synthetic controls when feasible. Report association strength; causality requires stronger identification than temporal proximity alone.
