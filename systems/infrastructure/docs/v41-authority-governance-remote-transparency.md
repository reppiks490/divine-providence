# V41 Authority Governance and Remote Transparency History

V41 adds append-only governance-authority-set epochs. Thresholds may not decrease and a successor authority set must retain exact identity/key overlap of at least the prior quorum. HEAD rollback/replay fails closed.

V41 also persists append-only checkpoint histories per remote peer/log. Per-peer sequence rollback/gaps and HEAD rollback fail closed. Equal-sequence hashes can be compared across peers; disagreement is explicit equivocation evidence.

These are evidence and supervisory-safety surfaces only. They grant no execution, promotion, routing, lease, sibling semantic, or live-trading authority.
