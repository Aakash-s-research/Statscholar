"""
Regression — Simple Linear Regression (v1 scope).
"""
import numpy as np
from scipy import stats


def simple_linear_regression(x: np.ndarray, y: np.ndarray) -> dict:
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    n = len(x)
    y_pred = intercept + slope * x
    residuals = y - y_pred

    r_squared = r_value ** 2
    df_resid = n - 2
    f_statistic = (r_squared / 1) / ((1 - r_squared) / df_resid) if df_resid > 0 else float("nan")

    return {
        "intercept": round(float(intercept), 3),
        "slope": round(float(slope), 3),
        "r_squared": round(float(r_squared), 3),
        "f_statistic": round(float(f_statistic), 3),
        "p_value": round(float(p_value), 4),
        "std_err": round(float(std_err), 3),
        "residuals": residuals.tolist(),
    }


def check_assumptions(residuals: np.ndarray, y_pred: np.ndarray) -> dict:
    normality_p = stats.shapiro(residuals).pvalue
    homoscedasticity_p = stats.spearmanr(np.abs(residuals), y_pred).pvalue

    flags = []
    if normality_p < 0.05:
        flags.append(
            "The residuals did not pass the normality check, which can affect the "
            "reliability of significance tests — consider a transformation of the outcome variable."
        )
    if homoscedasticity_p < 0.05:
        flags.append(
            "The spread of residuals was uneven across predicted values (heteroscedasticity "
            "detected), which may make the standard errors unreliable."
        )
    return {
        "normality_p": round(float(normality_p), 4),
        "homoscedasticity_p": round(float(homoscedasticity_p), 4),
        "flags": flags,
    }
