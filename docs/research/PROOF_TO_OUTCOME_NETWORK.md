# Proof-to-Outcome Network

## The idea

Build a subscription research service that turns consequential economic events into **replayable evidence packets**. A packet answers four questions: what happened, what was actually knowable at a chosen decision time, which assets or operations could be affected, and what happened afterward. The initial customer is an institutional crypto treasury, custodian, or market operations desk that must investigate transfers and incidents quickly. The same contract can later cover exchange outages, issuer revisions, SEC filings, and other primary-source events.

The proposed compounding asset is a permissioned, outcome-labeled history of event claims and their revisions. Each observed case improves parsers, exception handling, timing calibration, and falsification tests. This is a product hypothesis, not a claim of unique intellectual property, paying demand, or investment returns.

## Why this wedge

| Option considered | Strength | Constraint |
| --- | --- | --- |
| Standalone CCTP transfer alert | Precise, public first source and clear operator question | Too narrow to be the whole business; an attestation is not a mint. |
| General AI-agent trace platform | Broad market | Existing products already provide tracing and evaluation; a new generic platform has weak differentiation. |
| Economic-event evidence and outcome network | Combines decision-time proof, revisions, exposure, and measured outcomes across event classes | Needs source rights, reliable acquisition, labeled outcomes, and customer validation. |

[Forta](https://docs.forta.network/en/latest/network-overview) and [Nansen](https://app.nansen.ai/smart-alerts) already offer onchain alerts. [LangSmith](https://www.langchain.com/langsmith/evaluation) already offers AI evaluation and traces. The proposed distinction is a narrower contract: an event claim must retain its source bytes, knowledge time, revision, finality scope, and separately verified outcome, so an earlier decision can be replayed without later facts leaking backward. No market-wide originality claim follows from that distinction.

## Working first lane: CCTP attestation visibility

The research-only `divine_providence.onchain_research` package on this branch records exact response body bytes and HTTP status from Circle CCTP V2 fetches, local UTC receipt times, and a local hash chain. Its `timeline`, `asof`, and `verify` commands demonstrate a decision-time evidence packet for a specified EVM-style source transaction hash. A `complete` message means Circle reports attestation bytes were available when fetched. It does **not** establish destination mint, Circle's signing timestamp, economic impact, or tradable alpha. The component note and precise commands are in [ONCHAIN_PROOF_CLOCK.md](ONCHAIN_PROOF_CLOCK.md).

Circle documents source-message, attestation, and destination-receive steps separately; Fast and Standard transfers also have different confirmation rules. [V2 message API](https://developers.circle.com/api-reference/cctp/all/get-messages-v2), [technical guide](https://developers.circle.com/cctp/references/technical-guide), [finality rules](https://developers.circle.com/cctp/concepts/finality-and-block-confirmations).

## Build beyond the first lane

1. **Complete the transfer lifecycle.** Capture source burn receipt, chain and block identity, finality/reorg state, Circle attestation, destination receive receipt, and mint event as separate proofs. Do not infer a later stage from an earlier one.
2. **Add an exposure graph.** Link an event to affected chain, asset, issuer, protocol, venue, and optionally a customer's own holdings under a permissioned contract. Public addresses remain identifiers, not inferred people or intent.
3. **Freeze testable hypotheses.** Before seeing outcomes, record the affected asset or operational metric, decision timestamp, horizon, baseline, failure condition, and cost model. Later outcomes settle the claim without changing the frozen version. Research reports show missingness and uncertainty as well as wins.
4. **Offer proof packets by API and workflow.** A paying customer should be able to open an alert, inspect raw-source hashes and revisions, replay its knowledge state, and export an audit packet. No trade-routing authority is included.
5. **Generalize only after the first lane works.** Add an independent event class, such as a primary SEC filing or exchange service notice, using the same evidence contract. Keep provider-specific clock and revision semantics explicit.

## Business experiment

Start with a concierge pilot for custody and treasury operations. The proposed value is shorter incident investigation, fewer false settlement assumptions, and an auditable record for internal decisions. Subscription and API fees are plausible pricing models; willingness to pay has not been measured. RocketReach company-level search surfaced possible custody organizations, which is only a prospect inventory, not customer validation. Do not contact anyone without separate authorization.

Predeclare pilot measures: source coverage, correct lifecycle classification against independently checked chain receipts, time from a public change to local observation, false completion claims, investigation minutes saved, and paid conversion. If an economic-signal pilot is later approved, use chronological/purged splits, a sealed holdout, realistic fees/slippage/latency, uncertainty intervals, and a baseline available at the same decision time. Stop an event class when missingness, ambiguous joins, stale clocks, costs, or buyer feedback defeat its stated value.

## Authority and current limits

This branch is a research artifact. It has no continuous collector, authenticated destination-mint verification, external hash-chain witness, customer exposure integration, measured trading edge, or signed customer contract. `candidate_qualified=false`, `execution_authorized=false`, and `production_authorized=false` remain the applicable research posture. A local response hash proves the bytes stored in this local ledger have not been ordinarily modified; it does not authenticate Circle's signing key or defeat replacement of the entire database. No profitability, exponential growth, or live trading result is claimed.
