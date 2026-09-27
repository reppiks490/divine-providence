# Run 010 self-review

A fresh reviewer/subagent surface was not exposed, so this is explicitly an author self-review and is weaker than independent review.

Reviewed failure classes: empty dependency set; unknown proof; open-ended validity interval; multiple fact boundaries inside an affected interval; proof replacement chain; later proof status after historical supersession; unrelated conflicts; deterministic repeated execution; read-only behavior.

Important finding found and fixed with RED→GREEN regression: causal-chain membership originally relied on `proof_provenance_graph()`'s latest effective lifecycle state, so a later `revoked` event could hide an earlier supersession edge. Run 010 now derives causal lineage from all historical supersession events. Effective proof validity remains knowledge-time aware.

No additional Critical/Important finding remained after the fix pass. Exposure scoring is deliberately labeled as a transparent prioritization heuristic rather than a probabilistic severity estimate.
