# Adaptive query planner

A research task is compiled into a query graph, not a single string.

## Query families

For each research question, generate selected families:

- exact entity/identifier queries
- synonym and alias queries
- date-bounded queries
- primary-source targeting (`site:`, official domain, filing ID, contract address, DOI, ticker/exchange)
- contradiction/adversarial queries
- historical terminology
- jurisdiction/language variants when relevant
- implementation/code queries
- scholarly queries
- market/financial identifier queries

## Branching

New entities discovered during retrieval may create child queries when they are causally or evidentially important. Child queries inherit the original constraints, date window, and provenance requirements.

## Stop conditions

Stop expanding a branch when:

- the claim is supported by sufficient independent evidence
- new results are mainly duplicates or syndications
- remaining uncertainty is explicitly known and not worth additional cost
- the source class is exhausted within the allowed scope
- further access requires unavailable authorization

## Budgeting

The planner assigns a retrieval budget by expected information gain, not evenly across providers. Authoritative structured or primary sources get priority; broad crawling receives larger budgets only for discovery-heavy tasks.
