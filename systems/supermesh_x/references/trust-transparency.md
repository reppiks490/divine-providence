# Durable Trust Root & Transparency — v3.1.0

SuperMesh-X v3.1 adds a provider-neutral trust-root and transparency reference layer. It persists public trust policy only, requires sequential epoch rotation, requires both current-root and next-root signature thresholds for root changes, and never treats signatures as execution authority.

The transparency log uses domain-separated SHA-256 Merkle leaves/nodes and supports inclusion proofs plus Ed25519-signed checkpoints chained by the prior checkpoint digest. Same-size conflicting roots and rollback chains fail closed. The design is inspired by TUF root-rotation principles and RFC 6962 transparency semantics, without claiming certification or wire-level compatibility with either project.

Private keys, `secretref://` values, passwords, and execution capability grants are not valid trust-policy/transparency content.
