# SYSTEM INTEGRATION MAP — ICARUS / DAEDALUS / ATHENA / ARGUS

## Ownership boundaries

- **Icarus** — controlled execution/strategy runtime. Owns broker/order state, fills, positions, execution telemetry, and production risk enforcement.
- **DAEDALUS Research OS** — skeptical research scientist. Owns data provenance, hypothesis/model research, leakage-safe validation, protected evidence, adversarial tests, experiment memory, promotion evidence, and research-only export manifests.
- **ATHENA Supervisory Fabric** — state-aware supervisor. Owns world-state representation, uncertainty, contextual expert suitability, counterfactual stress, system-wide abstention/risk advisories, active-research scheduling, and cross-system lineage. It does not place orders.
- **ARGUS Microstructure Intelligence OS** — microstructure truth layer. Owns order-flow, depth/book-map, auction/liquidity intelligence, empirically scored order-block lifecycle, impact/execution-quality estimates, and explicit candle-only proxies when real trade/depth data are unavailable. It does not place orders.

## Direction of information

```text
Historical/Research Data ──> DAEDALUS ──research evidence────┐
Live Trades/Depth ─────────> ARGUS ─────microstructure───────┤
ARGUS prospective research ─────────────> ATHENA advisory────┤
Icarus telemetry ────────────────────────────────────────────┤
Cross-asset/state feeds ────────────────────────────────────> ATHENA
                                                             │
ATHENA advisory state/risk/routing ─────────────────────────> Icarus
DAEDALUS promoted research-only manifest ───────────────────> Icarus review/import boundary
ARGUS execution-safe microstructure features ───────────────> Icarus review/import boundary
```

## Non-negotiable firewalls

1. DAEDALUS protected-holdout outcomes never become development-selection inputs.
2. ATHENA may request research but may not spend or reinterpret DAEDALUS holdouts outside DAEDALUS protocol.
3. ARGUS must label every feature with evidence provenance: real depth, real trades, inferred trades, or candle proxy.
4. Candle proxies may never be labeled as L2/book-map evidence.
5. ATHENA and ARGUS initially export **advisories/features only**; neither has broker/order authority.
6. Icarus remains the only production execution authority unless a future explicit architecture review changes that boundary.
7. Every cross-system payload carries event time, ingestion time, source identity, representation identity, version, quality flags, and lineage.

## Recommended workspace

```text
<workspace>/
  Icarus/
  Icarus-engine/
  multi-level-csv/
  daedalus-research-os/
  athena-supervisory-fabric/
  argus-microstructure-os/
```


## Verified ARGUS -> ATHENA research sidepath

The hub connection `argus-athena-research` now verifies a separate
retrospective research path:

```text
ARGUS v2 prospective study
  -> registered Kaplan-Meier uncertainty
  -> argus-athena-research-v1 envelope
  -> publication only after follow-up cutoff
  -> ATHENA AdvisoryJournal
  -> local receipt-time visibility
```

The envelope preserves manifest/cohort IDs, lifecycle revision, evidence tiers,
predeclared confidence alpha, administrative-censor lineage, and explicit
research-only authority flags. Publication time is not treated as local
knowledge; ATHENA cannot see the artifact until ingestion time.

This path is intentionally separate from the live NEXUS instant fabric. It
does not convert retrospective study evidence into live market truth, broker
authority, or a production decision.
