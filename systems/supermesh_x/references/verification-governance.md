# Verification and governance

## Evidence record

Every important observation should carry: source/provider, source class, locator, retrieved time, event time if known, availability time if known, raw/normalized value, units, confidence, and transformation lineage.

## Quality gates

- freshness/staleness
- primary-source preference where practical
- independent corroboration for consequential factual claims
- duplicate/copy-source detection
- timestamp and timezone validity
- identifier/schema/unit consistency
- point-in-time validity for historical analysis
- missingness disclosure
- contradiction preservation
- reproducibility where possible

## Authority boundaries

Research access does not authorize writes, trades, deployments, credential changes, purchases, or account mutations. Each runtime/provider keeps its own permissions and confirmation rules.

## v2.4 pre-swarm release gate

Before enabling computer or swarm execution, verify durable restart/takeover, stale-fence rejection, CAS conflict behavior, suspension/resume idempotency, cancellation fencing, checkpoint payload non-persistence, cross-controller capacity accounting, overcommit rejection, capability allowlisting, and credential-reference-only admission. These are release gates, not advisory checks.
