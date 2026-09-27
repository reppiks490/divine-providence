# Architecture

SuperMesh-X has seven planes:

1. **Intent plane** — converts the request into capabilities, constraints, freshness, latency, and evidence requirements.
2. **Discovery plane** — enumerates runtime tools, plugins, skills, connectors, local/project files, browser access, and public endpoints.
3. **Acquisition plane** — search, crawl, scrape/extract, API query, file retrieval, repository retrieval, market feeds, blockchain queries, and browser-assisted collection.
4. **Normalization plane** — canonical identifiers, symbols, timestamps, currencies, units, schemas, corporate actions, chain IDs, URLs, document IDs.
5. **Evidence plane** — deduplication, contradiction detection, source independence, authority, staleness, point-in-time validity, and claim-to-source lineage.
6. **Reasoning/execution plane** — analysis, code, simulation, backtesting, study generation, repo edits, and artifact creation.
7. **Verification/handoff plane** — tests, checks, evidence summaries, unresolved gaps, ownership, and resumable state.

## Research fan-out

A difficult query can fan out by source class and then converge:

- primary/official
- structured specialist databases
- scholarly literature
- web/news
- code repositories
- user-authorized private corpora
- community/review evidence where appropriate

Fan-out is bounded by usefulness, quotas, latency, and independence. More sources are not automatically better; correlated copies of one original source count as one evidence family.

## Data lake behavior

The mesh may build a temporary task-local evidence lake with normalized records. Durable storage is optional and runtime-specific. The skill never assumes persistence unless the runtime explicitly provides it.

## v2.4 durable execution and isolation admission

The execution-domain layer now has a portable transactional reference backend (`SQLiteDurableRunStore`) and a transactional shared-capacity admission backend (`SQLiteIsolationAdmission`). Any future multi-computer or large-agent runtime must preserve their observable contracts: restart-safe monotonic fencing, CAS-protected lifecycle mutation, secret-free checkpoint metadata, explicit resource reservation, isolation-tier capability allowlists, and opaque credential references only. Backend substitution is allowed; semantic weakening is not.

## v2.5 pre-runtime isolation boundary
Future computer, terminal, or multi-agent workers must enter through the v2.4 admission reservation and the v2.5 workspace/remote-store contract. Keep host filesystem access deny-by-default, use explicit opaque mounts, enforce network egress at the runtime boundary, execute argv vectors rather than ambient shells, resolve secrets only through an authorized broker, and require remote ownership stores to preserve atomic CAS plus fencing. A control-plane policy decision is not itself runtime enforcement.
