# Run 010 cycle status

- Deep Research: explicitly attempted/discovered; first-party Deep Research was not exposed in this runtime and was not substituted.
- Capability preflight: performed. Plugin Management namespace was visible, but its Deep Research search action was not callable; the automation skill catalog returned no skills.
- Live repository reconciliation: not performed; this remains an offline proof-carrying continuation.
- TDD: four Run 010 tests first failed because `automatic_causal_horizon` did not exist. A fifth regression then failed because latest-status provenance erased an older supersession edge; that root cause was corrected and the regression passed.
- New capability: automatic causal horizon discovery, historical proof-chain traversal, automatic replay-boundary selection, exposure scoring, and deterministic minimal causal certificate.
