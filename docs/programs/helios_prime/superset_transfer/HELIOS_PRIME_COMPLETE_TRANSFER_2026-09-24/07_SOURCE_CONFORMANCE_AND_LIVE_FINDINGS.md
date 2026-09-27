# SOURCE CONFORMANCE & LIVE PROVIDER FINDINGS

The design loop exercised representative providers and found distinct states that must never collapse into generic failure:
- authorization blocked;
- entitlement blocked;
- timestamped live-ish data;
- current-looking but untimestamped data;
- structurally valid but semantically suspicious fields;
- restricted content with visible metadata;
- composite wrappers with upstream attribution;
- technically valid but investigation-irrelevant sources.

Observed examples:
- U.S. Gold Bureau: access-policy blocked; this means source unavailable under current access context, not that no gold price exists.
- StackerScan: explicit asOf/date/base/unit for XAU/XAG; spot reference is not COMEX futures.
- Bybit: price and order-book endpoints expose different timestamp semantics; qualification is endpoint-specific.
- Twelve Data: venue/time metadata for BTC/USD; venue-specific quote is not universal BTC price.
- DataBlue/Google Finance: usable price with zero-like ancillary fields; field-level semantic quarantine needed.
- FMP: commodity discovery available while quote entitlement blocked; provider catalog != quote entitlement.
- Massive: futures contract metadata available while requested MGC snapshot not entitled; reference metadata != live entitlement.
- Blockscout: announced future access-policy/key change; motivated access-decay forecasting.
- The Fly: metadata visible while content restricted; headline/body rights differ.
- Bigdata.com: wrapper exposed upstream attribution; wrapper+direct upstream is not independent confirmation.
- Zacks: rank/attention/research signals are distinct from raw market observations.
- Cheat Database: valid structured data but irrelevant to market investigation; source quality != relevance.

Canonical rule: connector success is not research eligibility.
