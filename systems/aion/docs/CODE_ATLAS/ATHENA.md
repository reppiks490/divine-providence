# ATHENA code atlas — saved handoff snapshot

Source: saved `ATHENA-SUPERVISORY-FABRIC_HANDOFF.zip` from 2026-09-23. Phase-0 starter and 3 passing starter tests; current private working tree unknown.

| Module group | Saved responsibility | AION boundary |
| --- | --- | --- |
| `contracts.py`, `firewall.py` | Data plane, provenance and no-order advisory types | Map source availability/quality/representation into ATHENA's versioned input after contract review. |
| `state_graph.py`, `uncertainty.py`, `router.py`, `risk.py` | State and advisory primitives | AION supplies reproducible observations; ATHENA owns inferred world state, uncertainty and abstention. |
| `counterfactual.py`, `scheduler.py` | Deterministic scenario and research-priority primitives | AION scenario packets remain labeled synthetic; ATHENA cannot spend DAEDALUS holdouts by request. |

The handoff proposed an append-only journal and deterministic replay as future work. AION's ledger can provide shared evidence only if a reviewed interface prevents duplicate, conflicting clocks and owner responsibilities.
