# ADR 0005: Pin the NEXUS v1.16 AION causal sibling contract

Status: accepted for branch validation (2026-10-01). Extends ADR 0004.

## Context

The consolidated AION boundary was intentionally hardened after v1.15:

- observation receipts can no longer claim an earlier `observed_receipt` availability;
- synthetic observations cannot hide under non-synthetic source manifests;
- frozen forecast frames preserve event/gap ledger cutoffs;
- late imports and later gap transitions cannot rewrite the evidence cited by a prediction;
- NEXUS derived genealogy and source-health context now use the explicit
  `derived_at_decision` basis instead of being mislabeled `synthetic`.

The exact Python 3.11.16 path-independent sibling snapshot generated in CI is:

`65cba148bc5df86bd4b660ba15b14e6c58c113fa00fecdf3e22ea745a13ffe9a`

Only AION `contracts.py` and `store.py` are semantic changes relative to the
v1.15 baseline. ARGUS contracts, ATHENA contracts and the DAEDALUS bridge are unchanged.

## Decision

- Record `sibling_contract_drift_baseline.v1.16.monorepo.json` without modifying
  the immutable v0.3 or v1.15 baselines.
- Make v1.16 the current PROMETHEUS NEXUS contract pin.
- Keep v0.3 and v1.15 pins only for their exact recorded historical bundle hashes.
  A fresh bundle cannot be relabeled with a historical identity, and a recorded
  historical bundle cannot be relabeled as current.
- Recompute and verify `bundle_hash` from canonical bundle content before binding.
- Under v1.16, verify the AION-specific causal rule that every
  `origin=nexus_derived` observation is context using `derived_at_decision`
  with `event_ns == available_ns` and without a synthetic label.
- Preserve all production/execution firewalls.

## Consequences

PROMETHEUS can reconnect to the current NEXUS/AION contract only after the live
monorepo snapshot exactly matches v1.16. Any later semantic sibling-boundary change
again produces `CONTRACT_DRIFT` and quarantines the input until another reviewed,
versioned pin is created.

This pin is evidence compatibility, not model approval, trading edge, or execution authority.
