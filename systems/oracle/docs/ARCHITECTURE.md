# ORACLE Architecture

ORACLE coordinates the Financial and Research surfaces of Icarus. It owns research questions, financial-state aggregation, research scheduling, thesis assessment, evidence routing, counterfactual specifications, and audit lineage.

It does **not** own market-data truth (NEXUS), microstructure truth (ARGUS), durable evidence memory (AION), research validation/promotion (DAEDALUS), supervisory risk/abstention (ATHENA), or broker/order authority (ICARUS).

Core path: NEXUS/other observations -> causal FinancialStateEngine -> anomaly Trigger -> Hypothesis -> Research Exchange -> prioritized ResearchJob -> sibling evidence -> ThesisAssessment -> candidate/shadow gate. Every outbound packet remains research-only unless an external authority explicitly promotes it later.
