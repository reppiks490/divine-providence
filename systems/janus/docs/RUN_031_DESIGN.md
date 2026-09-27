# JANUS ∞ Run 031 Design — Independent Receiver Replay + Certificate Chain

## Intent
Advance the Run 030 storage-state certificate from sender-local verification to portable, fresh-receiver reconstruction without expanding JANUS authority beyond project-twin temporal truth/conflict/proof synchronization.

## Scope
1. Export a portable receiver replay bundle containing the minimum database/proof material required for a fresh JANUS receiver to reconstruct and verify the certified state.
2. Import/replay that bundle into an empty receiver and require exact reproduction of the certified project/proof/storage summary before certificate verification succeeds.
3. Add a content-addressed certificate chain that binds previous certificate digest, current certificate digest, project-state delta, storage-state delta, receipt-head delta, recovery delta, and forensic-DAG delta; reject tampering, cycles, and predecessor mismatch.
4. Add one additional isolated kernel-enforced host fault class using process resource limits, without risking authoritative JANUS storage.
5. Keep the live-reconciliation gate unchanged except for any contracts needed to package Run 031.

## Non-goals
- No ownership of NEXUS/AION/ARGUS/ATHENA/DAEDALUS/Icarus semantics.
- No live Git adoption without an exposed authoritative checkout.
- No claim of hardware power-loss or true block-device fault coverage.

## Acceptance invariants
- A fresh empty receiver can reconstruct the sender-certified project/proof state from the portable bundle and independently verify the certificate.
- Missing/tampered bundle objects fail closed before receiver mutation is promoted.
- Certificate-chain verification fails on predecessor mismatch, tampered deltas, or cycles.
- The added host-fault probe is kernel-enforced and isolated to scratch storage.
- Full inherited regression suite remains green.
