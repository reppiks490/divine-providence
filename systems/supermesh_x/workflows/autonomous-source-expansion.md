# Autonomous Source Expansion

1. Start with the most authoritative available source for the requested claim.
2. Generate orthogonal query/source families: primary, structured, temporal, contradictory, scholarly, regulatory, repository, archive, community when appropriate.
3. Rank frontier items by relevance, novelty, source-family diversity, expected information gain, cost, and provider health.
4. Fetch the highest-value items within the budget.
5. Normalize and add them to the provenance/evidence graph.
6. Recompute gaps, contradictions, and novelty yield.
7. Stop when novelty collapses for the configured patience window, the evidence requirement is satisfied, or budget/permission boundaries are reached.
8. Never expand into unauthorized/private sources or bypass access controls.
