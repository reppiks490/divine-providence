# Event Fabric

The Event Fabric converts public, timestamped market-moving information into an auditable event family that can be replayed later without future-known contamination.

## Pipeline

`public signal -> canonicalization -> duplicate/syndication cluster -> append-only event ledger -> market observation -> shock graph -> confidence decay -> replay bundle`

### Duplicate and syndication control

Multiple reposts, wire stories, mirrors, quote-posts, and crawled copies can describe the same underlying event. Collapse them into an event cluster while preserving independent source families. Source count is not evidence independence.

### Event ledger

Each canonical event is committed to a hash-chained record carrying event, publication, and retrieval clocks. Revisions append a new record; they do not rewrite the first-seen event. This preserves what was known at a given time.

### Shock graph

Market responses are stored as observed cross-asset nodes with standardized move magnitude, lag, and transmission channel. The graph describes measured propagation; it does not predict direction and does not turn temporal ordering into a causal claim.

### Confidence decay

Attribution confidence decays as an event ages without new confirming evidence and is penalized by unresolved source conflict. New evidence may strengthen or weaken a prior association, but the original record remains immutable.

### Replay bundles

A replay bundle includes only evidence and market observations available on or before the requested cutoff. It carries a deterministic bundle hash so later analysis can verify the exact point-in-time input set.

## Political/public-figure boundary

Prioritization is based only on market relevance, topic relevance, recency, historical measured impact, and source coverage. It must never score political merit, ideology, electoral value, popularity, or persuasion potential.
