# External source semantics and review questions

These primary references support contract design. They do not prove that a specific user dataset has these fields or that it can be redistributed.

- [Databento MBO schema](https://databento.com/docs/schemas-and-data-formats/mbo): event and receive timestamps, venue sequence, order ID, add/cancel/modify/trade/fill and snapshots. Review actual venue-specific semantics and recovery before accepting a source.
- [St. Louis Fed FRED observations API](https://fred.stlouisfed.org/docs/api/fred/series_observations.html) and [vintage dates](https://fred.stlouisfed.org/docs/api/fred/series_vintagedates.html): economic series can have multiple revisions; the value known at a historical decision is a vintage, not today's final value.
- [CFTC Commitments of Traders](https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm): position observation dates generally precede publication. Preserve both dates and first-known time.

For each new source record dataset ID, licensing terms, raw SHA-256, native symbol/contract, venue, timezone/clock definition, per-stream sequence policy, correction semantics, source completeness, first-known/receipt proof, representation identity and review owner.
