# Divine Providence — ICARUS master build

The consolidated, validated source of the ICARUS system-of-systems, rebuilt from a
~414 MB corpus of checkpoints, bundles and handoffs (see [PROVENANCE.md](PROVENANCE.md)).
Twelve subsystems keep their own source trees and authority boundaries; a small hub
package verifies the contracts between them and serves everything to Claude Code as
the **`icarus-engine` MCP server**, together with read-only access to the live ICARUS
paper engine.

> BUILT ≠ VERIFIED ≠ READY_TO_COMMIT. Passing tests are engineering evidence only:
> no subsystem here holds trading, promotion or production authority, and
> `execution_authorized=false` / `production_authorized=false` remain the defaults.

## Quick start

```powershell
# Windows
.\scripts\bootstrap.ps1                  # .venv + install + hub tests
.\scripts\bootstrap.ps1 -Validate        # + every subsystem suite, compile checks, adversarial scripts, connections
.\scripts\bootstrap.ps1 -RegisterMcp     # + register icarus-engine with Claude Code (user scope)
```
```sh
scripts/bootstrap.sh --validate --register-mcp   # Linux/macOS
```

Then in Claude Code: `/mcp` shows **icarus-engine**; ask e.g. "list the ICARUS systems",
"check all connections", "show connection coverage", "run the DAEDALUS tests", "what is the engine status?".

The server exposes 18 read/verify-only tools (including `run_tour`). There are 6 verified cross-system connections, and
coverage accounts for all 12 systems: 9 connected, and 3 standalone by design (AEGIS, JANUS,
Infrastructure have no sibling contract in their code). The live-engine tools read the paper
runtime on :8791 and cannot change it.
Set `ICARUS_ENGINE_TOKEN` (see `.env.example`) before registering to enable the engine's research views.

## Layout

| Path | What |
|---|---|
| `systems/<name>/` | One canonical subsystem each, as delivered by its owner (own README, tests, state docs). |
| `src/divine_providence/` | Hub: `registry` (roles/authority), `runner` (isolated processes), `connections` + `drivers/` (cross-system contract checks), `engine` (read-only live-engine client), `mcp_server`, `validate`, `cli` (`dp`). |
| `tests/` | Hub tests, including a real stdio MCP handshake. |
| `docs/` | Architecture, repairs, handoffs, research reports, state capsules, program docs, evidence. |
| `provenance/` | Source archive → file mapping with SHA-256 for every file in `systems/` and `docs/`. |
| `scripts/` | Bootstrap for Windows and POSIX. |

## Subsystems

| System | Version | Role |
|---|---|---|
| `nexus` | 1.15.0 / iter 32 | Causal market-data substrate, sibling-safe instant bundles |
| `daedalus` | NEXUS-integrated receiver | Scientific validation, protected holdouts, promotion authority |
| `aion` | 0.1.0 | Durable evidence memory, hash-linked event ledger |
| `argus` | 0.1.0 | Microstructure / order-flow truth tiers (candle proxies stay non-L2) |
| `athena` | 0.1.0 | Supervisory interpretation, uncertainty, abstention (advisory) |
| `oracle` | Checkpoint C @ `6255339` | Financial & research automation fabric |
| `prometheus` | 0.5 unified | Research/meta-evolution loop; attestation + experiment routing |
| `ascension` | Kit 0.1 / Adapter 0.4 / Evaluator 0.8 | Evaluator, trust, collision, conformance, context distillation |
| `aegis` | Checkpoint 009 | Challenger forge, causal/holdout integrity |
| `janus` | Run 038 | Project-twin temporal truth, proof synchronization |
| `infrastructure` | V49 | Persistence, recovery, locking, authenticated restoration |
| `supermesh_x` | 3.7.0 Cycle 7 FINAL2 | Capability/provider mesh, trusted time, witnessed transparency |

Each subsystem runs in its own interpreter process with only its own import roots
(several ship flat top-level modules), so they never shadow each other.

## Commands

```
dp systems                 # list subsystems
dp test <name>             # run one suite
dp connect [<name>]        # run cross-system connection checks
dp tour                    # end-to-end: one NEXUS instant through every connected system + live engine
dp validate                # full build validation -> provenance/validation_report.json
dp mcp                     # serve icarus-engine over stdio
```

## Further reading

- [docs/research/PROOF_TO_OUTCOME_NETWORK.md](docs/research/PROOF_TO_OUTCOME_NETWORK.md) — research-only economic-event evidence product and CCTP proof-clock lane
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — dependency map, contracts, authority boundaries
- [docs/REPAIRS.md](docs/REPAIRS.md) — every defect found and fixed during consolidation
- [docs/REPO_HYGIENE.md](docs/REPO_HYGIENE.md) — what was excluded from Git and why, LFS guidance, secrets
- [docs/VALIDATION.md](docs/VALIDATION.md) — validation results and open issues
- [PROVENANCE.md](PROVENANCE.md) — canonical source selection per subsystem
