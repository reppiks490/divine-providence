import pytest

from daedalus.config import ShadowConfig
from daedalus.shadow import ShadowBook


def _manifest(auc=0.70, brier=0.18):
    return {
        'protected_holdout': {
            'metrics': {
                'auc': auc,
                'brier': brier,
                'brier_improvement': 0.03,
                'max_drawdown': 0.10,
                'profit_factor': 1.3,
                'trade_count': 50,
            }
        }
    }


def test_shadow_summary_uses_only_matured_forward_observations(tmp_path):
    book = ShadowBook(tmp_path / 'shadow.sqlite3')
    book.register('c1', _manifest())
    a = book.record_prediction('c1', 0.8, 1.0)
    b = book.record_prediction('c1', 0.2, 2.0)
    book.record_prediction('c1', 0.9, 3.0)  # remains immature
    book.mature('c1', a, 1.0, 0.02)
    book.mature('c1', b, 2.0, -0.01)
    s = book.summary('c1', threshold=.55, round_trip_cost_bps=1.0)
    assert s['mature_observations'] == 2
    assert s['signal_count'] == 2
    assert s['auc'] == 1.0
    assert s['signal_hit_rate'] == 1.0
    assert s['cumulative_log_return_repriced'] > 0
    assert len(s['calibration_bins']) >= 1


def test_shadow_candidate_manifest_is_immutable(tmp_path):
    book = ShadowBook(tmp_path / 'shadow.sqlite3')
    book.register('c1', {'x': 1})
    book.register('c1', {'x': 1})  # exact retry is idempotent
    with pytest.raises(ValueError):
        book.register('c1', {'x': 2})


def test_shadow_repeated_source_time_is_preserved_and_backward_time_is_rejected(tmp_path):
    book = ShadowBook(tmp_path / 'shadow.sqlite3')
    book.register('c1', {'x': 1})
    p1 = book.record_prediction('c1', 0.6, 10.0, source_key='bar-a')
    p2 = book.record_prediction('c1', 0.7, 10.0, source_key='bar-b')
    assert p1 != p2
    with pytest.raises(ValueError):
        book.record_prediction('c1', 0.7, 9.0)


def test_shadow_outcome_is_append_once_and_conflicts_are_rejected(tmp_path):
    book = ShadowBook(tmp_path / 'shadow.sqlite3')
    book.register('c1', {'x': 1})
    pid = book.record_prediction('c1', 0.7, 1.0)
    book.settle_prediction(pid, 0.01, target_source_time=2.0, metadata={'feed': 'x'})
    # Exact retry is safe/idempotent.
    book.settle_prediction(pid, 0.01, target_source_time=2.0, metadata={'feed': 'x'})
    with pytest.raises(ValueError):
        book.settle_prediction(pid, -0.01, target_source_time=2.0, metadata={'feed': 'x'})


def test_shadow_health_warms_then_detects_degradation(tmp_path):
    book = ShadowBook(tmp_path / 'shadow.sqlite3')
    book.register('c1', _manifest(auc=0.80, brier=0.12))
    cfg = ShadowConfig(
        min_mature_observations=20,
        recent_window=20,
        calibration_bins=5,
        min_signal_count=5,
        max_auc_drop_vs_reference=0.05,
        max_brier_degradation_vs_reference=0.05,
        max_expected_calibration_error=0.20,
        max_probability_ks_drift=0.50,
        max_recent_auc_drop=0.10,
        max_recent_brier_degradation=0.10,
        max_drawdown=0.50,
        min_directional_posterior_lower=0.20,
        watch_failures=1,
        degraded_failures=2,
    )
    # First observation => warming.
    pid = book.record_prediction('c1', 0.9, 1.0)
    book.settle_prediction(pid, -0.01)
    assert book.health('c1', cfg).recommended_status == 'SHADOW_WARMING'

    # Strongly inverted predictions produce multiple failures versus the reference.
    for i in range(2, 31):
        up = i % 2 == 0
        prob = 0.9 if up else 0.1
        realized = -0.01 if up else 0.01
        pid = book.record_prediction('c1', prob, float(i))
        book.settle_prediction(pid, realized)
    h = book.health('c1', cfg)
    assert h.recommended_status == 'SHADOW_DEGRADED'
    assert 'auc_degraded_vs_protected_reference' in h.failures
    assert len(h.failures) >= 2


def test_apply_health_status_creates_auditable_event(tmp_path):
    book = ShadowBook(tmp_path / 'shadow.sqlite3')
    book.register('c1', _manifest())
    cfg = ShadowConfig(min_mature_observations=5, recent_window=5, min_signal_count=2)
    h = book.apply_health_status('c1', cfg)
    assert h.recommended_status == 'SHADOW_WARMING'
    assert book.candidate('c1')['status'] == 'SHADOW_WARMING'
    history = book.status_history('c1')
    assert history[-1]['to_status'] == 'SHADOW_WARMING'
