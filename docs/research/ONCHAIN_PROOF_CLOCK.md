# ProofClock: CCTP V2 evidence component

## Purpose and status

ProofClock is a read-only research component for recording **when a particular CCTP V2 attestation was observed by this collector**. It is a narrow, testable step beyond the collection-only *Onchain Event Intelligence Grid* described in the referenced chat. The chat's market figures and event claims are unverified context here; none are imported as source data or used to establish an edge.

The current branch implements a local CLI and SQLite snapshot ledger for Circle Iris V2 `GET /v2/messages/{sourceDomainId}?transactionHash=...`. One fetch records one HTTP response, including non-200 responses, at local receipt time. `timeline` reconstructs the observations for a query, `asof` returns the latest locally received observation by a supplied decision time, and `verify` checks the local hash chain. The CLI does **not** discover burns, poll continuously, verify Circle signatures, inspect destination transactions, or send a transaction. The ledger's append-only trigger and hashes detect ordinary local edits; they are not an external timestamp or a defense against an administrator who can replace the whole database.

Example, with a real source domain and source transaction hash supplied by the operator:

```powershell
.\.venv\Scripts\python.exe -m divine_providence.onchain_research --db run/cctp-research.sqlite3 fetch --environment mainnet --source-domain 0 --transaction-hash 0x<64-hex-digits>
.\.venv\Scripts\python.exe -m divine_providence.onchain_research --db run/cctp-research.sqlite3 timeline --environment mainnet --source-domain 0 --transaction-hash 0x<64-hex-digits>
.\.venv\Scripts\python.exe -m divine_providence.onchain_research --db run/cctp-research.sqlite3 asof --environment mainnet --source-domain 0 --transaction-hash 0x<64-hex-digits> --decision-time 2026-09-28T00:00:00Z
.\.venv\Scripts\python.exe -m divine_providence.onchain_research --db run/cctp-research.sqlite3 verify
```

The `0x<64-hex-digits>` placeholder must be replaced before running. The collector captures the receipt clock itself; caller-supplied snapshots are accepted only as synthetic fixtures. A locally captured HTTPS response remains a provider report, not a cryptographically verified Circle attestation.

Circle documents that a CCTP transfer has distinct source-message, attestation, and destination-receive steps. A V2 `complete` response with attestation bytes therefore supports **attestation available when fetched**, not destination mint or end-to-end settlement. An absent message, HTTP error, malformed payload, unexpected status, or `pending_confirmations` response cannot be promoted to completion. Even a reported `forwardTxHash` needs a destination receipt and relevant log check before claiming a mint. [Circle technical guide](https://developers.circle.com/cctp/references/technical-guide), [V2 message API](https://developers.circle.com/api-reference/cctp/all/get-messages-v2), [Circle transfer quickstart](https://developers.circle.com/cctp/quickstarts/transfer-usdc-ethereum-to-arc).

## Evidence contract and clocks

| Field or clock | Meaning and limit |
|---|---|
| Query key | Environment, source domain, and source transaction hash; V2 can return multiple messages for one transaction, distinguished by `eventNonce`. |
| Raw snapshot | HTTP status and exact response body bytes, local `received_at`, SHA-256 digest, and hash link to the preceding local row. Headers are not retained. A synthetic flag keeps fixtures separate from Circle HTTP observations. |
| Provider state | `pending_confirmations` becomes `pending`; `complete` plus well-formed attestation bytes becomes `attestation_available`. Unknown or invalid responses remain explicit. |
| Decision time | `asof` excludes snapshots received after the stated time. It proves what this local ledger had received by then, subject to the integrity and clock limits above. |
| Event time | A source-chain burn timestamp, Circle's exact signing time, and destination-chain mint time are **not** measured by this first component. |

If a pending observation is followed by a complete observation, the first observed completion is an **upper bound** on attestation availability, with polling and network delay. It is not Circle's signing timestamp or transfer latency. Circle's Fast and Standard transfers have different confirmation rules, so future analyses must stratify by mode and route rather than mix them into one latency claim. Circle also documents a 40 requests/second service limit and a five-minute block after exceeding it; any future collector must bound polling and preserve HTTP 429 as missing evidence. [Circle finality rules](https://developers.circle.com/cctp/concepts/finality-and-block-confirmations), [Circle API limits](https://developers.circle.com/cctp/references/technical-guide).

**Synthetic example:** a fixture observed `pending_confirmations` at 00:00 UTC and `complete` at 01:00 UTC. An `asof` query at 00:30 UTC must return pending; a query at 01:00 UTC can return attestation available. Both remain marked `SYNTHETIC`, and neither proves a destination mint. These times illustrate clock behavior only; they are not a measured CCTP transfer.

## Proposed next gates

1. Capture source-chain burn receipt, log index, block hash, confirmation or finality state, and reorganization revisions. Join them to the Circle message by explicit identity checks.
2. Capture destination `receiveMessage` receipt and mint evidence, then any venue deposit, available liquidity, and realized execution or market impact as separate, source-specific states. No step inherits proof from an earlier step.
3. Run a prospective, opt-in pilot with immutable query selection and scheduled snapshots. Predeclare route and transfer-mode strata, missing-data policy, timeliness and false-claim metrics. Compare each decision-time view only with information locally available then; use later chain evidence solely as an outcome label. Account for API, infrastructure, relayer, gas, spread, slippage, and failed-transfer costs before any economic hypothesis is considered.

Launch criteria for any broader service are reproducible point-in-time evidence, stable collection under rate limits, independently checked destination outcomes, and a buyer-validated workflow. Stop or narrow the work if missingness, ambiguous joins, clock drift, or costs prevent those claims. This component supplies no profit guarantee, trading qualification, or live-execution authorization.
