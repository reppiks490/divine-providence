# HANDOFF TO CHATGPT WORK / REPO

## What this is
`daedalus-research-os` is a standalone research sibling for Icarus. It catalogs heterogeneous chart representations, generates causal features, performs hypothesis discovery, compares and freezes model ensembles on development evidence, budgets protected holdout exposure, attacks frozen predictions adversarially, records experiment memory, and exports only research candidates that satisfy local plus corpus-level gates.

It is **not** a replacement for Icarus and must not be inserted into the live execution path.

## Preferred repo placement

```text
<workspace-or-org-root>/
  Icarus/                    # existing system; leave untouched
  Icarus-engine/             # existing repo; leave untouched
  multi-level-csv/           # authoritative data repo/archive
  daedalus-research-os/      # THIS PACKAGE (new sibling repository)
```

Second-best, only if a sibling repo cannot be created:

```text
Icarus/research/daedalus/
```

Keep it excluded from production imports/execution until a separate Icarus integration review approves a bridge contract.

## Dataset placement
Do not move, rename, or collapse the 800+ CSV corpus for DAEDALUS. Point commands at the authoritative repo root. The scanner is recursive. Same-symbol/similar-suffix files remain distinct unless their bytes are exactly identical; even exact duplicates remain separate catalog records and only share compute.

## First commands Work should run

```bash
cd daedalus-research-os
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .
pytest -q
python scripts/audit.py

daedalus catalog /ABSOLUTE/PATH/TO/AUTHORITATIVE/CSV/ROOT --output artifacts/catalog.csv
```

**Stop if the catalog does not show the expected 800+ real CSVs.** Fix the root/path/mount before corpus research. The `Full csv candles only.zip` visible to this chat is only a subset: 238 real CSVs plus 238 macOS `._` metadata entries.

## Recommended staged run

```bash
# 1) identity review scaffold
daedalus identity-scaffold /ABSOLUTE/PATH/TO/AUTHORITATIVE/CSV/ROOT --output config/source_identity.csv

# 2) development-only pilot; resumable; spends zero protected tails
daedalus batch /ABSOLUTE/PATH/TO/AUTHORITATIVE/CSV/ROOT --project-root . --limit 20

# 3) inspect experiment memory
daedalus meta --registry artifacts/experiments.sqlite3

# 4) only after the pilot is clean, run the two-phase protected protocol
daedalus research-corpus /ABSOLUTE/PATH/TO/AUTHORITATIVE/CSV/ROOT --project-root . --limit 20
```

Increase the limit gradually. Remove it only after representative chart classes and identity mappings are understood.

## Alternate chart constructions
If a representation's OHLC values are synthetic/non-executable, do **not** use them as PnL. Use `research-fusion` with one explicitly execution-safe stream and one or more representation sources. Fusion aligns predictors strictly backward in time and does not allow exact-time matches.

## What Work must not do
- Do not merge same-symbol files based on filename suffixes.
- Do not infer chart type solely from `1`, `1S`, `2`, etc.
- Do not delete repeated timestamps; some constructions can legitimately share them.
- Do not silently sort a source whose timestamps move backward.
- Do not use `batch` as a protected-validation command; it is deliberately development-only.
- Do not repeatedly call `research` on the same source with changed protocol/config and then treat the tail as pristine.
- Do not connect `bridge.py` to live execution.
- Do not weaken gates merely to increase the number of passing candidates.

## Protected-holdout protocol v3
Development data freezes feature discovery, interaction discovery, regime thresholds, model-family comparison, ensemble membership/weights, and feature-ablation diagnostics. Corpus research then spends only a diversity-limited holdout budget. The selected frozen ensembles face predeclared holdout diagnostics, and the ledger records exposure before evaluation. Global FDR is applied after all selected protected tests complete.

If the protocol/configuration changes after a source tail has been exposed, the same tail is no longer pristine for the changed design. Under strict ledger mode DAEDALUS blocks reuse rather than silently accepting it.

## Promotion contract
A DAEDALUS candidate manifest is research-only. `production_authorized` is always false. Production integration requires an explicit, separate Icarus review and forward/shadow evidence appropriate to the intended use.

## Where outputs go

```text
artifacts/catalog.csv                    # source inventory
artifacts/runs/                          # per-source development/final reports
artifacts/experiments.sqlite3            # experiment memory / graveyard
artifacts/holdout_ledger.sqlite3         # protected-tail exposure history
artifacts/corpus_research_summary.json   # corpus two-phase result
artifacts/candidates/                    # globally eligible research manifests only
artifacts/shadow.sqlite3                 # forward/shadow observation book
config/source_identity.csv               # explicit identity decisions/review scaffold
```

## Validation completed before handoff
The package has unit/integration coverage for catalog integrity, repeated timestamp preservation, causal feature lagging, purge geometry, development-only screening, batch resumability, holdout budgeting, ensemble freezing, protected ledger behavior, adversarial tests, regime-conditioned diagnostics, fusion alignment, FDR, promotion, registry, shadow book, and corpus orchestration. It was also smoke-tested on real files from the accessible subset. Work should rerun the same test/audit suite after placing it beside the authoritative repos.
