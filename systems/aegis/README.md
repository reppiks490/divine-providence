# AEGIS Challenger Forge — Checkpoint 003

This checkpoint adds the first executable adversarial test harness.

## New executable capabilities
- Standard component adapter contract.
- Prefix-invariance causality auditor.
- Confirmed pivot adapter that emits only when right-side confirmation exists.
- Deliberately leaky/backdated pivot negative control.
- ATR risk adapter.
- DXY macro-pressure adapter with strict timestamp alignment.
- Purged chronological partition planner with untouched final holdout.
- Unit tests proving the causality auditor catches the cheating pivot and accepts the causal pivot.

No component is authorized for live trading.

## Checkpoint 004 additions
- Deterministic academic evidence grader.
- Full fetched records for HMM regime switching, statistical jump-model regimes, partial cointegration, and a broad pairs-trading review.
- Review articles cannot be treated as direct performance evidence.
- Missing OOS or transaction-cost evidence imposes grade caps.

## Checkpoint 005 additions
- Expanded NQ continuous research corpus across five quarterly contracts and four volume-based rolls.
- First real component competition on development data only.
- Both incumbent liquidity sweep and VWAP/volume challenger were quarantined.
- Challenger showed strong training performance but negative validation performance, a concrete overfit/fragility warning.
- Added event-time validation and cost/latency shadow-execution harness.

## Checkpoint 006 correction
Checkpoint 005 exposed a prefix-replay bug: aligned metadata (for example session IDs) was not sliced with price-series prefixes. This could invalidate causality audits for session-aware components. The prefix engine now slices bar-aligned metadata, a regression test was added, and the full suite was rerun. Checkpoint 005 is not considered verified.

## Checkpoint 007 additions
- Full 6,314-row NQ continuous payload identity completed.
- Payload SHA-256: `cf63ce4c0f4556308429cff037dc38fab60610f469f4e95197b04eb93516a7df`
- Manifest SHA-256: `e4b6f65a2ef43c474de94fbc7abb69ebd9b2c8808d4cf8bdad3f8966863ded3a`
- Four purged rolling validation folds completed; final 1,263-row holdout remains untouched.
- Neither liquidity candidate shows stable positive validation evidence.
- Added bootstrap uncertainty, sign-flip testing, multiple-testing ledger, causal volatility-regime adapter, and causal KNN-distance OOD abstention adapter.

## Checkpoint 008 additions
- Regime-conditioned NQ validation and session-block uncertainty testing.
- NORMAL-volatility incumbent pocket explicitly rejected as a specialist: 3/4 positive folds was insufficient because its CI crosses zero and adjusted p=1.0.
- Deterministic randomized-direction negative controls and tournament decision gates.
- Partial-fill/latency stress ladder.
- Executable PIT factor/correlation adapter.
- Four BTC MASTER components moved from formal specs into causal executable adapters.

### Verification correction
The verification gate caught two assembly defects before promotion: a concatenated import and missing recursive slicing for nested bar-aligned metadata. Both were fixed; the complete suite passes 31/31.

## Checkpoint 009 additions
- NQ PIT QQQ factor binding: 60.70% exact prior-hour coverage, correlation ~0.0301; retained only as context.
- NQ real KNN OOD: 1.28% overall abstention, 5.81% in HIGH volatility; retained as shadow guard.
- BTCUSD expanded to 23,976 clean 1h bars. Payload SHA-256 `fc7d0c2a37ba48f8dc9e912cf1b90d5d738d5905bfd5ba982f6eb74f8b6ed417`; 4,796-row holdout untouched.
- BTC MASTER directional uses tested on four fixed folds; all negative in every fold and quarantined.
- Added horizon disagreement abstention, circular-evidence/double-count firewall, and reversible tombstone ledger.
