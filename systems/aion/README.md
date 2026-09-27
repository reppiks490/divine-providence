# AION — The Market Remembers

AION is an isolated, read-only market memory for the Icarus intelligence stack. It records what a system could know at a decision time, reconstructs a market state from those observations, preserves the original forecast, and later appends the outcome. Its cockpit makes the provenance visible and lets an operator branch into **labeled hypothetical** conditions.

**Status:** working research foundation and synthetic cockpit. No sibling repository has been modified or connected to a live broker. No model has been certified, no live depth feed is present, and no trading performance is claimed. This repository's `docs/CURRENT.md` is the current handoff.

## Run the time machine

Python 3.11+; the core and cockpit use the standard library.

```bash
python -m aion.cli --db run/demo.sqlite3 demo
python -m aion.cli --db run/demo.sqlite3 verify
python -m aion.cli --db run/demo.sqlite3 serve --port 8765
```

Open `http://127.0.0.1:8765/`. The scene is **synthetic** and intentionally includes separate NQ/ES closed bars, a known future event schedule, later macro release, true-tier *synthetic* trade/book examples, an immutable forecast, and a delayed settlement. Every source in this scene has `origin=synthetic`, so its data cannot be mistaken for a real tape. The server is read-only and loopback-bound.

Useful commands:

```bash
python -m aion.cli --db run/demo.sqlite3 timeline
python -m aion.cli --db run/demo.sqlite3 frame 1790081932000000000
python -m aion.cli --db run/demo.sqlite3 predictions
python -m unittest discover -s tests -v
```

An authentic source must be registered from a reviewed manifest, then supplied as versioned observations:

```bash
python -m aion.cli --db run/research.sqlite3 register path/to/source.json
python -m aion.cli --db run/research.sqlite3 append path/to/observation.json
```

Version 1 exchange field shapes are in [`contracts/`](contracts/README.md). The Python constructors and ledger enforce cross-field clock, source, evidence and sequence rules.

Do not label TradingView OHLC exports as trade or depth events. A source manifest's declared capability is a *review assertion*, not cryptographic proof that the market feed was genuine. The source reviewer must verify the raw bytes, provider, license, clock semantics and sequence policy before using true-trade or true-depth tiers. Each bar's `event_ns` is its **close**, `available_ns` is when that completed bar was usable, and revisions carry a stable `source_event_id` with increasing `revision`.

## What exists

| Capability | Implementation | Boundary |
| --- | --- | --- |
| Source identity | Immutable, versioned source manifests with raw-source SHA-256 and capability tiers | Similar filenames and chart types stay distinct. |
| Event memory | Append-only SQLite with a global hash chain and idempotent source events | This detects ordinary mutation; it is not a signed third-party audit log. |
| As-of reconstruction | Availability-gated reads and visible macro revisions | Provider availability must be verified during source onboarding. |
| True book/flow evidence | Ordered snapshots/deltas, gap invalidation and recovery; true trades by aggressor | Only for registered, reviewed feeds; synthetic demo remains synthetic. |
| Time/price atlas | Separately identified representations, right-bar-confirmed pivots, labeled candle-origin hypotheses | No causal or executable order-block claim. |
| Forecast/outcome | Evidence- and frame-bound immutable predictions, separately appended settlement | Supplied outcomes require independent source review. |
| Scenario chamber | Deterministic depth, volatility, macro and source-loss branches | Synthetic stress does not prove alternate fills. |
| Federation | Read-only preview packets for Icarus, DAEDALUS, ATHENA and ARGUS | These are interface contracts, not running sibling integrations. |

## Architectural questions this machine answers

- Which source, revision, and chart representation produced a claim?
- Was the event released, received, and complete by the decision time?
- Was a supposed book wall true depth, true trades, or only a candle hypothesis?
- Did a missing sequence or stale source invalidate the state?
- What exact forecast was made before its result was known?
- How does a decision's context change under an explicitly hypothetical stress?

## Ownership

Icarus owns execution and paper fill telemetry. DAEDALUS owns protected research evidence and promotion. ATHENA owns advisory state and risk routing. ARGUS owns validated microstructure semantics. AION owns the shared time/identity/replay evidence contract. `docs/INTEGRATION.md` specifies the proposed interfaces; no code path in AION can place an order.

Read [`AGENTS.md`](AGENTS.md), [`docs/CURRENT.md`](docs/CURRENT.md), and [`docs/DECISIONS/ADR-0001.md`](docs/DECISIONS/ADR-0001.md) before extending this build.

The proposed CSV-first extension is [`PARALLAX`](docs/PARALLAX-PROPOSAL.md). It has not been implemented or published to a shared GitHub repository.
