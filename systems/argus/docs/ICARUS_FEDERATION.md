# ARGUS → ICARUS research federation

ARGUS publishes research state into the canonical ICARUS interface through a
receipt-only federation contract.

The machine-readable contract is:

`systems/argus/contracts/icarus_federation.v1.json`

## Boundary

Producer:

`reppiks490/divine-providence`

Consumer:

`reppiks490/Icarus`

Ingress:

`automation_intelligence/mcp_interface/events`

Receipt schema:

`icarus-interface-event-v1`

Consumer surface:

MCP Evolution and Adaptive Brain observability.

## Authority

The federation ceiling is `RESEARCH`.

`execution_authorized=false`

`production_decision_authorized=false`

`broker_substitution_authorized=false`

A receipt is evidence/observability metadata. It is not a broker instruction,
production strategy activation, or permission to alter ICARUS engine/runtime
ownership boundaries.

## Verification semantics

The federation preserves the source repository and exact source commit of each
receipt. A blocked or unverified source branch remains blocked or unverified
when surfaced in ICARUS.

GitHub Actions infrastructure failure is not converted into a research pass.
Only exact-head source runs that execute the required gates and succeed may be
represented as verified milestones.
