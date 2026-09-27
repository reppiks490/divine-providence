# JANUS ∞ Run 032 — Minimal Object Replay Graph + Fork Evidence + Kernel File-Size Fault

Run 032 advances the Run 031 receiver replay path without replacing it. The new path transfers only the content needed to reproduce the certified JANUS project state and the certificate-verification boundary, encoded as an exact SHA-256-addressed object graph.

## Object-addressed replay

`build_object_replay_graph()` exports a root object whose references lead to the signed storage certificate, optional forensic DAG, selected project-state table manifests, the minimum certificate-control rows needed by verification, and the certified DB/WAL/SHM evidence artifacts. Table rows are individual content-addressed objects. Unrelated SQLite control/runtime tables are not transferred.

`import_and_verify_object_replay_graph()` verifies every object hash and the exact transitive closure before staging. Missing objects, unreachable extras, substituted payloads, nondeterministic reference sets, schema drift, and root-reference mismatch fail before promotion. A fresh staging twin is reconstructed, the original storage certificate is independently verified against the certified physical snapshot, and only then is the staging state promoted. Successful reconstruction emits a deterministic `janus-object-reconstruction-receipt-v1`.

## Certificate branches

`detect_storage_certificate_forks()` independently verifies each signed chain entry and groups valid descendants by `(previous_chain_digest, previous_certificate_digest)`. Two or more distinct current certificates at the same branch point produce content-addressed `janus-storage-certificate-fork-evidence-v1`. JANUS records the conflict only; it does not choose a winning branch or absorb sibling trust-policy authority.

## Host fault

`run_host_file_size_limit_probe()` uses a child process with kernel `RLIMIT_FSIZE`. The probe writes only to scratch storage, catches `SIGXFSZ`, and records the resulting `EFBIG` boundary. Authoritative JANUS storage is never passed into the child.

## Authority boundary

JANUS remains limited to project-twin temporal truth/conflict/proof synchronization. No NEXUS/AION/ARGUS/ATHENA/DAEDALUS, Infrastructure, VECTOR, or ASCENSION authority is absorbed.
