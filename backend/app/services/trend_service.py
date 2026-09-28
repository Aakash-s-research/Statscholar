"""
Trend Analysis — Mann-Kendall family.

StatScholar's flagship module. All six tests are implemented here:
Mann-Kendall, Sen's Slope, Modified Mann-Kendall (Hamed & Rao correction),
Pre-Whitening, Trend-Free Pre-Whitening, and Seasonal Mann-Kendall.

References:
  Mann, H.B. (1945); Kendall, M.G. (1975)
  Sen, P.K. (1968) — slope estimator
  Hamed, K.H. & Rao, A.R. (1998) — modified variance for autocorrelated data
  von Storch, H. (1995) — pre-whitening
  Yue, S. et al. (2002) — trend-free pre-whitening
  Hirsch, R.M., Slack, J.R. & Smith, R.A. (1982) — seasonal Kendall test
"""
from itertools import combinations

import numpy as np
from scipy import stats


def mann_kendall(values: np.ndarray, alpha: float = 0.05) -> dict:
    """
    Classic Mann-Kendall trend test.

    Returns S, Z, p_value, tau, and n. Does not correct for
    autocorrelation — call `lag1_autocorrelation` separately and prefer
    Modified MK / TFPW when autocorrelation is present.
    """
    n = len(values)
    s = sum(
        np.sign(values[j] - values[i])
        for i, j in combinations(range(n), 2)
    )

    unique, counts = np.unique(values, return_counts=True)
    tie_term = np.sum(counts * (counts - 1) * (2 * counts + 5))
    var_s = (n * (n - 1) * (2 * n + 5) - tie_term) / 18

    if s > 0:
        z = (s - 1) / np.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / np.sqrt(var_s)
    else:
        z = 0.0

    p_value = 2 * (1 - stats.norm.cdf(abs(z)))
    tau = s / (0.5 * n * (n - 1))

    return {
        "S": int(s),
        "Z": round(float(z), 3),
        "p_value": round(float(p_value), 4),
        "tau": round(float(tau), 3),
        "n": n,
        "alpha": alpha,
        "significant": bool(p_value < alpha),
        "direction": "increasing" if z > 0 else "decreasing" if z < 0 else "none",
    }


def sens_slope(time: np.ndarray, values: np.ndarray, confidence: float = 0.95) -> dict:
    """
    Sen's slope estimator — median of all pairwise slopes. Report this
    alongside Mann-Kendall: MK answers "is there a trend", this answers
    "how big is it".
    """
    n = len(values)
    slopes = [
        (values[j] - values[i]) / (time[j] - time[i])
        for i, j in combinations(range(n), 2)
        if time[j] != time[i]
    ]
    slopes = np.sort(slopes)
    q_med = float(np.median(slopes))

    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    var_s = (n * (n - 1) * (2 * n + 5)) / 18
    c_alpha = z * np.sqrt(var_s)
    m1 = int((len(slopes) - c_alpha) / 2)
    m2 = int((len(slopes) + c_alpha) / 2) + 1

    return {
        "slope": round(q_med, 3),
        "ci_lower": round(float(slopes[max(m1, 0)]), 3),
        "ci_upper": round(float(slopes[min(m2, len(slopes) - 1)]), 3),
        "confidence": confidence,
    }


def lag1_autocorrelation(values: np.ndarray) -> dict:
    """
    Lag-1 autocorrelation check, used to decide whether standard MK is
    safe to use as-is or whether Modified MK / pre-whitening is needed.
    Critical value approximated at 1.96/sqrt(n) (standard large-sample rule).
    """
    n = len(values)
    r1 = float(np.corrcoef(values[:-1], values[1:])[0, 1])
    critical = 1.96 / np.sqrt(n)
    return {
        "r1": round(r1, 3),
        "critical_value": round(float(critical), 3),
        "significant_autocorrelation": bool(abs(r1) > critical),
    }


def _s_and_var(values: np.ndarray) -> tuple[int, float]:
    """Shared S statistic + tie-adjusted variance, factored out so
    Seasonal Mann-Kendall can sum these per-season without duplicating
    the pairwise-comparison logic in `mann_kendall`."""
    n = len(values)
    s = sum(np.sign(values[j] - values[i]) for i, j in combinations(range(n), 2))
    unique, counts = np.unique(values, return_counts=True)
    tie_term = np.sum(counts * (counts - 1) * (2 * counts + 5))
    var_s = (n * (n - 1) * (2 * n + 5) - tie_term) / 18
    return int(s), float(var_s)


def _z_and_p(s: float, var_s: float) -> tuple[float, float]:
    if var_s <= 0:
        return 0.0, 1.0
    if s > 0:
        z = (s - 1) / np.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / np.sqrt(var_s)
    else:
        z = 0.0
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    return float(z), float(p)


def modified_mann_kendall(values: np.ndarray, alpha: float = 0.05) -> dict:
    """
    Modified Mann-Kendall (Hamed & Rao, 1998).

    Corrects the MK variance for autocorrelation by: detrending with
    Sen's slope, ranking the residuals, computing their autocorrelation
    at each lag, and inflating the variance by an amount proportional to
    the *significant* lag correlations only (insignificant ones are
    treated as zero, per the original method — including sampling noise
    would over-correct).
    """
    n = len(values)
    time = np.arange(n)
    slope = sens_slope(time, values)["slope"]
    detrended = values - slope * time
    ranks = stats.rankdata(detrended)
    r_bar = ranks.mean()

    correction_sum = 0.0
    for k in range(1, n - 1):
        num = np.sum((ranks[: n - k] - r_bar) * (ranks[k:] - r_bar))
        den = np.sum((ranks - r_bar) ** 2)
        rho_k = num / den if den > 0 else 0.0
        # 95% CI for autocorrelation of ranks under the null (Hamed & Rao, eq. 6)
        ci = (-1 + 1.96 * np.sqrt(n - k - 1)) / (n - k) if n - k - 1 > 0 else 0.0
        if abs(rho_k) > abs(ci):
            correction_sum += (n - k) * (n - k - 1) * (n - k - 2) * rho_k

    correction_factor = 1 + (2 / (n * (n - 1) * (n - 2))) * correction_sum
    correction_factor = max(correction_factor, 1e-6)  # guard against pathological inputs

    s, var_s = _s_and_var(values)
    var_s_corrected = var_s * correction_factor
    z, p_value = _z_and_p(s, var_s_corrected)
    tau = s / (0.5 * n * (n - 1))

    return {
        "S": s,
        "Z": round(z, 3),
        "p_value": round(p_value, 4),
        "tau": round(tau, 3),
        "n": n,
        "alpha": alpha,
        "significant": bool(p_value < alpha),
        "direction": "increasing" if z > 0 else "decreasing" if z < 0 else "none",
        "correction_factor": round(correction_factor, 3),
        "effective_n": round(n / correction_factor, 1),
    }


def pre_whitening(values: np.ndarray, alpha: float = 0.05) -> dict:
    """
    Pre-Whitening (von Storch, 1995).

    Removes lag-1 autocorrelation before testing: y_i = x_{i+1} - r1*x_i.
    Known limitation this method doesn't correct for — pre-whitening the
    raw series also removes part of a genuine trend along with the
    autocorrelation, biasing toward *under*-detecting real trends. TFPW
    (below) exists specifically to fix that; prefer it over this when
    a trend might be genuinely present alongside autocorrelation.
    """
    n = len(values)
    r1 = float(np.corrcoef(values[:-1], values[1:])[0, 1])
    critical = 1.96 / np.sqrt(n)
    applied = bool(abs(r1) > critical)

    series = values[1:] - r1 * values[:-1] if applied else values
    result = mann_kendall(series, alpha=alpha)
    result["r1"] = round(r1, 3)
    result["critical_value"] = round(float(critical), 3)
    result["pre_whitening_applied"] = applied
    return result


def trend_free_pre_whitening(time: np.ndarray, values: np.ndarray, alpha: float = 0.05) -> dict:
    """
    Trend-Free Pre-Whitening (Yue et al., 2002).

    Fixes pre-whitening's trend-removal bias by detrending with Sen's
    slope *before* checking/removing autocorrelation, then adding the
    trend back before running Mann-Kendall — so the genuine trend
    survives the whitening step.
    """
    n = len(values)
    t = time - time[0]
    slope = sens_slope(time, values)["slope"]
    detrended = values - slope * t

    r1 = float(np.corrcoef(detrended[:-1], detrended[1:])[0, 1])
    critical = 1.96 / np.sqrt(n)
    applied = bool(abs(r1) > critical)

    if applied:
        whitened = detrended[1:] - r1 * detrended[:-1]
        reconstructed = whitened + slope * t[1:]
    else:
        reconstructed = values

    result = mann_kendall(reconstructed, alpha=alpha)
    result["r1_detrended"] = round(r1, 3)
    result["critical_value"] = round(float(critical), 3)
    result["pre_whitening_applied"] = applied
    result["sen_slope_used"] = round(slope, 3)
    return result


def seasonal_mann_kendall(values: np.ndarray, season_ids: np.ndarray, alpha: float = 0.05) -> dict:
    """
    Seasonal Mann-Kendall (Hirsch, Slack & Smith, 1982).

    Runs MK independently within each season (comparing only same-season
    values across years, so a trend can't be masked or exaggerated by
    seasonal swings), then sums S and its variance across seasons —
    assuming independence between seasons, which is the standard basic
    version of this test.

    Also runs the formal Van Belle & Hughes (1984) chi-square test for
    homogeneity of trend across seasons: it decomposes the sum of squared
    per-season Z scores into a combined-trend component and a leftover
    heterogeneity component (df = n_seasons - 1). A significant result
    means the trend direction/magnitude genuinely differs across seasons,
    so the single combined trend shouldn't be read as applying uniformly.
    """
    seasons = np.unique(season_ids)
    if len(seasons) < 2:
        raise ValueError("Seasonal Mann-Kendall needs at least 2 distinct seasons")

    total_s, total_var = 0, 0.0
    per_season = {}
    z_uncorrected = []  # for the homogeneity decomposition (no continuity correction)
    for season in seasons:
        season_values = values[season_ids == season]
        if len(season_values) < 4:
            continue  # too few points in this season to contribute meaningfully
        s, var_s = _s_and_var(season_values)
        total_s += s
        total_var += var_s
        z_season, _ = _z_and_p(s, var_s)  # continuity-corrected, for display
        z_raw = s / np.sqrt(var_s) if var_s > 0 else 0.0  # uncorrected, for the chi-square decomposition
        z_uncorrected.append(z_raw)
        per_season[str(season)] = {"S": s, "Z": round(z_season, 3), "n": len(season_values)}

    z, p_value = _z_and_p(total_s, total_var)
    n_pairs = sum(len(values[season_ids == s]) for s in seasons)
    tau = total_s / (0.5 * n_pairs * (n_pairs - 1)) if n_pairs > 1 else 0.0
    overall_direction = "increasing" if z > 0 else "decreasing" if z < 0 else "none"

    # Van Belle & Hughes (1984) homogeneity of trend chi-square test.
    k = len(z_uncorrected)
    if k >= 2:
        chi2_homog = float(sum(zi ** 2 for zi in z_uncorrected) - (sum(z_uncorrected) ** 2) / k)
        df_homog = k - 1
        p_homog = float(1 - stats.chi2.cdf(chi2_homog, df_homog)) if df_homog > 0 else 1.0
    else:
        chi2_homog, df_homog, p_homog = 0.0, 0, 1.0
    homogeneous = bool(p_homog >= alpha)

    # Simple readable summary of which seasons disagree in direction —
    # kept alongside the formal test since it's easier to act on in an
    # interpretation sentence than a chi-square statistic alone.
    disagreeing = [
        s for s, v in per_season.items()
        if (v["Z"] > 0 and overall_direction == "decreasing")
        or (v["Z"] < 0 and overall_direction == "increasing")
    ]

    return {
        "S": total_s,
        "Z": round(z, 3),
        "p_value": round(p_value, 4),
        "tau": round(tau, 3),
        "n": len(values),
        "n_seasons": len(seasons),
        "alpha": alpha,
        "significant": bool(p_value < alpha),
        "direction": overall_direction,
        "per_season": per_season,
        "homogeneity_chi2": round(chi2_homog, 3),
        "homogeneity_df": df_homog,
        "homogeneity_p": round(p_homog, 4),
        "homogeneous": homogeneous,
        "disagreeing_seasons": disagreeing,
    }
