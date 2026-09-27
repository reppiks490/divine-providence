# Interactive Brokers adapter

SuperMesh-X treats Interactive Brokers as both a high-value market/account data source and a consequential action surface.

## Capability lanes

Read-only lane: quotes, historical bars, contract lookup, scanners, account/portfolio state, order/status reads, executions/fills, positions, P&L, and market-data subscriptions when the connected IBKR account is entitled to them.

Write lane: placing, modifying, cancelling orders or initiating any account-changing action. This lane never inherits authority from research or read-only access and always requires explicit user authorization at execution time.

## Connection modes

Retail clients should support Client Portal Gateway for Web API access and TWS/IB Gateway for the socket API. Institutional/approved integrations may additionally use direct Web API OAuth and FIX where IBKR authorizes it. Runtime capability discovery decides which is actually available.

Keep account permissions, market-data entitlements, authentication state, brokerage-session state, pacing/rate limits, and websocket lifetime as runtime state rather than static assumptions.

## Safety and audit

Never store credentials in the portable skill. Never claim a connection until authentication succeeds. Every order-capable action must preserve request, account, instrument, quantity, order type, limit/stop values, time-in-force, confirmation state, broker response, and execution identifiers in an audit record.
