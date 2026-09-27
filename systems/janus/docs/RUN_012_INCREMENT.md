# JANUS ∞ Run 012 — Content-Addressed Causal Evidence Bundles + Receiver Verification

Run 012 makes the Run 011 minimal causal certificate portable. `build_causal_evidence_bundle(change_id)` computes the evidence closure needed to reproduce a certificate: connected proof bundles and lifecycle events, normalization decisions, participating facts, explicit adjudication policies, and the dependency subgraph that justifies blast radius. Each object is canonicalized and SHA-256 addressed; a deterministic root digest commits to the sorted chunk set.

`verify_causal_evidence_bundle()` fails closed on payload tampering, key/hash disagreement, manifest/chunk disagreement, or root mismatch. `import_causal_evidence_bundle()` verifies before mutation, imports in dependency-safe order, and allows a fresh receiver to recompute `generalized_truth_delta()` and reproduce the sender's certificate digest.

The bundle is selective: unrelated proof bundles are excluded. Source observations remain immutable and sibling authority boundaries are unchanged.
