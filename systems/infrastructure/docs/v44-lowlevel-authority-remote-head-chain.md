# V44 Low-Level Authority Durability + Signed Remote Head Chain

V44 exposes safe authority-record/HEAD failure boundaries in `AuthoritySetStore`. A crash after the record but before HEAD leaves verification fail-closed; `repair_head()` advances HEAD only after independently validating every authority record, linkage, threshold and prior-quorum overlap. Writes use temporary files, atomic replace, file fsync and directory fsync when durability is enabled.

V44 also persists signed remote transparency history heads in a predecessor-hash-linked append-only chain. Each entry retains the signed peer head and binds the previous entry hash. Chain verification revalidates signatures, monotonic sequence/time, linkage, entry hashes and HEAD. Independent chains for the same peer expose equal-sequence/different-record-hash evidence as temporal split-view/equivocation.

These mechanisms authenticate and preserve evidence only. They grant no execution, mutation, promotion, routing, lease, sibling-system, or live-trading authority.
