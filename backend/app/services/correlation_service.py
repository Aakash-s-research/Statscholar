"""
Correlation — Pearson, Spearman, Kendall Tau.
"""
import numpy as np
from scipy import stats


def recommend_method(x: np.ndarray, y: np.ndarray) -> str:
    x_normal = stats.shapiro(x).pvalue > 0.05
    y_normal = stats.shapiro(y).pvalue > 0.05
    if x_normal and y_normal:
        return "pearson"
    if len(x) < 20:
        return "kendall"
    return "spearman"


def compute_correlation(x: np.ndarray, y: np.ndarray, method: str) -> dict:
    fn = {
        "pearson": stats.pearsonr,
        "spearman": stats.spearmanr,
        "kendall": stats.kendalltau,
    }[method]
    r, p_value = fn(x, y)
    return {"r": float(r), "p_value": float(p_value), "method": method}


def correlation_matrix(df, columns, method: str):
    return df[columns].corr(method=method).round(3).values.tolist()
