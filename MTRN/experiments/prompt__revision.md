# Repair the Materion return and variance experiment

## Objective and controlling scope

Implement the methodological and reporting repairs below in the existing Materion experiment. Prioritize valid comparisons, coherent uncertainty estimates, economic interpretation, and accurate reporting. Do not add deep learning or expand model complexity merely to obtain significant results. A well-supported inconclusive result is an acceptable outcome.

This prompt is stored under `Materion/experiments/review`. The implemented experiment remains under `MTRN/experiments/financial_valuation_models`. These are intentional, distinct paths; do not rename or relocate the existing experiment. All paths below are relative to the repository root.

Read these sources before proceeding:

- `MTRN/experiments/prompt_v2_financial_valuation_models.md`
- `MTRN/experiments/financial_valuation_models/SPECIFICATION.md`
- `MTRN/experiments/financial_valuation_models/README.md`
- `MTRN/experiments/financial_valuation_models/WORK_LOG.md`
- `MTRN/experiments/financial_valuation_models/CONTINUATION_AUDIT.json`
- `MTRN/experiments/financial_valuation_models/COMPLETION_AUDIT.json`
- `MTRN/experiments/financial_valuation_models/final/Financial_Valuation_Model_Comparison.html`
- The experiment's implementation, method tests, raw inputs, processed data, forecast ledger, and validation results.

This repair specification takes precedence where it explicitly corrects an earlier methodological or reporting choice. Retain the earlier specification's full research-report and figure requirements elsewhere.

## 1. Audit the continuation point and preserve the baseline

Before changing anything:

1. Read the completed work rather than restarting from an assumed earlier state. Verify that every referenced section, variable, figure, and output exists and is complete. Identify stale generated artifacts and any truncated code or report sections.
2. Preserve the current experiment, original investment report, and historical-attribution study. Record hashes of baseline code, configuration, input archives, forecasts, and reports.
3. Save revised code and generated outputs in a separate `MTRN/experiments/financial_valuation_models/review_revision` directory. Reuse original input archives read-only. Do not overwrite the baseline to make a comparison appear reproducible.
4. Maintain an issue register linking each finding below to its severity, resolution, supporting artifact, validation, and remaining limitation.
5. Keep the information cutoff at **2026-09-18** and the final complete target month at **2026-08-31**. Retain the primary January 2023–August 2026 evaluation: 44 one-month outcomes per established issuer. Distinguish target-month labels from actual forecast-origin trading dates.
6. Keep MTRN, ENTG, CRS, and ATI as the established-issuer sample. ELMT remains descriptive unless an independently justified eligibility requirement is met; its short public history cannot be manufactured from private operating data.

Label the revision as research performed after inspecting historical results. Freezing a revised specification before rerunning it does not make the historical sample unseen or the study prospectively preregistered. Record methodological decisions before generating revised score tables and explain subsequent changes.

## 2. Make uncertainty reporting internally consistent

The current percentile confidence intervals and recentered bootstrap p-values can disagree about rejection at the same nominal level. Replace that combination with one documented procedure whose confidence intervals and p-values are mutually compatible.

- Define the estimand, null hypothesis, alternative, loss function, sign convention, confidence level, and resampling unit before implementation.
- Use paired, synchronized calendar-block resampling. Preserve dependence between competing models, companies, and overlapping outcomes. For joint cross-company results, resample complete calendar blocks rather than individual company-month rows.
- Retain three-, six-, and twelve-month block sensitivities, designating six months as primary before recomputing results. Use a fixed recorded seed and report the replication count and resulting Monte Carlo resolution.
- Verify agreement between an unadjusted test and its corresponding confidence interval at the same nominal level. Distinguish pointwise intervals from multiplicity-adjusted decisions; Holm-adjusted p-values need not agree with unadjusted interval exclusion.
- Clearly separate conditional uncertainty about saved forecast losses, uncertainty from estimation and hyperparameter selection, and uncertainty from prior specification search. Resampling saved losses does not capture all three.
- Assess small-sample calibration and the assumptions required by the selected procedure. Where formal inference is not adequately supported, report descriptive uncertainty and withhold discovery claims.

Retain the existing sixteen-contrast return family for traceability: valuation addition, P/E difference versus level, ARMA errors versus static, and added lags versus static, each across four established issuers. Report exclusions or degenerate comparisons as untested; do not count identical forecasts as affirmative evidence of no effect.

Before evaluating revised variance forecasts, enumerate a separate variance comparison family by company, model pair, horizon, and loss. Apply multiplicity adjustment within each declared family. Every remaining comparison is exploratory. Adjustment over one family does not validate unrelated model winners or the broader search.

For suitable fixed nested linear specifications, evaluate a Clark–West sensitivity separately from the operational forecast-loss comparison. Do not apply it indiscriminately to tuned penalized models or trees, or treat rejection as proof of an economically useful forecasting strategy.

Useful primary methodological references:

- [Clark–West: predictive accuracy in nested models](https://www.nber.org/papers/t0326)
- [Patton: volatility forecast comparison using imperfect proxies](https://public.econ.duke.edu/~ap172/Patton_vol_proxies_JoE_2011.pdf)

## 3. Reduce predictor redundancy and distinguish availability from testing

Retain the existing six-variable compact model as the main interpretable reference:

- `revenue_growth`
- `operating_margin`
- `earnings_yield`
- `market_return`
- `industry_relative`
- `driver_return`

Keep their original definitions available for baseline comparison. Treat the broad feature catalogue as a sensitivity, not the primary basis for interpreting individual factor contributions.

Add a compact financial extension using equipment-capex operating cash generation relative to assets (`fcf_equipment_assets`) and debt relative to assets (`debt_assets`). Evaluate this predefined financial addition as a group. Preserve its proxy limitations rather than calling it fully reconciled free cash flow. Do not select new combinations based on which produces the most favorable test score.

For every fitted specification, record:

- Candidate and retained predictors, including missing indicators.
- Training-window coverage and the reason each candidate was excluded.
- Imputation, clipping, scaling, and transformation definitions.
- Matrix rank, collinearity diagnostics, and an appropriate measure of model complexity.
- Regularization choices and feature/coefficient selection stability.

Use a broader, documented shrinkage range where the original grid constrains selection; include the intercept-only benchmark as an available validation choice. Avoid simultaneously including redundant levels, lags, and first differences in unpenalized models. Explain that eliminating identical columns does not guarantee full rank or remove economic redundancy.

Keep unavailable variables explicitly untested. Distinguish exclusion, identical forecasts, zero estimated coefficients, unstable coefficients, and evidence against meaningful predictive improvement. Group-average availability is not evidence that each factor was tested at every origin.

## 4. Improve economic and accounting definitions

Audit each business driver against the actual issuer exposure and historical business mix. Keep MTRN copper exposure explicit. Treat natural gas and other weakly matched commodity inputs as exploratory sensitivities rather than equally compelling drivers for every company.

Distinguish traded industry proxies from physical demand indicators. Failure of SOXX, ITA, or commodity-return predictors does not disprove the corresponding operating mechanism. An exposure mapping based on present-day knowledge is not automatically a historical point-in-time mapping.

Explicitly document and test the sensitivity of conclusions to:

- Equipment-only versus mine-inclusive MTRN free cash flow.
- ENTG consolidated-equity substitutions, the age of the supporting NCI evidence, and the absence of proof that an old materiality assessment still applies.
- Unreconciled EV and ROIC proxies, including missing financing claims and denominator conventions.
- Filing-period differences, stale observations, acquisition effects, and business exits.
- Missing analyst estimates, forward valuation, relevant metal prices, and company-specific physical demand data.

Use matched inclusion/exclusion sensitivities for material accounting proxies. Do not substitute missing disclosures with zeros or relabel proxies as fully reconciled measures. State which findings are about accounting representations rather than underlying business economics.

Additional data collection is optional and must not delay repairs to the existing study. Record unavailable inputs and the questions they prevent the study from answering.

## 5. Make training, tuning, pooling, and model comparisons fair

Retain chronological expanding-window evaluation, with the existing primary origins and matured targets. Fit preprocessing and all data-dependent selection inside each training fold.

- Align inner validation with the monthly refitting procedure used in the outer evaluation. At each inner origin, fit only on labels that have matured by that origin.
- Keep annual hyperparameter retuning explicit. Distinguish the December forecast origin from the January target month when describing the schedule.
- Retune the rolling 84-month sensitivity using its own training history. Do not reuse the expanding model's selected penalty while claiming a fully retuned rolling comparison.
- Normalize Ridge regularization consistently with sample size when comparing individual and pooled estimation. Explain the objective-function convention and how estimator parameters map to it.
- Keep pooled folds synchronized by date, and keep company identity available without concatenating issuer histories into a single ARIMA series.
- Use matching histories and targets for comparisons intended to isolate pooling, factor additions, or model structure. Separately label comparisons of complete forecasting procedures that intentionally use different histories.

For variance, estimate a controlled comparison matrix:

1. Individual persistence-only model.
2. Pooled persistence-only model.
3. Individual persistence plus external factors.
4. Pooled persistence plus external factors.

Use the same persistence and external definitions on both sides of each comparison. Retain historical variance, EWMA, and GARCH benchmarks. Document GARCH-X positivity/stability restrictions, external-input timing, assumptions about future external inputs, training-window lengths, and log-variance retransformation.

Continue to distinguish next month's realized variance of daily returns from the variance of the compounded monthly return. Report variance and volatility with their respective units. A square root of expected variance is not generally expected volatility.

## 6. Investigate influential periods without deleting them

Keep all valid observations in headline results. Add diagnostics that:

- Exclude each target month individually.
- Exclude each calendar year individually.
- Display cumulative paired forecast losses.
- Separate market regimes defined from information known at the origin.
- Compare one- and three-month forecasts on common origins, while identifying the different target periods.
- Report all nonoverlapping three-month calendar offsets.

Explicitly revisit MTRN's August 2024 and ENTG's April 2025 influence. Determine whether the apparent CRS and ATI variance improvements remain more stable across these checks. These observations are not errors simply because they are influential, and their removal must not become the preferred result.

State whether diagnostics hold saved forecasts fixed or refit the full procedure. Do not call a loss-only exclusion a full training-sample robustness test.

Nonoverlapping outcomes are not necessarily independent. Do not dismiss a longer-horizon finding merely because the one-month finding is weak. Report its uncertainty, calendar dependence, and effective information without claiming that three offsets are three independent replications.

## 7. Correct the identified reporting and export defects

Repair and validate all of the following:

1. Forecast-origin dates versus target-month dates. The original one-month actual origins run December 30, 2022–July 31, 2026; January 2023–August 2026 describes target months.
2. Missing base-variable definitions for `industry_relative` and `driver_return`, including their use in the six-variable compact model.
3. Blank leave-one-block-out incremental losses caused by looking up comparisons in the opposite direction. If a stored comparison is reversed, reverse both the estimated loss difference and interval endpoints correctly.
4. The omitted MTRN–ATI exception in the correlation discussion. Generate claims about interval exclusion from the actual table rather than hard-coded prose.
5. Coverage summaries presented as training eligibility despite being calculated over a larger descriptive sample.
6. Differences between monthly forecast regimes and daily correlation regimes, including their exact windows, thresholds, and timing.
7. Successful-fit comparisons: score each pair on the intersection of origins where both fitted successfully. Maintain a separate operational score including documented fallbacks.

Check every displayed value, model label, variable name, caption, unit, horizon, and conclusion against its generating artifact. Verify that all figures are numbered, discussed in the text, and supported by readable source data.

Remove or qualify unsupported assertions that:

- Pooling's economic mechanism has been established by a performance difference.
- Success on variance establishes adequate statistical power for the return experiment.
- The sample is underpowered against every plausible effect without a stated power analysis.
- Failure to reject improvement establishes equivalence, zero effect, or stable absence of a relationship.
- Keeping a derived variable in a reduced model necessarily changes out-of-sample performance in a particular direction.

Quantify detectable effects under explicit calibration assumptions where feasible. Otherwise state the observed uncertainty without inventing a universal power claim.

## 8. Reframe investment conclusions

For every major result distinguish:

1. **Explanatory association:** what variables move together conditionally, without implying causality.
2. **Predictive usefulness:** whether additional information improves matched out-of-sample performance, including performance against a credible simple benchmark.
3. **Statistical evidence:** what survives the applicable uncertainty assessment, multiplicity treatment, and sensitivity checks.
4. **Investment relevance:** whether an economically actionable benefit has actually been demonstrated.

A lower RMSE is not investment alpha. A lower variance loss is not demonstrated portfolio improvement. A stock return minus SPY is market-relative return, not automatically risk-adjusted alpha or return in excess of the risk-free rate.

Assess whether findings could inform valuation work, risk monitoring, diversification, or position sizing. Explain when transaction costs, feasible execution timing, covariance forecasting, position constraints, or an explicit portfolio experiment remain necessary. A closing-price-based statistical forecast is not automatically executable at that closing price.

Keep investment interpretation company-specific. Do not transfer a stronger CRS result to MTRN or conclude that all firms benefit because an average score improves. Preserve the distinction between uncertain short-horizon returns and intrinsic valuation.

## 9. Deliverables, acceptance, and completion record

Produce within the revision directory:

- A revised standalone research report and consistent figures with source data.
- Machine-readable model scores, paired comparisons, inference families, ablations, coverage/selection records, and influence diagnostics.
- A completed issue-resolution register, with explicit deferrals and their implications.
- Baseline-versus-revision comparisons identifying which results changed and why.
- Revised code, pinned or recorded dependencies, a reproducible execution command, and validation results.
- A continuation/completion record that makes the final state clear to a later researcher.

Retain the research-question → setup → variables → evaluation → results → figures → interpretation → conclusion structure for each major experiment. Explain financial mechanisms, model choices, transformations, missing-value treatment, timing, metrics, and limitations in precise, readable language. Maintain the eight research questions in the existing specification or provide an explicit crosswalk if organizing the report differently.

Acceptance requires:

- Independent reproduction of return and variance targets and all headline evaluation metrics.
- Chronological availability, training-label maturity, and future-data perturbation checks.
- Compatible unadjusted confidence-interval and p-value decisions, with adjusted decisions separately labeled.
- Explicit comparison families and correctly scoped multiplicity treatment.
- Matched-date ablations with populated incremental results and correct reversal of paired intervals.
- Complete variable and model registries, including all compact inputs.
- Influence, horizon, and regime diagnostics supporting the strength of the conclusions.
- No unsupported claim of causality, stable forecast superiority, or investment profitability.
- Preserved original artifacts and a clear account of changed results.

A wider issuer panel, archived analyst estimates, physical business drivers, intraday variance measures, and portfolio execution tests remain follow-up research unless needed to resolve a demonstrated defect. If clustering is proposed, apply it to a sufficiently broad, economically relevant universe using training-period information; clustering five selected companies is not a substitute for predictive evidence.

Finish by stating which issues were resolved, which remain unanswered, what the revised evidence supports, and what it cannot support. Do not treat statistical significance as a completion requirement.
