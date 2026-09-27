# SuperMesh-X STATE CAPSULE — v2.3.0

## Identity
- Version: `2.3.0`
- Build name: **Execution-Domain Foundation**
- Last verified durable checkpoint: `v2.2.0-cycle6`
- Compatibility baseline: `0.3.0`
- Protected-worker status: **ACTIVE / FIXED WORKER**
- READY_TO_COMMIT: **NO — independent MASTER LOOP GOVERNOR verification is still required**

## Completed work
Added the control-plane substrate required before multi-isolated-computer or 50+ logical-agent expansion:
- authoritative expiring execution leases;
- monotonically increasing fencing tokens on ownership takeover;
- stale-owner rejection at mutation boundaries;
- hard resource budgets and fail-closed handling for unbudgeted resources;
- exact least-privilege authority manifests;
- deterministic operation-specific idempotency keys;
- content-addressed secret-free checkpoint receipts;
- fenced rollback receipts;
- terminal-run non-reopen semantics;
- privacy-safe trace-context sanitizer that strips arbitrary baggage and secrets;
- executable smoke coverage and package-contract coverage;
- corrected the obsolete v2.2 compatibility test so it validates preserved v2.2 capabilities instead of pinning the current manifest to exactly `2.2.0`.

The planned isolated-computer runtime, unrestricted shells, credential vault, and 50+ logical-agent swarm are deliberately **not launched yet**.

## Files changed / added
- `scripts/execution_domain_kernel.py`
- `tests/test_execution_domain_kernel.py`
- `tests/test_v230_contract.py`
- `tests/test_v220_contract.py` (compatibility-test repair)
- `references/execution-domain-foundation.md`
- `CHANGELOG_V230.md`
- `CHANGELOG.md`
- `BUILD_REPORT_V230.md`
- `BUILD_REPORT.md`
- `manifest.yaml`
- `README.md`
- `scripts/smoke_check.py`

## Exact verification evidence
- Baseline before change: `206 passed`
- TDD RED: `ModuleNotFoundError: No module named 'scripts.execution_domain_kernel'`
- Initial focused implementation: `11 passed`
- Focused execution-domain + v2.3 package-contract suite: `13 passed`
- First full regression: `218 passed, 1 failed`
  - failure cause: obsolete `test_v220_contract.py` required the current version to remain exactly `2.2.0`
- Repaired v2.2 compatibility contract: `3 passed`
- Final full regression: **`219 passed`**
- Critical failure/rollback/privacy/authority/provider-health/subscription/conformance suite: **`63 passed`**
- `python scripts/validate_package.py`: PASS
- `python -m compileall -q scripts tests`: PASS
- `python scripts/smoke_check.py`: PASS, package `2.3.0`, **32/32 smoke checks**
- cache / `.pyc` cleanup: PASS
- ZIP integrity (`unzip -t`): PASS
- fresh-extract package validator: PASS
- fresh-extract executable smoke: PASS

## Artifact identity
- Local package: `/mnt/data/supermesh_x_v2_3_0.zip`
- Persistent package: `/Google Drive/Icarus Governance/SuperMesh-X/supermesh_x_v2_3_0.zip`
- Google Drive file identity: `external-gdrive:file:1oo8o1hSDrF3qQ5tSfp7yRd2-qLuk8LL-`
- SHA-256: `c312bc7b50964ea768a590b6897e53e071c1bd5e365611a25b7b659b7386481c`
- Commit identity: unavailable in this runtime; no GitHub write connector was exposed, so no commit is claimed.

## Interfaces / contracts introduced
### ExecutionDomainLedger
- `acquire(run_id, worker_id, now_ms, ttl_ms)`
- `renew(run_id, worker_id, fencing_token, now_ms, ttl_ms)`
- `configure_budget(run_id, limits)`
- `consume_budget(run_id, usage)`
- `set_authority(run_id, requested, granted)`
- `require_authority(run_id, capability)`
- `checkpoint(run_id, worker_id, fencing_token, state, now_ms, state_ref=None)`
- `rollback(run_id, worker_id, fencing_token, checkpoint_id, now_ms)`
- `complete(run_id, worker_id, fencing_token, outcome, now_ms)`

### Standalone primitives
- `canonical_dispatch_key(...)`
- `sanitize_trace_context(...)`

## Dependencies / assumptions
- Python standard library only for the new kernel.
- Production durable-store adapters must add transactional/CAS semantics around lease acquisition, renewal, takeover, checkpoint pointer writes, and terminal transitions.
- Fencing tokens must remain strictly monotonic across process restarts.
- Secret/private checkpoint payloads must live outside receipts; receipts carry only hashes and optional opaque state references.
- Authority checks must execute immediately before side-effect dispatch, not merely during planning.

## Privacy / authority status
PASS.
- No Gmail or Finances data was accessed this cycle.
- Read scopes do not imply write scopes.
- Research capability does not imply brokerage execution.
- Arbitrary OpenTelemetry baggage, credentials, email addresses, customer IDs, and private context are not forwarded by the trace sanitizer.
- The execution-domain module itself cannot grant host-filesystem, credential, brokerage-order, external-write, or live-trading authority.

## Capability preflight actually used
Control-plane / skill guidance loaded or applied:
- Capability Orchestrator
- Baton Pass
- Astral Orchestrator
- Akinator
- Exa Search skill
- Tavily guidance
- Firecrawl guidance
- Google Drive guidance
- Stock Market Summary
- Adaptive Codex Orchestrator
- selected requested domain skills during inventory

No child-agent runtime was exposed, so Astral did **not** fabricate workers or claim a swarm run.

Successful provider/tool probes:
- Exa
- Parallel Search
- Firecrawl developer search
- DataBlue
- omgskills discovery (returned no matching skills for the query)
- TickerLayer
- Massive
- CoinGecko
- Bybit
- Runway authentication/capability metadata
- Scite
- Zacks
- FMP
- Next Stock — Market Insights
- Exum / ExoScope Crypto
- Blockscout session unlock
- Google Drive / File Library continuity and persistence

Degraded or unavailable in this cycle:
- Tavily Research: plan usage limit (`432`)
- Twelve Data `auth_status`: internal provider failure
- U.S. Gold Bureau health check: IP authorization failure

Not invoked because not materially required for this foundational change:
- Gmail
- Finances
- Google Calendar
- live brokerage execution
- media generation/editing
- FFmpeg transformation
- marketing execution
- actual GPU workloads
- multi-agent child spawning

## Research basis used
- Kubernetes Lease semantics for distributed coordination / leader ownership.
- OpenTelemetry context and baggage privacy guidance; arbitrary baggage is treated as unsafe across public/untrusted provider boundaries.
- MCP protected-capability authorization concepts.
- Multi-agent/durable execution research from Exa, Parallel Search, Firecrawl, Scite, and requested provider surfaces.

## Blockers / risks
### Blocking READY_TO_COMMIT
1. **Independent MASTER LOOP GOVERNOR verification has not occurred.** Self-verification and scheduler state do not satisfy this gate.

### Non-blocking but required before swarm/computer expansion
1. No durable transactional run-store adapter yet (Redis/Postgres/Kubernetes/other backend).
2. No credential-vault broker / scoped secret-injection runtime yet.
3. No isolated-computer sandbox backend or host escape tests yet.
4. No 50+ agent admission controller, concurrency scheduler, deadlock detector, duplicate-work suppressor, or runaway recursion guard yet.
5. No distributed lease chaos tests across separate processes yet.
6. No GPU allocation/lease adapter yet.
7. No GitHub write connector exposed in this runtime, so package was built locally and persisted to Drive without a repository commit.

## Next evolution target
**v2.4.0 — Durable Execution Store & Isolation Admission Layer**

Priority scope:
1. Define a provider-neutral durable run-store protocol with optimistic concurrency / CAS and monotonic fencing-token persistence.
2. Add SQLite reference backend for deterministic local tests plus an adapter interface suitable for Postgres/Redis/Kubernetes implementations.
3. Add resource/admission contracts for future isolated computers: CPU, memory, storage, GPU, provider-call, token, wall-clock, and concurrency quotas.
4. Add execution-domain lifecycle states: queued, claimed, running, suspended/input-required, retry-scheduled, succeeded, failed, cancelled, worker-lost.
5. Add crash/restart/takeover failure injection and stale-worker mutation tests across independent process simulations.
6. Add credential-reference contracts that never serialize raw credentials into checkpoints, traces, or inter-agent messages.
7. Only after those gates pass, begin the isolated-computer runtime abstraction; do not create the 50+ agent swarm yet.

## Exact resume instructions
1. Treat `v2.3.0` and SHA-256 `c312bc7b50964ea768a590b6897e53e071c1bd5e365611a25b7b659b7386481c` as the newest worker-local verified artifact.
2. Confirm `/Google Drive/Icarus Governance/SuperMesh-X/supermesh_x_v2_3_0.zip` and this versioned capsule exist before modifying anything.
3. Never overwrite v2.2.0-cycle6 or v2.3.0; extract v2.3.0 into a new working directory.
4. Run the full baseline regression before the next behavior change; expected baseline is `219 passed`.
5. Start v2.4.0 with failing tests for the durable run-store/admission protocol before implementation.
6. Preserve the v2.3 authority, privacy, fencing, budget, idempotency, checkpoint, and trace contracts.
7. Keep multi-isolated-computer launch and the planned 50+ logical-agent swarm disabled until the durable-store/isolation prerequisites and their failure-injection tests pass.
8. At cycle end, repeat full regression, critical gates, package validator, compile, executable smoke, cache cleanup, ZIP integrity, SHA-256, Drive persistence, and a new versioned state capsule.
9. Do **not** report READY_TO_COMMIT unless the MASTER LOOP GOVERNOR independently verifies the protected worker.
