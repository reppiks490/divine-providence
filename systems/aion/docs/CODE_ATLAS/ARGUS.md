# ARGUS code atlas — saved handoff snapshot

Source: saved `ARGUS-MICROSTRUCTURE-OS_HANDOFF.zip` from 2026-09-23. Starter framework and 4 passing starter tests; no authenticated L2 feed claimed. Current private working tree unknown.

| Module group | Saved responsibility | AION boundary |
| --- | --- | --- |
| `contracts.py`, `proxy.py`, `fusion.py` | Evidence-tier firewall and proxy handling | Carry every tier and quality flag intact; bars cannot become true trade/depth. |
| `orderflow.py`, `bookmap.py`, `auction.py`, `orderblocks.py` | Starter flow/book/auction/block primitives | Supply authentic ordered events; ARGUS owns empirical feature definitions and lifecycle validation. |
| `execution.py` | Starter impact estimate | Compare later with independently recorded Icarus fills; candle backtests do not validate queue or slippage. |

The handoff explicitly named event journal, deterministic depth-delta replay, sequence gaps and recovery as the next build stages. AION's generic `set/delete` book adapter is a proof of contract; venue-specific order semantics remain an ARGUS/provider review item.
