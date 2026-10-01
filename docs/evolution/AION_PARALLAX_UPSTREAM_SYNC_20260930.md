# AION / PARALLAX upstream synchronization — 2026-09-30

Source repository: `reppiks490/aion-parallax-research`
Source revision: `7b99df66f08ddbe50b0c30148fe7acadfbfa4b57`
Target branch: `sol/subsystem-evolution-20260930`

This synchronization imports the current AION/PARALLAX source and research-boundary
changes that differ from the consolidated `systems/aion` tree. It includes
prediction-v2 frozen evidence cutoffs, retrospective-replay labeling, unverified
outcome handling, the ZIP-native PARALLAX inventory, the reconciled 659-member /
542-byte-content corpus checkpoint, and the current regression tests.

The satellite workflow file is intentionally not copied into the nested subsystem:
GitHub only executes workflows at the repository-root `.github/workflows`; the
monorepo receives its own root-level subsystem CI separately.

No ICARUS execution-engine, asset, timeframe, chart, sub-minute, broker, or
order-routing code is changed.

The historical source-selection record in `PROVENANCE.md` remains intact. This
receipt records the post-consolidation upstream revision so lineage remains explicit.
