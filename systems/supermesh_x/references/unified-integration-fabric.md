# Unified Plugin Mesh

SuperMesh-X is a single capability facade over many optional plugins, skills, connectors and public/authorized data sources. It does not bundle third-party credentials or magically install providers.

At runtime, discover providers from `config/plugin-universe.json`, map the prompt to capability contracts, check actual connection/auth/readiness state, choose the smallest sufficient provider set, and escalate only when evidence quality or coverage requires it.

Behavioral/orchestration skills and data providers remain separate. Orchestrators may choose and coordinate tools; they do not inherit permissions from them. Data providers supply observations; they do not control agent workflow. Brokerage/action providers have an independent write-authority gate.

New providers can be added by declaring `id`, `mode`, `priority`, and `capabilities` without rewriting the central router.
