# SuperMesh-X v3.5.0

## Crash-tail quarantine recovery
- Added an explicit `DurableGossipJournal.recover()` path for incomplete final journal writes.
- Recovery is intentionally narrow: only a malformed/incomplete final JSON fragment at EOF is quarantined; authenticated/hash-chain corruption remains fail-closed.
- The torn fragment is durably written to a unique quarantine file before the active journal is atomically replaced with the last complete prefix.
- The recovered prefix is replayed through the normal signature/hash-chain/policy verification path before use.
- Added regression coverage proving strict load still rejects torn tails and recovery refuses valid-JSON integrity tampering.

## Compatibility
- Existing `load()` behavior remains strict and unchanged.
- Existing v3.4 witness policy, gossip replay, and legacy receipt semantics remain backward compatible.
- Protected v3.1 stable baseline is not overwritten or promoted.
