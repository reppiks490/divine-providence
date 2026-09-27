# Cross-provider financial research workflow

1. Resolve ticker/security identity and venue.
2. Pull current quote/state from a real-time structured provider.
3. Pull historical OHLCV/reference data from a second provider when accuracy or backtesting matters.
4. Add fundamentals/earnings/statements from a fundamentals specialist.
5. Add factor/regime/analogue data from a factor specialist.
6. Add official filings, exchange notices, company IR, and macro/rates sources as needed.
7. Normalize currency, units, timestamps, sessions, corporate actions, and adjustment state.
8. Compare provider disagreements explicitly.
9. For historical studies, enforce point-in-time availability and leakage checks.
10. Produce an evidence matrix rather than collapsing all sources into one opaque score.
