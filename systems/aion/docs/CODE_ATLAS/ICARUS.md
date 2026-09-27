# Icarus code atlas — accessible checkpoint

Repository `reppiks490/Icarus`, reviewed public main `007e701` and isolated ML branch `e89acba` on 2026-09-23. These branches have diverged; neither was changed by AION. Verify newer commits before adapter work.

| File or boundary | Existing responsibility | AION interface or caution |
| --- | --- | --- |
| `icarus_engine/runtime.py`, `backtest.py` | Paper runner, warm-up and replay/fill accounting | Later settlement must reference a separate recorded Icarus outcome, not a fabricated fill. |
| `icarus_engine/advisory.py`, `orchestration.py` | Isolated research/advisory review and bounded model roles | AION exports read-only evidence; it cannot approve or apply an input patch. |
| `icarus_engine/market_sources.py` | Public collectors, publication/receipt fields and source records | Map first-known timing/revisions without confusing period, publication and receipt. |
| `icarus_engine/microstructure.py` | TradeEvent/TradeAggregator with sequence and completed watermark; no connected futures tick provider | Consume provider-verified events or preserve unknown. |
| `icarus_engine/events/calendar.py` | Main event-window and seed events | Main can expose an upcoming event's `surprise_abs` through its feature API; isolated ML branch restricts event hits to prior prints. This is a code-path risk, not evidence of a fitted-model leak. |
| `icarus_engine/trainers/`, `audit/` | Research models and candidate audits; branch records 44 fitted cells | AION does not replace trained models or assert their predictive validity. |

Owner rules from this checkpoint: avoid Pulse/emulator rewrites, keep Icarus the execution authority, do not treat stock context as a futures fill tape, and keep broker/order authorization separate.
