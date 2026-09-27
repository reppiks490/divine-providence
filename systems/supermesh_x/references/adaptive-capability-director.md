# Adaptive Capability Director

The v0.8 adaptive layer keeps provider choice stable while allowing live tool ecosystems to evolve.

## Surface snapshots

Capture provider/tool name, version when available, input schema, runtime target, transport/auth metadata, and a deterministic schema fingerprint. Do not store secrets or raw tool outputs in the snapshot.

## Drift classes

- **Compatible:** new tool, added optional parameter, metadata-only change.
- **Breaking:** removed tool, removed parameter, parameter type change, newly required parameter, incompatible transport/auth requirement.
- **Unknown:** insufficient schema information; treat as unverified until validated.

## Discovery receipts

For every adaptive discovery decision preserve: query/need, candidates exposed, result limit, withheld count, top withheld candidates, status, stop reason, provider/version/schema metadata, and the chosen provider. Receipts are audit metadata only. Never include raw user prompts beyond the compact discovery need when retention policy forbids it, raw arguments, raw outputs, private inbox/account content, or credentials.

## Capability-specific feedback

Learn provider usefulness per capability using bounded observations such as success, quality, and latency. A provider can be excellent for `research.search` while poor for `market.history`; never collapse all performance into one global provider score. Cold-start providers use a neutral prior.

## Replacement planning

When drift is breaking or health fails:
1. quarantine the incompatible route;
2. discover providers exposing the same capability;
3. enforce runtime state, auth/transport, privacy, and authority gates;
4. rank surviving providers with health plus capability-specific feedback;
5. preserve the discovery receipt and reason;
6. switch only to a verified compatible adapter;
7. if none exists, degrade safely instead of guessing.

## Runtime notifications

When the host supports MCP `tools/list` refreshes or tool-list-changed notifications, refresh the surface snapshot and run the same drift classifier before activating modified tools.
