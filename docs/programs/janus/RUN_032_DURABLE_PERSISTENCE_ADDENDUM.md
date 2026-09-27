# JANUS ∞ Run 032 Durable Persistence Addendum

The final locally sealed Run 032 checkpoint was byte-compared against files already present in Google Drive under the unsuffixed Run 032 names. Those Drive files were older/intermediate bytes and did not match the final resealed local checkpoint, so they were preserved unchanged as lineage evidence rather than overwritten.

Authoritative final offline seal:
- `JANUS_INFINITY_HANDOFF_RUN_032.zip` SHA-256: `543419c3f8bb52ab2a911aa49af502e13b5c15e305a6ad379db7ea75948c4199`
- `STATE_CAPSULE_RUN_032.md` SHA-256: `a91e3dec9802cd1dc4a4546cf8cffc6feb71d53c3a004a2efddd4cce2331e3f0`

Observed pre-existing Drive bytes before final persistence:
- unsuffixed Drive ZIP SHA-256: `ec6976f153d6c52b2c02dd46f0e5583d67e5c181629771c5fc9ed92e2b4eadcd`
- unsuffixed Drive capsule SHA-256: `37934162ea4030d90094f37610343e85d584d3922a44585d3e4a0d3413b8f229`

The final verified bytes are to be persisted under distinct `_SEALED` names in `/Google Drive/Icarus Governance/Icarus-Build/` so no prior checkpoint is overwritten.
