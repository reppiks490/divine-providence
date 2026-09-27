# ATHENA Supervisory Fabric

Tested starter framework + full blueprint for the supervisory/world-model layer above DAEDALUS, ARGUS and Icarus.

Start with `docs/BLUEPRINT.md`, `INTEGRATION_MAP.md`, and `docs/NEXT_MODEL_HANDOFF.md`.

ATHENA has **no live execution authority**. The starter code implements contract/firewall, expert routing, uncertainty aggregation, advisory risk governance, state-graph primitives, counterfactual transforms, and research-priority ranking.

Run:
```bash
python -m pip install -e . pytest
pytest -q
```
