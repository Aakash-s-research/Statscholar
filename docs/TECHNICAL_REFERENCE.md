# StatScholar Technical Reference

This document describes the backend API and the statistical methods behind
each module. Intended for anyone extending the codebase, writing about the
software (e.g. in a thesis methods section), or preparing IP/copyright
documentation.

## Architecture

- **Backend**: FastAPI (Python), stateless per-request except for an
  in-memory dataset store keyed by a UUID returned at upload time.
- **Frontend**: React + Vite, communicating with the backend over a REST
  API proxied through `/api/*` in development.
- **Statistical libraries**: pandas, numpy, scipy, statsmodels — but the
  Mann-Kendall family and the interpretation engine are original
  implementations, not wrappers around an existing trend-test package.

## Statistical methods and their references

| Method | Reference | Implemented in |
|---|---|---|
| Mann-Kendall trend test | Mann (1945); Kendall (1975) | `trend_service.mann_kendall` |
| Sen's Slope estimator | Sen (1968) | `trend_service.sens_slope` |
| Modified Mann-Kendall | Hamed & Rao (1998) | `trend_service.modified_mann_kendall` |
| Pre-Whitening | von Storch (1995) | `trend_service.pre_whitening` |
| Trend-Free Pre-Whitening | Yue et al. (2002) | `trend_service.trend_free_pre_whitening` |
| Seasonal Mann-Kendall | Hirsch, Slack & Smith (1982) | `trend_service.seasonal_mann_kendall` |
| Homogeneity of trend (chi-square) | Van Belle & Hughes (1984) | `trend_service.seasonal_mann_kendall` |
| Pearson / Spearman / Kendall correlation | Standard | `correlation_service.compute_correlation` |
| Simple linear regression (OLS) | Standard | `regression_service.simple_linear_regression` |
| Shapiro-Wilk normality test | Shapiro & Wilk (1965) | used in descriptive stats + regression diagnostics |

### Modified Mann-Kendall — implementation notes
Detrends the series with Sen's slope, ranks the residuals, computes their
autocorrelation at each lag, and inflates the Mann-Kendall variance in
proportion to only the *statistically significant* lag correlations
(insignificant ones are treated as zero, per the original method — this
prevents over-correcting from sampling noise).

### Trend-Free Pre-Whitening — implementation notes
Detrends with Sen's slope before checking for autocorrelation (unlike
plain Pre-Whitening, which whitens the raw series and can remove part of
a genuine trend along with the autocorrelation). If significant lag-1
autocorrelation remains in the detrended series, it's removed, and the
trend is added back before running Mann-Kendall on the reconstructed series.

### Seasonal Mann-Kendall homogeneity test — implementation notes
Decomposes the sum of squared per-season Z-scores into a combined-trend
component and a residual heterogeneity component:

```
χ² = Σ(Zᵢ²) − (ΣZᵢ)² / k        df = k − 1
```

where `Zᵢ` is season *i*'s own (uncorrected) Z statistic and `k` is the
number of seasons. A significant result means the trend genuinely differs
in direction or magnitude across seasons, so the single combined trend
shouldn't be interpreted as applying uniformly through the year. This is
the standard basic form of the test, which assumes independence between
seasons — a covariance-aware version is a documented non-goal for v1
(see the main README).

## Automated Interpretation engine

Deliberately rule-based rather than LLM-based (`app/services/interpretation_engine.py`).
Each statistical result is passed through a function that returns:

```python
{"student_text": str, "research_text": str, "flags": list[str]}
```

This design choice was made for three reasons: reproducibility (the same
input always produces the same output), zero marginal cost per interpretation,
and — relevant if pursuing copyright registration — the wording is original
authored logic rather than model-generated text, which is a more
straightforward basis for claiming authorship than an LLM wrapper would be.

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/data/upload` | Upload a CSV/XLSX/TSV, returns column types + quality score |
| GET | `/data/{id}` | Re-fetch a dataset's summary |
| GET | `/data/{id}/series?columns=a,b` | Raw column values for charting |
| GET | `/descriptive/{id}/{variable}` | Descriptive statistics for one variable |
| POST | `/trend/run` | Run one of the six trend tests |
| POST | `/correlation/run` | Run Pearson/Spearman/Kendall correlation |
| POST | `/regression/run` | Run simple linear regression |
| GET | `/visualization/{id}/recommend` | Chart recommendations for a dataset |
| POST | `/report/export/docx` | Compile sections into a DOCX |
| POST | `/report/export/pdf` | Compile sections into a PDF |

Full request/response schemas are in `app/models/schemas.py`, and are also
browsable interactively at `http://localhost:8000/docs` (FastAPI's
auto-generated Swagger UI) while the backend is running.

## Testing

43 automated tests (`backend/tests/`), split into:
- `test_trend_service.py` — unit tests on the statistical functions directly,
  including substantive checks (e.g. that Modified MK actually becomes more
  conservative under autocorrelation, not just that it runs without error).
- `test_api_integration.py` — end-to-end tests through the real FastAPI app,
  including regression tests for two real bugs found during development
  (duplicate-column requests crashing the series endpoint; `numpy.bool_`
  breaking JSON serialization in two of the trend tests).

Run with `pytest` from the `backend/` directory (needs
`requirements-dev.txt` installed, which adds `httpx` and `pypdf` on top of
the runtime dependencies).

## Known limitations (v1)

- Multiple linear and logistic regression are not implemented (simple
  linear only).
- Seasonal Mann-Kendall assumes independence between seasons; the
  covariance-aware extension of the homogeneity test is not implemented.
- The dataset store is in-memory and per-process — restarting the backend
  clears all uploaded datasets. Not suitable for multi-user deployment
  without replacing it with a persistent/session-scoped store.
