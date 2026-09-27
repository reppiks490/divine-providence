# Portfolio Shock Overlay

The Portfolio Shock Overlay joins an already-observed market Shock Graph to authorized holdings or allocation context. It computes exposure-weighted impact summaries and identifies which positions/channels were exposed. It does not generate a trade, order, or causal claim.

Inputs can come from Finances or another authorized portfolio provider. Normalize symbol, asset class, weight/value, timestamp/freshness, and account scope. Treat stale or partial account synchronization as a coverage limitation. Keep the resulting overlay private unless the user explicitly requests a shareable/redacted output.

A public event such as a policy statement, macro release, geopolitical development, or public executive communication remains public evidence. Holdings and account data remain private evidence. The fusion layer may say how an observed public shock intersects the authorized portfolio, but must preserve those evidence classes separately.
