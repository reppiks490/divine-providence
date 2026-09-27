# Temporal and point-in-time data

SuperMesh-X distinguishes four times when possible:

- `event_time`: when the real-world event/value occurred
- `published_time`: when a source published it
- `available_time`: when it would have become knowable to the analysis system
- `retrieved_time`: when the mesh fetched it

## Why it matters

Historical analysis and backtesting must not use a value that was revised or published after the simulated decision point.

## Temporal rules

- preserve revisions instead of overwriting history when feasible
- record timezone and market session context
- for filings/earnings/macro releases, use release timestamps rather than fiscal-period labels alone
- for blockchain data, preserve chain ID and block number/timestamp
- for news, separate article publication time from event time
- for corporate actions, record ex-date/effective date and adjustment method
