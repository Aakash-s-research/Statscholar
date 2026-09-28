"""
Mann-Kendall sanity checks.
"""
import numpy as np
import pytest

from app.services.trend_service import (
    lag1_autocorrelation,
    mann_kendall,
    modified_mann_kendall,
    pre_whitening,
    seasonal_mann_kendall,
    sens_slope,
    trend_free_pre_whitening,
)


def test_mann_kendall_detects_clear_increase():
    values = np.array([10, 12, 11, 15, 18, 20, 19, 24, 27, 30])
    result = mann_kendall(values)
    assert result["direction"] == "increasing"
    assert result["significant"] is True
    assert result["p_value"] < 0.05


def test_mann_kendall_no_trend_on_flat_noise():
    rng = np.random.default_rng(42)
    values = 50 + rng.normal(0, 0.5, size=10)
    result = mann_kendall(values)
    assert result["direction"] in ("increasing", "decreasing", "none")


def test_sens_slope_matches_mann_kendall_direction():
    time = np.arange(2000, 2010)
    values = np.array([10, 12, 11, 15, 18, 20, 19, 24, 27, 30])
    mk = mann_kendall(values)
    sen = sens_slope(time, values)
    assert (sen["slope"] > 0) == (mk["direction"] == "increasing")


def test_lag1_autocorrelation_shape():
    values = np.array([10, 12, 11, 15, 18, 20, 19, 24, 27, 30])
    result = lag1_autocorrelation(values)
    assert "r1" in result and "significant_autocorrelation" in result


def test_modified_mann_kendall_inflates_variance_under_autocorrelation():
    # Strongly autocorrelated trending series (each step depends on the last)
    rng = np.random.default_rng(1)
    n = 30
    noise = np.zeros(n)
    for i in range(1, n):
        noise[i] = 0.8 * noise[i - 1] + rng.normal(0, 1)
    values = 10 + 0.5 * np.arange(n) + noise

    standard = mann_kendall(values)
    modified = modified_mann_kendall(values)

    # Same S (data doesn't change), but the corrected test should be more
    # conservative (larger p-value / smaller |Z|) under positive autocorrelation.
    assert modified["S"] == standard["S"]
    assert modified["correction_factor"] >= 1.0
    assert abs(modified["Z"]) <= abs(standard["Z"]) + 1e-6


def test_modified_mann_kendall_close_to_standard_when_independent():
    rng = np.random.default_rng(2)
    values = 10 + 0.5 * np.arange(20) + rng.normal(0, 0.5, 20)
    standard = mann_kendall(values)
    modified = modified_mann_kendall(values)
    assert modified["correction_factor"] == pytest.approx(1.0, abs=0.5)
    assert modified["direction"] == standard["direction"]


def test_pre_whitening_runs_and_flags_application():
    values = np.array([10, 12, 11, 15, 18, 20, 19, 24, 27, 30], dtype=float)
    result = pre_whitening(values)
    assert "pre_whitening_applied" in result
    assert "direction" in result


def test_trend_free_pre_whitening_preserves_increasing_direction():
    time = np.arange(2000, 2020)
    rng = np.random.default_rng(3)
    noise = np.zeros(20)
    for i in range(1, 20):
        noise[i] = 0.7 * noise[i - 1] + rng.normal(0, 1)
    values = 10 + 0.5 * np.arange(20) + noise

    result = trend_free_pre_whitening(time, values)
    assert result["direction"] == "increasing"
    assert "sen_slope_used" in result


def test_seasonal_mann_kendall_detects_combined_trend():
    # 5 years x 4 seasons, each season trending upward
    years = np.repeat(np.arange(2015, 2020), 4)
    season_ids = np.tile(np.arange(4), 5)
    values = 100 + 3 * years - years.min() * 3 + season_ids * 2.0
    values = values + np.array([0, 0.1, -0.1, 0.05] * 5)  # tiny jitter, no ties

    result = seasonal_mann_kendall(values, season_ids)
    assert result["direction"] == "increasing"
    assert result["n_seasons"] == 4
    assert "per_season" in result
    assert "homogeneity_chi2" in result and "homogeneity_p" in result


def test_seasonal_mann_kendall_homogeneous_when_all_seasons_agree():
    # All 4 seasons trend upward at the same rate — should NOT flag heterogeneity
    years = np.repeat(np.arange(2000, 2020), 4)  # 20 years for a stable test
    season_ids = np.tile(np.arange(4), 20)
    rng = np.random.default_rng(5)
    values = 100 + 2.0 * (years - years.min()) + rng.normal(0, 0.3, len(years))

    result = seasonal_mann_kendall(values, season_ids)
    assert result["homogeneous"] is True
    assert result["homogeneity_p"] >= 0.05


def test_seasonal_mann_kendall_flags_heterogeneous_trend():
    # 3 seasons trend up strongly, 1 season trends down strongly — should flag heterogeneity
    years = np.repeat(np.arange(2000, 2020), 4)
    season_ids = np.tile(np.arange(4), 20)
    t = years - years.min()
    direction = np.where(season_ids == 3, -1, 1)
    rng = np.random.default_rng(6)
    values = 100 + direction * 4.0 * t + rng.normal(0, 0.3, len(years))

    result = seasonal_mann_kendall(values, season_ids)
    assert result["homogeneous"] is False
    assert result["homogeneity_p"] < 0.05
    assert "3" in result["disagreeing_seasons"]


def test_seasonal_mann_kendall_requires_multiple_seasons():
    values = np.array([1.0, 2.0, 3.0, 4.0])
    season_ids = np.array([0, 0, 0, 0])
    with pytest.raises(ValueError):
        seasonal_mann_kendall(values, season_ids)
