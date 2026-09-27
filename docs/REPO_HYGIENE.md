# Repository hygiene: exclusions, large files, secrets

## Excluded from Git (kept in the source corpus)

| Material | Size | Reason |
|---|---|---|
| 250 ZIP checkpoints / aggregates (`*_Checkpoint_*`, `supermesh_x_v*`, `infrastructure_supervisory_loop_v*`, `DAEDALUS_*`, `JANUS_*`, `ICARUS_*EVERYTHING*`, `OPUS_NON3D_*`) | ≈370 MB | Historical snapshots, ancestors of the canonical builds or re-packagings of them (24 exact duplicates by SHA-256). Canonical content is extracted into `systems/`; the identity of each source is in `provenance/`. |
| 18 git bundles (PROMETHEUS, ORACLE, NEXUS) | ≈2 MB | History of three subsystems. Canonical trees are in `systems/`. Recommended: publish them as tags or branches of per-subsystem history if needed, not as blobs. |
| `NEXUS artifacts/` (32 loop iterations × ≈48 MB JSON) | 1.2 GB | Generated research-loop output; reproducible from code plus the external CSV corpus. |
| `infra_loop_journal.jsonl`, `*.sqlite3`, `artifacts/runs/` | small | Runtime state written by the subsystems. |
| `OrderBlockPro_*.mp4` ×2, `Mini_MOnster_Fortress.mp4` | 26.5 MB | Source media. The OrderBlockPro analysis derived from the videos is in `docs/research/orderblockpro/`; the third video is unrelated. |
| OrderBlockPro screenshots inside `OPUS_NON3D_*` | ≈81 MB | Image evidence; its text findings are in `docs/`. |
| `*.docx` handoffs (5) | ≈280 KB | Word renderings of handoffs whose `.txt`/`.md` twins are in `docs/handoff/`. |
| `*.sha256` sidecars | tiny | Checksums of excluded archives; superseded by `provenance/assembly_sources.json`. |
| 3D character-builder program (`character3d_masterbuild_v1_4_progress.zip`, release signature, its report) | ≈0.6 MB | A separate product, explicitly scoped out of the ICARUS handoffs by the owner. Its suite also needs `trimesh`/FastAPI, which are not installed. Recommend its own repository. |
| `Executive_Summary_7_UNRELIABLE.json` (OPUS quarantine) | small | The owner's own handoff marks it as ungrounded. |
| `.pytest_cache/`, `__pycache__/`, `build/`, `*.egg-info/`, `.omc/`, `baton-pass` state | — | Caches and agent tooling state. |

The docs collector (`provenance/docs_provenance.json`) also dropped 48 exact-duplicate
documents and 18 loose copies of files already inside `systems/`.

## Large files and Git LFS

Measured commit candidates, applying the `.gitignore` rules: **1,659 files, 9.5 MB**. The largest are
`provenance/file_provenance.json` (461 KB),
`docs/evidence/icarus_repo_workstreams/workstreams/04_OMNIVISION_EXOTIC_RESEARCH/FULL.patch` (427 KB)
and `systems/janus/src/janus_infinity/core.py` (259 KB). Nothing exceeds 1 MB. **Git LFS is not needed.**

Line endings: `.gitattributes` normalises authored text to LF, but exempts corpus-derived documents
(`docs/*/**`, some authored with CRLF) so the SHA-256 values in `provenance/docs_provenance.json` stay
verifiable after commit. Every file under `systems/` is already byte-identical to its
source or git blob, apart from the listed repairs.
If you later want the excluded videos or checkpoint ZIPs under version control, track
them with LFS (`git lfs track "*.mp4" "*.zip" "*.bundle"`) in a separate
`divine-providence-archive` repository, so clones of the source repository stay small.

## Secrets and credentials

Scanned across the whole extracted corpus (3.8 GB) for credential files (`.env*`,
`*.pem`, `*.key`, `*.p12`, `id_rsa*`, `credentials*`) and token patterns (OpenAI,
Anthropic, AWS, GitHub, Slack, Google API keys, PEM private-key blocks, and
key/secret/password/token assignments). Findings:

- No credential files and no real tokens or private keys.
- `seed='9d61b19d…7f60'` in SuperMesh-X tests is the public RFC 8032 Ed25519 test vector.
- `test-openai-secret-never-save` / `test-claude-secret-never-save` are fixtures in excluded Icarus-repo evidence.
- The 3D release signature contains only a public key (and is excluded anyway).

Protection in place: `.gitignore` blocks `.env*` (except `.env.example`), key/cert
formats, `secrets/` and `credentials*.json`. The engine token is read from
`ICARUS_ENGINE_TOKEN` at runtime and never written to the repository. The MCP
registration passes it with `-e` into the user-scope Claude config, which is outside
the repo.
