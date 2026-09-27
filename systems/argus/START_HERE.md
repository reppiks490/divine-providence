# START HERE — ARGUS Microstructure Intelligence OS

**What it is:** microstructure truth layer spanning order flow, book mapping, auction/liquidity intelligence, empirical order-block lifecycle, impact and execution-quality modeling, plus explicitly quarantined candle-only proxies.

**Where it goes:** `<workspace>/argus-microstructure-os/` as a separate sibling repo.

**Read in order:**
1. `docs/BLUEPRINT.md`
2. `INTEGRATION_MAP.md`
3. `docs/NEXT_MODEL_HANDOFF.md`
4. `README.md`

**Already implemented:** tested starter contracts with evidence tiers, signed flow stats, true-depth book/microprice metrics, auction profile primitive, empirical order-block scoring primitive, book-walk execution estimate, candle-proxy firewall and evidence-aware fusion.

**Purity rule:** candle proxies can never masquerade as true trade or L2/depth evidence.

**Authority:** features/advisories only. No broker/order authority.
