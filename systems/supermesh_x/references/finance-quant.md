# Finance and quant mesh

## Provider roles

- TickerLayer / Twelve Data: quotes, OHLCV, sessions, market state, reference data, rates and related structured feeds when available.
- Zacks: company snapshots, statements, research, metrics, news, comparisons.
- FactorWeave: factor states, analogues, regimes, embeddings, labels, futures factor context.
- Economist graphs: specialized macro/political-economic datasets when relevant.
- Hey-Traders: chart research, backtests, and simulated-paper workflows where supported.
- Broad web/research providers: primary filings, exchange notices, central banks, company IR, news, and missing context.

## Enhanced market data model

Normalize observations into: instrument identity, venue, asset class, timestamp, availability timestamp, timezone, currency, units, adjustment state, source, and raw payload hash.

## Quant integrity

Before using data in a backtest or model, check:

- look-ahead / future-known fields
- survivorship bias
- delisted/inactive symbol treatment
- split/dividend/corporate-action adjustment
- timezone/session alignment
- stale bars and missing bars
- continuous-futures roll methodology
- symbol mapping and venue ambiguity
- revised macro/fundamental data versus originally published values
- train/test contamination

## Fusion examples

A market-research task can combine price structure + volatility + factors + fundamentals + earnings + rates + macro + news + cross-asset context + historical analogues. The mesh keeps each feature family separate so correlation is not mistaken for independent confirmation.

## No automatic financial decision

Present evidence, scenarios, uncertainty, and model assumptions. Do not convert provider output into an unquestioned trade decision.
