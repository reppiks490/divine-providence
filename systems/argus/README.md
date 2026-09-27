# ARGUS Microstructure Intelligence OS

Tested starter framework + full blueprint for a multi-domain microstructure system centered on order flow, book mapping, auction/liquidity behavior, empirical order blocks, and execution quality.

Start with `docs/BLUEPRINT.md`, `INTEGRATION_MAP.md`, and `docs/NEXT_MODEL_HANDOFF.md`.

The included starter code explicitly separates **TRUE_DEPTH / TRUE_TRADE / INFERRED_TRADE / CANDLE_PROXY** evidence so candle data cannot masquerade as L2. It has **no live execution authority**.

Run:
```bash
python -m pip install -e . pytest
pytest -q
```
