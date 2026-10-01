# PROMETHEUS -> ASCENSION handoff CLI

PROMETHEUS now exposes the existing runtime handoff serializer through the
`prometheus-loop` command.

The command operates only on an existing append-only PROMETHEUS research-memory
file and requires an exact `research-provenance:` manifest ID plus one bound
`plugin-evidence:` ID:

```text
prometheus-loop export-ascension-handoff \
  --memory <research-memory.jsonl> \
  --provenance-manifest-id <research-provenance:...> \
  --plugin-evidence-id <plugin-evidence:...> \
  --output <optional.json>
```

The exporter reuses the fail-closed runtime checks in
`prometheus_loop.handoff`: strict `REQUIRE_VERIFIED` provenance, exact
content-addressed runtime artifacts, verified receipt semantics, byte-for-byte
provenance-manifest binding, and no invented ASCENSION authority.

Stdout always contains the exact JSON export. `--output` writes the same JSON
for transport to the separately governed ASCENSION verification plane.

This command does not create signatures, trust policy, collision verdicts,
transparency proofs, witness evidence, authentication, Transfer, production
promotion, broker authority, or execution authority.
