# V46 Durable Equivocation Evidence Ledger

V46 persists only independently witnessed, cryptographically valid equivocation bundles in a predecessor-linked append-only ledger. Canonical evidence hashes deduplicate replayed bundles. Every reopen re-verifies observer receipts and conflicting signed heads; entry tamper, linkage corruption, duplicate evidence and HEAD rollback fail closed. The ledger is evidence-only and has no execution or infrastructure mutation authority.
