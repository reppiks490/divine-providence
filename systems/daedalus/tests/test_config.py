import pytest
from daedalus.config import ValidationConfig, DiscoveryConfig, FeatureConfig


def test_invalid_probability_threshold_rejected():
    with pytest.raises(ValueError):
        ValidationConfig(probability_threshold=0.5)


def test_invalid_fdr_alpha_rejected():
    with pytest.raises(ValueError):
        DiscoveryConfig(fdr_alpha=0.0)


def test_invalid_feature_coverage_rejected():
    with pytest.raises(ValueError):
        FeatureConfig(min_row_feature_coverage=0.0)
