"""
Automated Interpretation engine.

Rule-based by design — no LLM call in v1. That keeps results
reproducible, free to run, and defensible as StatScholar's own authored
logic. Each function takes a stats result dict (from trend_service /
correlation_service / regression_service) and returns
{student_text, research_text, flags}.
"""


def _effect_size_band(value: float) -> str:
    v = abs(value)
    if v < 0.10:
        return "negligible"
    if v < 0.30:
        return "weak"
    if v < 0.50:
        return "moderate"
    if v < 0.70:
        return "strong"
    return "very strong"


def interpret_mann_kendall(result: dict, variable: str, time_unit: str = "year") -> dict:
    strength = "strong" if result["p_value"] < 0.01 else "moderate" if result["significant"] else None
    direction = result["direction"]

    if result["significant"]:
        student = (
            f"The Mann-Kendall test was used to check whether {variable} shows a trend "
            f"over the {result['n']}-{time_unit} period. The test found a statistically "
            f"{strength} {direction} trend (p = {result['p_value']}, below the "
            f"{result['alpha']} threshold), meaning it's unlikely this pattern happened by chance."
        )
        research = (
            f"A Mann-Kendall trend test indicated a statistically significant {direction} trend "
            f"in {variable} over the study period (S = {result['S']}, Z = {result['Z']}, "
            f"\u03c4 = {result['tau']}, p < {result['alpha']}, n = {result['n']})."
        )
    else:
        student = (
            f"The Mann-Kendall test did not find a statistically significant trend in {variable} "
            f"(p = {result['p_value']}), meaning any rise or fall you see in the data could just "
            f"be random variation rather than a real pattern."
        )
        research = (
            f"A Mann-Kendall trend test found no statistically significant trend in {variable} "
            f"(S = {result['S']}, Z = {result['Z']}, p = {result['p_value']}, n = {result['n']})."
        )

    return {"student_text": student, "research_text": research, "flags": []}


def interpret_autocorrelation_flag(autocorr: dict) -> list:
    if autocorr["significant_autocorrelation"]:
        return [
            f"Lag-1 autocorrelation detected (r\u2081 = {autocorr['r1']}). Consider Modified "
            f"Mann-Kendall or Trend-Free Pre-Whitening instead of the standard test."
        ]
    return []


def interpret_modified_mann_kendall(result: dict, variable: str) -> dict:
    if result["significant"]:
        student = (
            f"Because the data showed autocorrelation, a corrected version of the Mann-Kendall "
            f"test was used instead. This adjustment accounts for the fact that values close "
            f"together in time tend to be similar. The corrected test still found a statistically "
            f"significant {result['direction']} trend (p = {result['p_value']})."
        )
        research = (
            f"Given significant autocorrelation, the Modified Mann-Kendall test (Hamed & Rao, "
            f"1998) was applied to {variable}. Results indicated a significant {result['direction']} "
            f"trend (Z = {result['Z']}, correction factor = {result['correction_factor']}, "
            f"p = {result['p_value']})."
        )
    else:
        student = (
            f"A corrected version of the Mann-Kendall test, which accounts for autocorrelation in "
            f"the data, did not find a statistically significant trend in {variable} "
            f"(p = {result['p_value']})."
        )
        research = (
            f"The Modified Mann-Kendall test (Hamed & Rao, 1998) found no statistically "
            f"significant trend in {variable} (Z = {result['Z']}, "
            f"correction factor = {result['correction_factor']}, p = {result['p_value']})."
        )
    return {"student_text": student, "research_text": research, "flags": []}


def interpret_pre_whitening(result: dict, variable: str) -> dict:
    if result["pre_whitening_applied"]:
        student = (
            f"Before testing for a trend, StatScholar checked whether values in {variable} are "
            f"related to their immediate past values. A meaningful relationship was found "
            f"(r\u2081 = {result['r1']}), so the data were 'pre-whitened' to remove that "
            f"autocorrelation before running the Mann-Kendall test. "
            f"{'A statistically significant ' + result['direction'] + ' trend remained (p = ' + str(result['p_value']) + ').' if result['significant'] else 'No statistically significant trend remained after this correction (p = ' + str(result['p_value']) + ').'}"
        )
    else:
        student = (
            f"No meaningful autocorrelation was found in {variable} (r\u2081 = {result['r1']}), "
            f"so pre-whitening wasn't needed — the standard Mann-Kendall result applies "
            f"(p = {result['p_value']})."
        )
    research = (
        f"Lag-1 autocorrelation {'was' if result['pre_whitening_applied'] else 'was not'} "
        f"detected (r\u2081 = {result['r1']}, critical value = {result['critical_value']}). "
        f"{'Pre-whitening (von Storch, 1995) was applied prior to' if result['pre_whitening_applied'] else 'The standard'} "
        f"Mann-Kendall test on {variable} yielded Z = {result['Z']}, p = {result['p_value']}."
    )
    flags = []
    if result["pre_whitening_applied"]:
        flags.append(
            "Pre-whitening can remove part of a genuine trend along with the autocorrelation. "
            "Trend-Free Pre-Whitening is generally preferred when a real trend may be present."
        )
    return {"student_text": student, "research_text": research, "flags": flags}


def interpret_trend_free_pre_whitening(result: dict, variable: str) -> dict:
    student = (
        f"This is a more careful version of pre-whitening: it removes the trend first, corrects "
        f"for autocorrelation, then adds the trend back — avoiding the risk of removing part of "
        f"a real trend along with the autocorrelation. "
        f"{'The result shows a statistically significant ' + result['direction'] + ' trend (p = ' + str(result['p_value']) + ').' if result['significant'] else 'No statistically significant trend was found (p = ' + str(result['p_value']) + ').'}"
    )
    research = (
        f"Trend-free pre-whitening (Yue et al., 2002) was applied to {variable} "
        f"(Sen's slope used for detrending = {result['sen_slope_used']}, "
        f"r\u2081 of detrended series = {result['r1_detrended']}). The corrected series "
        f"{'retained' if result['significant'] else 'showed no'} significant "
        f"{result['direction']} trend (Z = {result['Z']}, p = {result['p_value']})."
    )
    return {"student_text": student, "research_text": research, "flags": []}


def interpret_seasonal_mann_kendall(result: dict, variable: str) -> dict:
    student = (
        f"Because {variable} is recorded across {result['n_seasons']} seasons, the Seasonal "
        f"Mann-Kendall test was used — this checks for a trend within each season, then combines "
        f"the results. "
        f"{'Overall, this found a statistically significant ' + result['direction'] + ' trend (p = ' + str(result['p_value']) + ').' if result['significant'] else 'No statistically significant combined trend was found (p = ' + str(result['p_value']) + ').'}"
    )
    research = (
        f"A Seasonal Mann-Kendall test was conducted across {result['n_seasons']} seasonal "
        f"blocks for {variable}, yielding a combined statistic of S = {result['S']} "
        f"(Z = {result['Z']}, p = {result['p_value']}). A Van Belle & Hughes (1984) chi-square "
        f"test for homogeneity of trend across seasons was "
        f"{'not significant' if result['homogeneous'] else 'significant'} "
        f"(\u03c7\u00b2 = {result['homogeneity_chi2']}, df = {result['homogeneity_df']}, "
        f"p = {result['homogeneity_p']})."
    )
    flags = []
    if not result["homogeneous"]:
        season_list = ', '.join(result['disagreeing_seasons']) if result['disagreeing_seasons'] else "one or more seasons"
        student += (
            f" A formal test found the trend is not consistent across all seasons "
            f"(season(s) {season_list} moved differently from the rest), so the overall trend "
            f"doesn't apply equally year-round."
        )
        flags.append(
            f"Trend is not homogeneous across seasons (\u03c7\u00b2 = {result['homogeneity_chi2']}, "
            f"p = {result['homogeneity_p']}) — season(s) {season_list} disagree with the combined direction."
        )
    return {"student_text": student, "research_text": research, "flags": flags}


def interpret_sens_slope(result: dict, variable: str, unit: str, time_unit: str = "year") -> dict:
    direction = "increasing" if result["slope"] > 0 else "decreasing" if result["slope"] < 0 else "flat"
    student = (
        f"The Sen's Slope estimator was used to measure how fast {variable} is changing. "
        f"On average, {variable} is {direction} by about {abs(result['slope'])} {unit} per "
        f"{time_unit} (95% CI: {result['ci_lower']} to {result['ci_upper']})."
    )
    research = (
        f"Sen's slope estimator yielded a magnitude of {result['slope']} {unit}/{time_unit} "
        f"(95% CI [{result['ci_lower']}, {result['ci_upper']}]), indicating a {direction} trend."
    )
    return {"student_text": student, "research_text": research, "flags": []}


def interpret_correlation(r: float, p_value: float, var1: str, var2: str, method: str, alpha: float = 0.05) -> dict:
    significant = p_value < alpha
    strength = _effect_size_band(r)
    direction = "positive" if r > 0 else "negative"

    if significant:
        student = (
            f"A {method} correlation was run to see how {var1} and {var2} relate to each other. "
            f"There is a {strength} {direction} relationship between them (r = {round(r, 3)}, "
            f"p = {round(p_value, 4)}) — meaning as {var1} goes {'up' if r > 0 else 'down'}, "
            f"{var2} tends to go {'up' if r > 0 else 'down'} too."
        )
        research = (
            f"A {method} correlation coefficient was computed to assess the relationship "
            f"between {var1} and {var2}. There was a statistically significant {strength} "
            f"{direction} correlation, r = {round(r, 3)}, p < {alpha}."
        )
    else:
        student = (
            f"A {method} correlation was run between {var1} and {var2}. No statistically "
            f"significant relationship was found (p = {round(p_value, 4)}), so we can't conclude "
            f"these two variables are related based on this data."
        )
        research = (
            f"No statistically significant {method} correlation was found between {var1} and "
            f"{var2} (r = {round(r, 3)}, p = {round(p_value, 4)})."
        )

    flags = ["Correlation shows a relationship, not that one variable causes the other."]
    return {"student_text": student, "research_text": research, "flags": flags}


def interpret_regression(result: dict, predictor: str, outcome: str, alpha: float = 0.05) -> dict:
    significant = result["p_value"] < alpha
    r2 = result["r_squared"]
    r2_band = (
        "explains very little of the variation" if r2 < 0.10 else
        "explains a small amount" if r2 < 0.30 else
        "explains a moderate amount" if r2 < 0.50 else
        "explains a substantial amount" if r2 < 0.70 else
        "explains most of the variation"
    )

    if significant:
        student = (
            f"A simple linear regression was used to see whether {predictor} can predict "
            f"{outcome}. The model was statistically significant (p = {round(result['p_value'], 4)}), "
            f"and for every 1-unit increase in {predictor}, {outcome} changes by "
            f"{round(result['slope'], 3)} on average. The model {r2_band} in {outcome} "
            f"(R\u00b2 = {round(r2, 3)})."
        )
    else:
        student = (
            f"A simple linear regression was used to see whether {predictor} can predict "
            f"{outcome}. The model was not statistically significant "
            f"(p = {round(result['p_value'], 4)}), meaning {predictor} does not reliably "
            f"predict {outcome} based on this data."
        )

    research = (
        f"A simple linear regression was conducted to predict {outcome} from {predictor}. "
        f"The model was {'statistically significant' if significant else 'not statistically significant'}, "
        f"F = {round(result['f_statistic'], 2)}, p = {round(result['p_value'], 4)}, R\u00b2 = {round(r2, 3)}."
    )

    return {"student_text": student, "research_text": research, "flags": []}
