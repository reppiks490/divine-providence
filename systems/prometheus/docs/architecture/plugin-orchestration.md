# Plugin Orchestration Architecture

## Current rule

Every top-level PROMETHEUS research run performs a complete plugin inventory and selection pass. A candidate plugin receives exactly one initial decision: `SELECTED`, `SKIPPED_NOT_BENEFICIAL`, `SKIPPED_REDUNDANT`, `SKIPPED_POLICY`, or `UNAVAILABLE`. A selected plugin records the exact descriptor content hash and must then receive a host execution record ending in `COMPLETED` or `FAILED` before the run can finalize. Evidence normalization rejects descriptor drift between those stages.

Deep Research is mandatory when visible and available. If it is unavailable, the run is `DEGRADED_RESEARCH`; if it is selected but no host execution evidence exists, the run fails closed. Other selected plugins also require an execution record, because "selected" means PROMETHEUS judged them materially beneficial and therefore must actually attempt to use them.

## Why host-mediated

ChatGPT plugins/connectors are host capabilities, not Python libraries inside this repository. The v0.1 package therefore models the boundary honestly:

```text
ChatGPT host
  inventory installed/available plugins
  select/invoke policy-eligible plugins
  capture result/failure references
            |
            v
HostPluginResult
            |
            v
PROMETHEUS PluginAudit
            |
            +--> PluginExecutionEvidence (descriptor-bound)
            |
            +--> PluginContributionReport
            |
            +--> research artifacts / lineage
```

The local package never fabricates a connector call. Unit tests use deterministic `HostPluginResult` fixtures so orchestration logic remains reproducible offline.

## Selection semantics

"Every beneficial plugin" means every visible, policy-eligible plugin with positive expected marginal information, validation, provenance, execution-quality, or orchestration value for the current objective after considering duplication, latency, permissions and sensitivity.

A plugin is not beneficial merely because it is installed. For example, an email connector is not invoked for a local architecture experiment unless the run objective actually depends on email evidence.

## Security posture

Plugin outputs are evidence, not authority. They cannot:

- authorize production;
- mutate sibling production state through PROMETHEUS;
- bypass DAEDALUS validation;
- manufacture NEXUS availability timestamps;
- convert candle proxies into ARGUS trade/depth truth; or
- override ATHENA supervisory state.

The host should use least-privilege permissions and scoped/ephemeral credentials when supported. PROMETHEUS records failures rather than silently discarding them.

## Code map

- `src/prometheus_loop/plugins.py` — plugin descriptors, decisions, usage, audit, and immutable execution evidence.
- `src/prometheus_loop/policy/plugins.py` — deterministic benefit/policy selection.
- `src/prometheus_loop/forge/plugin_contribution.py` — deterministic attribution-overlap classification without scalar ranking.
- `src/prometheus_loop/policy/promotion.py` — research-only DAEDALUS review packet builder.
- `src/prometheus_loop/orchestration/loop.py` — enforces selected-plugin execution evidence and persists normalized evidence/contribution artifacts.
- `tests/test_plugins.py` — plugin rule tests.
- `tests/test_loop.py` — end-to-end plugin-aware run tests.

**When not to use this pattern:** do not treat it as a general-purpose plugin marketplace, direct connector runtime, credential store, or plugin-quality leaderboard. PROMETHEUS records host-mediated research-plugin usage and attribution only.

**Stale when:** the ChatGPT host exposes a stable in-process plugin execution SDK that this package is explicitly authorized to own, or the owner changes the Deep Research requirement.
