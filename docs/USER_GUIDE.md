# StatScholar User Guide

StatScholar is a general-purpose statistical analysis platform, anchored by a
complete six-test Mann-Kendall trend-analysis suite, that walks you from raw
data to a finished report — explaining every result in either plain language
(Student Mode) or formal statistical reporting (Research Mode).

## Getting started

1. Start the backend and frontend (see the main README for setup).
2. Open the app in your browser. You'll land on the **Dashboard**.
3. Drag a CSV, XLSX, or TSV file onto the upload area, or click "Browse
   files." The first row of your file is read as the column headers.

Once a dataset is loaded, its name and row count appear in the sidebar, and
every module becomes usable.

## The Student / Research toggle

The button in the top-right corner switches how every result is explained:

- **Student Mode** — plain-language explanations, written to be understood
  without a statistics background. Numbers are still shown, but the
  emphasis is on what a result *means*.
- **Research Mode** — formal statistical reporting style (e.g.
  "Z = 2.87, p < .01"), suited for copying into a methods or results section.

You can switch modes at any time — it doesn't re-run anything, it just
changes how the same underlying numbers are explained. Any report you
export uses whichever mode is active when you export it.

## Module walkthrough

### 1. Data Preparation
Shows the detected type of each column (nominal, ordinal, interval, or
ratio), a 0–100 data quality score, how much of each column is missing,
and a preview of the first rows. Fix any misdetected column type before
moving on — the trend tests specifically need a properly ordered time
column to work correctly.

### 2. Descriptive Statistics
Per-variable summary: mean, median, standard deviation, variance,
skewness, kurtosis, min/max, and a Shapiro-Wilk normality test p-value.

### 3. Trend Analysis — the flagship module
Six non-parametric trend tests, all from the Mann-Kendall family, commonly
used in hydrology, climate science, and other time-series work:

| Test | What it answers | When to use it |
|---|---|---|
| Mann-Kendall | Is there a monotonic trend? | Default starting point |
| Sen's Slope | How big is the trend? | Always report alongside Mann-Kendall |
| Modified Mann-Kendall | Is there a trend, corrected for autocorrelation? | When your data shows autocorrelation |
| Pre-Whitening | Trend test after removing autocorrelation | Alternative autocorrelation correction |
| Trend-Free Pre-Whitening | Pre-whitening that preserves genuine trends | Preferred over plain Pre-Whitening |
| Seasonal Mann-Kendall | Is there a trend once seasonal effects are accounted for? | Data with a repeating seasonal pattern (e.g. quarterly, monthly) |

Pick a variable and a time column, and for Seasonal Mann-Kendall, also pick
a **season column** — a repeating group label (like quarter 0–3 or month
1–12) that is *not* the same column as your time index.

Every result includes a chart of the series, the full statistics, and an
automated interpretation. If autocorrelation is detected, the app will
suggest switching to a correction method.

### 4. Correlation
Pearson, Spearman, or Kendall Tau correlation between two variables, shown
as a matrix, a scatter plot, and an interpretation that includes effect
size in plain language (weak/moderate/strong).

### 5. Regression
Simple linear regression between a predictor and an outcome. Residual
diagnostics (normality, homoscedasticity) run automatically — if an
assumption is violated, you'll see a flagged warning explaining what that
means for how much to trust the result.

### 6. Visualization
Chart recommendations computed from your actual dataset — which chart
type fits which columns, and why, ranked by relevance.

### 7. Automated Interpretation
A running log of every explanation generated this session, in the order
you generated them. This is also what feeds into Report Generation.

### 8. Report Generation
Compiles everything in your Automated Interpretation log into a single
document. Export as DOCX (editable in Word) or PDF. The report follows
whichever mode (Student/Research) is currently active.

## Tips

- Run analyses in the order shown in the sidebar — later modules (like
  Report Generation) depend on results from earlier ones.
- If a trend test result seems off, check the Data Preparation module
  first — a misdetected column type is the most common cause.
- For Seasonal Mann-Kendall, the season column and time column must be
  different columns, even though both are usually numeric.
