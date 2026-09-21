# Output definitions

All observation/period dates are ISO dates. Return fractions are decimal in CSV:
0.01 = 1%. Variance is squared decimal return; the report multiplies it by 10,000
for squared percentage points. Means/volatility multiply by 100 in the report.
All monetary statement amounts in derived financial tables are **USD millions**,
except EPS and prices (USD/share); actual shares are millions. Raw SEC fact
audits retain their original USD, USD/share or shares units/tag context.

| Files | Meaning / main fields |
|---|---|
| daily_returns, monthly_returns | Adjusted-close simple returns; monthly returns compound daily returns. No forward filling; no partial September month. |
| daily_factors, monthly_factors | French returns/RF in decimals. MKT = market excess return, SMB = size, HML = value, MOM = momentum. Data through July2026. |
| holding_returns | Total return and CAGR from base close; CAGR missing for <1 year. Max drawdown includes initial wealth. Annual mean is arithmetic, not CAGR. |
| moments | Panel, frequency, basis, N/dates; mean and block SE/CI; sample N−1 variance and CI; volatility and CI; lag-1 correlation; block size. Annual volatility is a secondary √frequency conversion. |
| paired_comparisons | Synchronized MTRN−peer mean differences, MTRN/peer variance and volatility ratios and pointwise intervals. Identical dates within a row. |
| covariance_*, correlation_* | Matched daily total-return sample covariance/correlation, one file per panel. |
| models | Monthly excess-return regressions. Alpha/CI/p use HAC3. Residual/fitted/total variance share N−1. `residual_mse` uses N−p separately. `*_boot_*` comes from row-block refits. Scaled condition number uses standardized factor columns. |
| coefficients | Monthly beta, HAC SE/CI/p, factor mean and mean contribution. `const` is alpha. ETF regressors are excess returns. Nominal-yield beta is return fraction per one percentage-point yield change. |
| primary_alpha_family | Four long M2 alpha tests with BH q-values. Pointwise CIs are not simultaneous intervals. |
| model_exclusions | Ineligible model/firm/panel and exact sample-size gate reason. |
| model_residuals_* | Actual monthly excess return, fitted value including alpha, and in-sample residual. Not an investable wealth series. |
| daily_models, daily_residual* | Separate raw-return daily market/industry fits. Their intercept is not risk-free-adjusted alpha. Residual mean is zero by construction. |
| refitted_model_moments | Joint synchronized refits: native intercept and residual variance/volatility with intervals. `basis` distinguishes raw and excess returns. |
| paired_model_comparisons | Jointly refitted MTRN−peer intercept/alpha difference and residual variance/volatility ratios with intervals. Primary long monthly M2, recent M1, and daily models. |
| refitted_contributions | Beta intervals and factor-mean contribution intervals, re-estimating both beta and sample factor mean within each resample. |
| factor_correlations | Correlations among available monthly factors; shared variance prevents unique causal block percentages. |
| moment_sensitivity_* | Daily primary total-return moments under five-/twenty-session blocks. |
| monthly_bootstrap_* | Primary long/recent model intervals under two-/six-month blocks. |
| hac_sensitivity | Primary long/recent models with zero/six HAC lags (three is baseline). |
| daily_model_stability | Simpler daily market-only fits, and chronological half-sample market/industry fits. No optimized breakpoint. |
| influence_checks | Remove one/five largest absolute returns per firm; primary data retain all observations. |
| announcement_influence | Recent daily mean/variance before/after removing the union of primary three-session announcement windows. |
| financial_snapshots | As-known endpoints: TTM flows, approximate rolling EPS, contemporary price, latest filed actual shares, carrying debt, equity/FCF multiples. Missing/older-period measures are not silently carried forward. |
| financial_fact_audit | One record per fact selection: asof, filed, available, period start/end, duration days, accession, tag, source URL, value, metric. Comparative facts are selected only from eligible filed vintages. |
| manual_mine_disclosures.json | Original 10-K mining-capex rows and filing/accession dates supplement standard SEC tags. |
| annual_operating_history | Annual data from latest eligible cutoff vintage; fiscal dates retained; not a historical availability panel. |
| quarterly_operating_history | Directly disclosed 60–110-day revenue/profit/EPS observations. CFO/capex derived from compatible same-accession YTD components; missing Q4/other unavailable values remain missing. |
| accounting_bridges | Four endpoint windows. Price and EPS/multiple log contributions; total return separately; dividend/reinvestment gap = total simple return − price simple return. Validity flag and limitations. |
| earnings_announcements | Original release date/session, timing evidence, filing/accession, EPS and prior-year EPS, quarterly GAAP margins, pre-release close, financial updates. Release revenue/income are retained in the exhibit's units (thousands or millions); ratios cancel that common scale. |
| earnings_extractions.json | Verbatim archived GAAP table extraction plus release/date evidence; inspect before changing parser rules. |
| event_cars | Market or market+industry model, conservative or same-date mapping, primary [−1,+1], short [0,+1] or wide [−1,+5]. CAR is arithmetic summed abnormal return. Explicit estimation and event dates, N and market beta. |
| event_summary | Per-firm primary mean CAR and event-to-event N−1 variance with two-calendar-quarter-block intervals; event counts and complete update counts. |
| event_regression | Four company intercepts + common slopes on price-scaled YoY EPS change and YoY margin change. Both covariates in decimals. Intervals preserve pairs and calendar-quarter dependence. |
| event_sensitivity | Event counts/means/variances across each window, timing convention and benchmark. `var` is N−1 event variance. |
| event_exclusions | Non-quarterly releases and duplicate presentation/8-K exclusions, source paths retained. |
| strategic_events | Selected source-established disclosure context, overlap flags and dates; not exhaustive or independently causal. |
| business_exposure, coverage | Issuer/security mapping, qualitative exposure map, raw coverage and recorded split counts. No present-day exposure weights backfilled. |
| report_coverage | Report coverage table generated from calculated moments, models, holding periods and announcement counts. |
| ELMT_case.json | Manually reconciled H1 operating data and Q2 balances; September preferred/warrants/conditional commitment reviewed separately. Grant-netted capex; no invented pro-forma balance sheet. |
| ELMT_event_returns | Compounded close-to-close ELMT/SPY/ITA returns and arithmetic differences between those returns. Descriptive; not model CARs. |
| secondary_price_checks, large_move_audit | Second-provider close reconciliations and outstanding verification gaps; no winsorization or deletion. |
| synthesis | Central research summary table. Distinct accounting/mean/variance/event columns. |
| input_hashes, validation_results.json | Source inventory/hash and completion validation. |
| reproducibility_results.json | Recorded two-rebuild comparison of numerical/audit CSV and JSON hashes, with test counts. Not regenerated by an ordinary single rebuild. |
| deferrals.json | Dataset failures, sample restrictions and deliberately simplified functions. |

## Model and resampling conventions

Long window starts 2016; recent starts 2021; matched starts with returns after
ELMT's Apr23 first close. Monthly M0 = MKT; M1 = MKT+SMB+HML+MOM;
M2 = M1+SEMIS+DEFENSE. M1_nominal and M2_nominal add the change in the nominal
10-year yield. FF5_MOM uses the FF5-specific SMB, HML, RMW, CMA and MKT, plus MOM.
The full real-yield/credit M3 is unavailable. Each monthly panel shares one
complete-case date set; the gate is max(60, 10×parameters including intercept).

Moving blocks are non-circular contiguous blocks with uniformly sampled valid
start positions, concatenated and truncated to N observations. Samples preserve
cross-issuer rows. 2,000 replications, seed20260918. Event bootstraps sample two
adjacent calendar quarters, then retain all issuer events in those quarters;
the number of events per resample may vary. Percentile 2.5%/97.5% intervals are
approximate. Joint model comparisons refit OLS in every resample. No ordinary
IID standard error, distributional higher-moment estimator or investor-motive
proxy is part of the primary analysis.

Weekly returns require every observed SPY calendar session in a Friday-ending
bin, with valid returns for every compared issuer. This retains complete first
weeks and holiday-shortened weeks. Bins ending after the effective cutoff and
incomplete opening weeks are excluded. Excess weekly returns are compounded
stock returns less separately compounded risk-free returns on those same days.
