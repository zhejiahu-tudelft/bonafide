# Financial, valuation and business-driver models: a historical forecasting experiment

**Protocol version:** 2, drafted September 20, 2026.
**Reporting requirements:** Expanded September 20, 2026 after the continuation review; sections 15–18 are mandatory parts of this protocol.
**Initial companies:** MTRN, ENTG, CRS, ATI and ELMT.
**Information/price cutoff:** September 18, 2026, US market close.
**Primary question:** Do company financial characteristics, starting valuations and their changes add useful historical out-of-sample information about returns, and does adding time-series structure improve on a static regression using the same information?

## 1. Assignment and relationship to the existing experiment

Act as an empirical-finance researcher and implement this protocol reproducibly. Improve the existing framework by explicitly testing company financial and valuation variables as explanatory predictors. Compare static, distributed-lag and dynamic regression models without presuming which will win.

Read these existing artifacts first:

- `MTRN/README.md` and the original investment report.
- `MTRN/experiments/prompt.md` and `historical_attribution/README.md`.
- `historical_attribution/final/Historical_Attribution.html`.
- `historical_attribution/final/Investment_Interpretation.md` and its diagnostic outputs.
- Existing data dictionaries, source manifests, financial availability audits, code, tests and deferrals.

Preserve the original protocol, reports, source archives and numerical outputs. Place this implementation in `MTRN/experiments/financial_valuation_models/`. Reuse verified shared utilities and immutable source files rather than overwriting them or duplicating all downloads.

The earlier study estimated contemporaneous market/style/industry exposures, examined financial announcements and decomposed price changes into EPS and P/E changes. It did not estimate a combined predictive model of company financial characteristics and valuation levels. Do not describe that earlier model as a completed test of this new question.

This protocol deliberately adds **historical forecasting evaluation**: recreate forecasts from successive past information dates and assess outcomes already observed by the cutoff. Do not issue a live trading signal or claim a previously unseen sample. The companies and much of their history have already been reviewed; this is a newly frozen comparison protocol, not a claim of formal preregistration or an untouched historical holdout. Future genuinely unseen data would be needed for independent prospective confirmation.

Continue to focus on first moments and second central moments. Skewness, kurtosis and attribution to investor motives remain outside scope. No statistical significance or winning model is required for completion.

## 2. Targets, dates and what counts as a forecast

### Primary target: next-month total return

At the final trading close of month `t`, assemble the information available by that close, `I_t`. Predict:

```text
y[i,t+1] = adjusted_close[i,t+1] / adjusted_close[i,t] - 1
```

Use a documented dividend/split-adjusted total-return proxy, with corporate-action checks and no double counting of dividends. Model arithmetic returns; do not substitute stock-price levels and obtain misleadingly high fit from common trends. This close-to-close evaluation is an informational forecast benchmark, not a claim of execution at the already observed closing auction.

Use established-company target months from January 2016 through August 2026, where the required as-known inputs exist. September 2026 is incomplete at the cutoff and is excluded from monthly targets. Retrieve earlier statements/prices only as necessary for initial lags, trailing metrics and valuation histories. Do not silently shorten every analysis to July merely because the old French/RF archive stops there; publish the actual dates supported by each feature set.

### Secondary targets

1. Next-month stock return minus SPY return over the identical month. The future SPY return is part of the realized target, not an input known in advance.
2. Three-month compounded total return, using the same past information at origin `t`. Treat overlapping labels explicitly. Do not add many horizons after seeing results.
3. A separate risk task, where feasible: next month's **realized within-month daily variance**, `v[i,t+1] = sum((daily_return - monthly_daily_mean)^2)/(D-1)`, with `D` observed trading sessions. This is a daily-return central variance estimated during the future month, not the raw second moment and not automatically the variance of a monthly return. Predict log variance if useful, then use a documented training-only retransformation correction when reporting a mean variance forecast. Report volatility as its square root. Do not infer successful risk forecasting merely from lower return-forecast RMSE.

The one-month return target determines the primary model comparison. Secondary targets have separate tables, uncertainty and multiplicity labels. Directional accuracy is appropriate for signed return targets, not the sign of a positive variance target.

### Distinguish three different activities

- **Forecasting:** only `I_t` predicts the outcome after `t`.
- **Contemporaneous explanation:** actual market/industry/commodity movements during the outcome period may explain realized stock movements. These are separately labeled historical associations.
- **Accounting decomposition:** a price/EPS/multiple identity describes the arithmetic of repricing. It is not an independent predictive regression or causal decomposition.

Never put realized next-month market returns, next-month commodity changes, a financial statement released next month, or a valuation measured at next month's closing price into the forecast from `t`. A conditional forecast supplied with those future realizations is an oracle/scenario diagnostic and must not appear on the genuine forecast leaderboard.

## 3. Availability, accounting and security data

Build one monthly as-known feature table, with a separate long-format audit of every input. Each value must record issuer, economic period, original release/filing timestamp, first usable session, vintage, source URL/accession, retrieval date, units, transformation and missing-data reason.

1. Financial period end is not its availability date. Use the first verified public release containing the actual metric. If only a filing/release date is known, use the next trading session. Do not use after-close news at the preceding close.
2. Reconstruct historical releases and filings. Current revised/restated histories cannot automatically serve as historical predictor vintages. Keep a separately labeled latest-comparable history for explanatory context.
3. Quarterly fundamentals may be carried forward **after** publication until replaced. Record their age in days and number of distinct underlying releases. Repeated monthly values do not create new independent earnings announcements. Do not interpolate unreleased financial statements.
4. Derive TTM dollar flows from compatible quarter/YTD components. Reconcile fiscal-year differences, 52/53-week years, acquisitions, disposals and reporting currencies. Missing flows are not zero. Do not difference cumulative statements across incompatible vintages.
5. Keep common-share earnings, consolidated earnings, actual shares and diluted weighted-average shares distinct. Adjust historical per-share observations consistently for splits. Repair the earlier approximate rolling-EPS approach where the data permit; disclose any approximation that remains.
6. Reconstruct contemporaneously known share counts, financing claims and corporate actions. Never apply the latest shares, preferred financing or current index membership to all past dates.
7. For macro series, use release dates and historical vintages where revised data matter. For market prices, use what was observed by the origin. Any unavoidable retrospective-vintage input belongs in a labeled sensitivity unless its historical equivalence can be established.
8. Keep GAAP and reconciled non-GAAP measures separate. Identify impairment, restructuring, acquisition accounting and unusual taxes. Apply predefined treatments consistently across issuers; never delete inconvenient observations because their returns are extreme.
9. Archived historical analyst estimates are required for forward valuation, earnings surprises and estimate revisions. Today's consensus cannot reconstruct past expectations. If unavailable, mark those features unavailable and compare other models on the same eligible dates.

For MTRN, include mine-development investment in total capex and retain value-added sales as an issuer-specific supplement to gross revenue. Do not treat another issuer's gross revenue as directly equivalent to MTRN value-added sales. For CRS, preserve surcharge-inclusive and surcharge-excluded distinctions when available. For ATI, reconcile minority interests and exceptional accounting charges. For ENTG, flag acquisitions/disposals and acquired-intangible amortization. Verify each issue from original documents rather than relying only on this candidate list.

ELMT's April 2026 IPO/reorganization and subsequent preferred/warrant financing require a separate common-share claims bridge. Its private operating history can provide financial context; it cannot create public stock returns. It fails the primary long-history gates at this cutoff, so retain a descriptive case and an explicit model exclusion rather than fitting a spurious full model.

## 4. Financial factor catalogue: company characteristics

Create a feature registry with the formula, units, availability rule, economic mechanism, denominator validity and status for every item below. The catalogue is a candidate set, not an instruction to put every correlated variable into an unpenalized regression.

Use latest available TTM flows by default, quarterly year-over-year growth to limit seasonality, and average balance-sheet stocks over the corresponding earnings period for return-on-capital ratios.

| Dimension | Required candidate definitions | Economic interpretation / guardrail |
|---|---|---|
| Revenue growth | Latest reported quarterly revenue / comparable prior-year quarterly revenue − 1; TTM year-over-year growth as an alternative. | Business expansion; distinguish price pass-through, volume, FX and acquisitions where disclosed. Add gross-profit growth or disclosed organic/VA growth as comparable supplements, not invented equivalents. |
| Earnings and EPS growth | Comparable quarterly common earnings or diluted EPS / prior-year value − 1, when both values and the denominator make percentage growth meaningful. | Change in profitability available to shareholders. For losses, zero or tiny bases, retain dollar/per-share changes, common-earnings change scaled by lagged assets, and loss-transition flags. Do not call a change from a loss to a profit an ordinary percentage growth rate. |
| Profit margins | Gross profit/revenue; operating income/revenue; common net income/revenue. | Pricing power, cost control and operating efficiency. Keep numerator/denominator conventions compatible; pass-through sales can distort comparisons. |
| ROE | TTM earnings available to common / average common book equity over the period. | Earnings relative to shareholders' accounting capital; flag nonpositive equity. |
| ROA | TTM consolidated net income / average consolidated total assets. | Profitability relative to the asset base. Do not mix common-only earnings and an unreconciled consolidated denominator without a flag. |
| ROIC | TTM NOPAT / average invested capital; NOPAT = EBIT × (1 − normalized tax rate); invested capital = common equity + preferred capital + noncontrolling interests + interest-bearing debt − cash, under a fixed claims convention. | Operating return on invested financing. State that this is one definition, identify excess-cash/goodwill sensitivity, and do not invent missing components. Use a disclosed 25% normalized tax convention for the initial comparable series, clearly not an assertion of actual tax rates; show a GAAP effective-tax sensitivity only where meaningful. |
| Operating cash flow | TTM CFO in currency units for the audit, with CFO/average assets and CFO/revenue as modeling candidates. | Cash generated by operations; working-capital releases are not necessarily recurring growth. |
| Free cash flow | TTM CFO − total investment capex; scale by average assets or revenue for financial candidates. | Cash remaining after investment. This is levered CFO-based FCF, not unlevered FCFF. Acquisition payments and customer/grant funding require separate flags. FCF/market cap belongs to valuation. |
| Debt and leverage | Interest-bearing debt/common equity; debt/assets; net debt/positive operating EBITDA, with net debt = debt − cash. | Financing risk. Flag negative equity, nonpositive EBITDA and claim-definition differences; no infinite ratios. |
| Interest coverage | TTM EBIT / positive gross interest expense, with a consistent reported expense definition. | Ability to service debt from operating earnings; signed EBIT can identify coverage below zero. Missing interest expense is not zero. |
| Liquidity | Current assets/current liabilities; quick ratio = (cash + short-term investments + receivables)/current liabilities. | Near-term balance-sheet capacity. Use positive liabilities and aligned reporting dates. |
| Capex | TTM total capex; capex/revenue; capex/depreciation-and-amortization where comparable and positive. | Reinvestment demands and potential capacity expansion. Separate maintenance/growth spending only when disclosed. |
| Dividends | Trailing common cash dividends/positive common earnings; dividend yield = trailing split-consistent common dividends per share/current price. | Distribution policy and current cash return. Dividend yield is price-dependent: assign it to the valuation block for ablations, while payout ratio belongs to financial factors. Distinguish regular and special dividends. |
| Earnings surprise | (Actual reported EPS − last archived pre-release consensus EPS)/pre-release share price, using identical fiscal period and GAAP/adjusted basis. | New earnings information relative to recorded expectations. Prior-year EPS changes and guidance comparisons are distinct variables, not analyst surprises. |
| Estimate revisions | Change in archived consensus for an unchanged fiscal period/horizon over one month; percentage revision only with a meaningful positive base. | Changes in anticipated earnings. Separate true revision from rolling from one forecast year to another; record estimate count, age and basis. |

ROE, ROA, margins and leverage are economically and algebraically related. Include them in the registry and controlled comparisons, not automatically all together. This is particularly important because the earlier event study had nearly redundant EPS/margin updates dominated by ATI exceptional items.

## 5. Valuation factor catalogue: what investors paid at the forecast origin

Compute valuation with the price at origin `t` and accounting/expectation inputs actually available then. These variables must enter predictive tests explicitly; a broad value-style factor is not a substitute.

| Factor | Definition at origin `t` | Important treatment |
|---|---|---|
| Trailing P/E | Common market capitalization / TTM earnings available to common. | This is the primary consistent market-cap convention. Also show price/TTM diluted EPS where the rolling per-share basis is reconstructible. Explain differences rather than mixing conventions. Nonpositive/near-zero earnings make P/E invalid. |
| Forward P/E | Current price / archived next-12-month consensus diluted EPS. | Requires historical consensus with a stated horizon. A next-fiscal-year P/E is a separate measure; do not silently substitute it. |
| P/B | Common market capitalization / latest available common book equity. | Require positive comparable common equity. |
| P/S | Common market capitalization / TTM revenue. | Revenue pass-through and different capital structures limit interpretation. |
| EV/EBITDA | Reconciled enterprise value / positive TTM operating EBITDA. | Base operating EBITDA = operating income + compatible depreciation/amortization; reconciled adjusted EBITDA is a labeled alternative. |
| EV/Sales | Same enterprise value convention / TTM revenue. | Do not change enterprise-value definitions between multiples. |
| FCF yield | TTM CFO-based FCF / common market capitalization. | May be negative. Retain the sign; do not take logs of negative yields. |
| Earnings yield | TTM common earnings / common market capitalization. | May be negative and can be more usable than P/E near losses. For positive earnings it is the reciprocal of P/E; do not pretend the two are independent information. |
| Dividend yield | Trailing common dividends per share / price. | Defined in the financial catalogue; entered only once, in this block. |
| Historical relative valuation | Current valid log multiple minus the median of its own preceding 60 monthly observations; minimum 36 prior observations. For signed yields, use the current yield minus its trailing median. | Exclude the current observation from the reference window. Also report a trailing percentile. Never compute the reference distribution using future years. |
| Peer relative valuation | Current valid log multiple minus the same-date median log multiple of predefined comparable peers, excluding the subject company; yield differences for signed yields. | Peer eligibility and membership must be known at the origin. Require at least three valid comparable peers for a median-based feature; otherwise mark unavailable or explicitly descriptive. |

Define base EV as common equity market value + interest-bearing debt + preferred claims + noncontrolling interests − cash. Include finance leases consistently within debt and avoid double counting. If operating lease liabilities are added, adjust the earnings denominator consistently; otherwise exclude them from the base bridge and state the convention. Reconcile pension adjustments, investments, contingent claims, warrants and material dilution separately. No current balance sheet or later financing may be inserted into an earlier EV.

For loss firms, negative earnings/FCF yields can remain economically meaningful, whereas negative P/E or EV/EBITDA rankings generally do not. Publish missingness and denominator flags. Complete this historical bridge before claiming EV-based predictive evidence; it was deferred in the earlier implementation.

Use an economic peer map rather than treating these five companies as interchangeable. If peers are selected quantitatively, use financial characteristics known at the origin, exclude valuation and future returns from selection, and fit any scaling/clustering inside the training information set. Clustering is an optional peer-selection aid, not a prerequisite for the forecast experiment.

## 6. First-order transformations and lag definitions

For a feature `x` already aligned to information available at month `t`, distinguish:

```text
Level:                    x_t
First difference:         Delta x_t = x_t - x_(t-1)
Percentage change:        x_t / x_(t-1) - 1
Log change:               log(x_t) - log(x_(t-1)), only for positive levels
One-period lag:           x_(t-1)
Lagged first difference:  Delta x_(t-1) = x_(t-1) - x_(t-2)
```

A difference measures change; a lag measures an older value. For P/E moving from 20 to 22: the difference is +2 multiple points, percentage change is +10%, and the one-period lag is 20. For revenue growth moving from 10% to 15%, its first difference is **+5 percentage points**; that is growth acceleration, not 5% revenue growth.

For financial statements, maintain two explicit clocks:

- **Monthly as-known change:** the change between the values available at successive forecast origins. It can be zero when no new release occurred.
- **Release-to-release financial change:** the latest disclosed ratio/growth rate minus the corresponding value from the preceding fiscal quarter, using a comparable accounting basis. Carry the resulting latest update only after publication and record its age.

Do not label a one-month lag of a carried-forward ratio as a new independent quarterly observation. Preserve seasonality: quarter-on-quarter and year-on-year transformations answer different questions.

Test a bounded set of feature representations on identical origins: levels; eligible first differences; eligible percentage/log changes; and levels plus selected changes. Test extra monthly lag sets `{0}`, `{0,1}` and `{0,1,3}`, where zero means information available at the current forecast origin, not a future outcome-period realization. These are prespecified alternatives, not a search over every possible combination.

Important algebra: `x_t`, `x_(t-1)` and `Delta x_t` are exactly linearly dependent. Do not place all three in an unpenalized model. Even under regularization they are alternative parameterizations of overlapping information; do not claim a new independent signal just because their penalties produce different fits. Likewise, P/E and earnings yield, or operating margin and its numerator/denominator, can create strong redundancy.

Use percentage/log changes only for meaningful bases; avoid percentage changes in signed returns, near-zero yields, ROE crossing zero or negative profits. For rates, margins and spreads, differences in percentage points or basis points are usually the interpretable change. Store units explicitly.

Most importantly, a P/E change calculated **through origin `t`** may predict a later return. A P/E change calculated through `t+1` contains the target price and is forbidden as a predictor of that same return. The EPS/P/E accounting identity belongs in the separate explanatory appendix.

## 7. Market, industry and company-specific external drivers

### Broad market and financing conditions

Register these candidate inputs with actual source and availability dates:

- Broad market total return: SPY or a consistently defined broad US index.
- The return of an index containing the issuer, only with verified historical membership. Listing exchange alone does not establish membership. If unavailable, omit the membership-specific feature and retain the broad benchmark.
- Sector and industry index/ETF returns, with historical coverage and possible own-stock overlap disclosed.
- Market volatility: month-end VIX level and/or the previous month's realized SPY daily volatility. State that implied and realized volatility measure different things.
- Treasury rates: short and 10-year nominal yields, term spread, and 10-year real yield where obtainable; use levels and economically meaningful changes under the transformation policy.
- Credit conditions: a broad US high-yield option-adjusted spread and its change; retain exact series and units.
- Relevant FX rates: for example USD against an exposure-relevant currency, or a broad USD index where justified. Define quotation direction and distinguish revenue translation, input costs and debt exposure.
- Market momentum: cumulative SPY return over the preceding 3 and 12 months, ending at the forecast origin; distinguish these from the traded French momentum factor.

Use earlier-period market returns to predict later returns. Do not interpret their coefficients as the contemporaneous betas from the original report. Archived French market/style factors can be auxiliary controls where their historical availability is defensible; they do not replace issuer-level financial or valuation inputs.

### Economic mapping of external drivers

Create `exposure_map.csv` with:

```text
issuer, business_segment, exposure_start, exposure_end, evidence_date, source,
candidate_driver, exact_series, unit/currency, transmission_channel,
revenue_or_cost_exposure, possible_sign, pass_through/hedging,
release_lag, vintage_quality, feature_block, inclusion_status, omission_reason
```

Economic relevance must precede statistical selection. Record whether the driver influences demand, realized selling prices, input costs, financing, working capital or required returns. A metal-price rise can help sales while raising costs or working capital; do not impose a uniformly favorable coefficient. Current segment weights must not be projected backward. Use quantitative weights only when historically disclosed; otherwise retain qualitative mappings.

Candidate mapping for verification:

| Company | Candidate business drivers to verify | Main comparability issue |
|---|---|---|
| MTRN | Semiconductor production/equipment demand; aerospace/defense activity; relevant copper/precious-metal inputs; beryllium-specific supply/demand disclosures where measurable. | Gross metal-price pass-through can raise reported revenue without equivalent value-added profit. Do not invent a liquid beryllium price series. |
| ENTG | Semiconductor production and wafer-fabrication-equipment demand; process-material demand; relevant disclosed input/energy/FX exposures. | A semiconductor equity index and a physical demand series are different inputs. Memory spot prices are not automatically a valid proxy for all process-material demand. |
| CRS | Aerospace-engine demand/deliveries; relevant nickel/titanium/alloy inputs; surcharge mechanisms; disclosed energy exposure. | Timing of surcharge recovery, specialty mix and customer contracts can dominate spot-metal direction. |
| ATI | Aerospace/defense demand; relevant titanium/nickel/alloy inputs; industrial activity and disclosed energy exposure. | Business exits, restructuring and changes in mix make historical exposure time-dependent. |
| ELMT | Tungsten/molybdenum prices and supply indicators; semiconductor/defense demand; relevant energy costs and documented contracts/grants. | Short public history, financing changes and thin/proprietary commodity data constrain inference. |

For an expanded universe, apply the same mapping method: oil/gas prices for exposed energy companies; local electricity prices for exposed utilities or energy-intensive firms; freight/shipping rates for transport/logistics; and relevant agricultural commodities for agriculture-related issuers. These are conditional examples, not instructions to insert unrelated commodity series into every model.

Prefer original filings and investor releases for exposures, and primary exchange, government, central-bank, industry-body or index-provider data for series. Examples of candidate providers include SEC, Treasury/Federal Reserve/ALFRED, EIA, BLS/BEA/Federal Reserve production data, USGS, exchanges and relevant industry associations. Verify access, licensing, definition, publication lag and usable history; do not assume every desired series is freely available. Do not purchase data without authorization.

Keep sparse strategic disclosures in a dated event register. Do not manufacture continuous backlog, contract or policy variables from a selected collection of favorable headlines. Missing or economically unsuitable drivers remain excluded with reasons.

## 8. Candidate models and fair structural comparisons

Estimate the three families separately for each eligible established issuer. A pooled model with issuer intercepts may be a separately labeled sensitivity if data support common slopes, but four issuers are not a broad cross-sectional asset-pricing sample. Do not concatenate four issuers into one artificial time series for ARIMA estimation.

### Model 1: static factor regression

```text
y_(t+1) = intercept + beta' X_t + error_(t+1)
```

`X_t` contains eligible financial, valuation, transformation, market, industry and business-driver features available at `t`. Static means no separately modeled AR/MA error process. A selected feature may itself summarize a past change or trailing return.

Fit a small interpretable OLS specification and regularized Ridge, Lasso and Elastic Net candidates where appropriate. Scale predictors within training data and leave the intercept unpenalized. Tune penalties with chronological inner validation. Correlated ratios make Ridge/Elastic Net useful candidates; Lasso selections can be unstable, so selection frequency and group-level results matter. Never report ordinary post-selection OLS p-values as if the feature set had been fixed independently.

### Model 2: dynamic regression / ARIMAX

Use regression with ARMA errors as the primary, precisely stated implementation:

```text
y_(t+1) = intercept + beta' X_t + u_(t+1)
u_(t+1) = sum(phi_j * u_(t+1-j))
          + epsilon_(t+1) + sum(theta_k * epsilon_(t+1-k))
```

This asks whether recent unexplained outcomes/errors help forecast the next outcome after accounting for the same predictors. The MA terms concern past innovations, not moving averages of the explanatory variables. Treat `X` as supplied regressors, not as an MA process. “Exogenous” here describes the model input, not proof of causal independence.

For return targets, start with `d=0`. Candidate `(p,q)` orders are `(0,0)`, `(1,0)`, `(2,0)`, `(0,1)` and `(1,1)`. Include `(0,0)` so the data can prefer no dynamics. Do not add seasonal ARIMA or difference stationary returns by default. Any `d>0` or factor-process model requires a separately justified, frozen extension based on training-only evidence, with forecasts returned to the same target scale.

Use only filtered information available at the origin to update states/innovations; no future-smoothed states. Align the software's exogenous row for target month `s` to the features known at `s-1`. For a one-step forecast from `t`, pass `X_t`, not realized `X_(t+1)`. For multi-step forecasts, use a direct horizon-specific model or separately trained forecasts/scenarios of unknown future inputs; never feed their realized future path.

Report the exact equations implemented. Regression with ARMA errors and a model with lagged `y` plus `X` do not generally have identical coefficient interpretations or lag restrictions. This model is not a latent dynamic-factor extraction model unless a separate state-space factor model is explicitly introduced.

### Model 3: distributed-lag factor regression

```text
y_(t+1) = intercept + beta_0' X_t
          + sum(beta_l' X_(t-l), l in selected_lags) + error_(t+1)
```

Use the predefined lag sets `{0}`, `{0,1}` and `{0,1,3}` with Ridge/Elastic Net when the added lags make the model large. The primary version has no ARMA error structure. It asks whether older predictor observations add useful information beyond the latest available values. Keep lagged predictor effects distinct from differences and from autoregressive target dynamics.

### Compare information and model structure separately

Produce two explicit comparisons:

1. **Common-input comparison:** static, distributed-lag and ARIMAX models use the same compact base predictor set, source vintages, target observations and outer forecast origins. This isolates the value of added predictor lags or error dynamics. Select at most six base predictor columns inside training data using a fixed economic priority list or a nested, budget-limited selection rule. Require financial and valuation representation when testing the combined financial/valuation hypothesis. Refit any selection in each inner fold; the common selected base set at an origin is shared by the three families. Preserve eligible driver blocks in separate targeted ablations if the compact set cannot retain every block.
2. **Practical pipeline comparison:** a broader regularized static model and broader regularized distributed-lag model may use the full eligible catalogue; compare these with the feasible dynamic pipeline on matched origins. A difference here reflects the entire pipeline, including feature selection and complexity, and cannot be attributed solely to ARMA structure.

Within the common-input ARMA comparison, use the matching `(0,0)` regression with the same likelihood/intercept and exogenous-variable convention as the direct static baseline. Compare its nonzero-order versions without also changing its predictor set or penalty. Comparisons with a separately tuned Ridge baseline remain useful pipeline comparisons, but do not isolate ARMA structure alone.

Freeze the feature-budget rule and numeric penalty grids in configuration before scoring. A practical initial grid is 12 log-spaced penalty strengths per regularized estimator, Elastic Net mixing values `{0.2, 0.5, 0.8}`, and the listed lag/order candidates. Calibrate penalty scale using training-only standardized inputs/targets and record the objective-function convention. Do not expand the grid because the first results are weak.

For unpenalized OLS/ARIMAX, target at least ten training observations per estimated parameter, counting intercept, AR/MA terms and innovation variance where applicable; never fit below five. These are conservative workflow gates, not statistical guarantees. Label fits below the preferred threshold as limited-sample. Reduce predictor count or omit infeasible orders consistently rather than overriding a gate to obtain a result. Report convergence, stationarity/invertibility constraints, condition numbers and failures. A failed fit must not silently remove an unfavorable test month.

## 9. Expanding/rolling out-of-sample evaluation

### Outer evaluation

Use at least **84 completed monthly training targets** for the initial forecast and seek at least **36 one-month out-of-sample targets** for primary performance claims. These gates reflect the small dataset; they do not guarantee power. With complete 2016-onward data, the first target would be January 2023, subject to feature/lag availability. If the common eligible period cannot meet the gates, provide an explicitly exploratory comparison, reduce scope or acquire earlier point-in-time data; do not claim a robust winner.

Use an expanding window as primary and a fixed trailing 84-month rolling window as a declared sensitivity. Refit coefficients at each monthly origin. Use the same origins across models and blocks in each named comparison. ELMT is excluded from these primary fits because its history is far shorter than the gate.

### Inner selection

At every outer origin, choose transformations, penalties, permitted feature subsets, lag length and ARMA orders using only earlier data. Use the most recent 24 completed target months inside that outer training set as two consecutive 12-month inner validation blocks, with at least 60 earlier months available before the first block. At the initial 84-month origin, these are training months 1–60/validation 61–72 and training months 1–72/validation 73–84. Expanding-window origins extend the earlier training history; rolling-window origins use their preceding 84-month slice. Within a validation block, issue sequential one-step forecasts with only then-known information and already matured labels; keep candidate hyperparameters fixed for that block. Apply the label-maturity/purge rule as well; a secondary longer-horizon task may therefore require a later first eligible origin.

Use average inner squared error as the selection criterion. Favor the simpler candidate when differences fall within estimated inner uncertainty; record the tie rule. Do not use the outer test month to tune or select. Past outer outcomes may enter later training once genuinely observed under this fixed procedure, but must not be used to redesign the procedure after reviewing the leaderboard.

Put imputation, winsorization if justified, scaling, correlation pruning, selection, dimensionality reduction and any peer-selection algorithm inside the training pipeline. Fit none of these on the full sample. For optional sparse variables, use predefined eligibility thresholds and missingness/age indicators where meaningful. Do not fill an unavailable analyst estimate with zero or fabricate a financial value merely to retain a row. Preserve genuine extreme returns in evaluation.

### Label timing and overlap

Store feature-origin and target-end timestamps. A training label is eligible only when its entire target interval has ended by the fitting origin. For an `h`-month outcome, purge training origins whose labels extend into the validation/forecast information boundary; derive the required gap from timestamps rather than assuming ordinary time-series splits are sufficient. Use a conservative extra gap only if actual publication/implementation timing requires it, and document it.

Three-month overlapping outcomes require dependence-aware uncertainty and a non-overlapping-origin sensitivity. Never randomize rows, split each company independently into overlapping calendar train/test periods, or treat carried-forward statements as independent releases.

### Benchmarks and missing forecasts

Include zero return, the expanding historical mean, and a simple AR(1) estimated using the same available training outcomes. The principal out-of-sample R² benchmark is the expanding historical mean at each origin. For the risk task, include trailing realized variance as a persistence benchmark.

Declare a fallback to the origin's historical-mean forecast for failed return-model fits, record every failure and report both full operational performance including fallbacks and the matched successful-fit sensitivity. A failure cannot be counted as evidence of a dynamic-model improvement. Use an analogous positive persistence fallback for the risk target.

## 10. Required ablations and transformation comparisons

Assign every feature to one economic block and record dependencies. The requested cumulative sequence is:

| Stage | Added information |
|---|---|
| A0 | Historical-mean benchmark |
| A1 | Financial levels/growth/policy variables |
| A2 | A1 + company valuation levels and relative valuation |
| A3 | A2 + selected first-order transformations of financial and valuation variables |
| A4 | A3 + broad market, volatility, rates, credit, FX and market momentum |
| A5 | A4 + sector/industry returns and industry-demand indicators |
| A6 | A5 + company-relevant commodity/input-cost/business-driver variables |

Complete the full sequence with the broad regularized static pipeline. Repeat on the feasible common-input comparison for all three model families and explicitly report any omitted block/model combination. Do not claim every requested variable was tested merely because its category appears in a table.

This sequence is order-dependent. Also require:

- Market/industry controls alone versus those controls plus financials, then valuations.
- Full model minus financial variables, and full model minus valuation variables.
- Full model minus each other eligible economic block, retaining identical target dates.
- Levels versus differences versus eligible percentage/log changes versus levels-plus-changes, using the same underlying eligible variables and observations.
- Added predictor lags versus no extra lags; ARMA dynamics versus `(0,0)`, with the same base inputs.

When removing a block, remove its derivatives, lags and any interaction depending on it. Otherwise a purported no-valuation model could still contain lagged earnings yield. At A3, transformations refer to the financial/valuation variables already introduced; later blocks enter with their predefined economically meaningful representations, such as market returns and yield changes. A separate full-model transformation comparison tests broader alternatives. Do not mislabel a commodity return as an untransformed spot-price level.

Use matched dates for the two sides of every ablation. Report full-coverage performance separately from the common-sample comparison when optional consensus/EV/commodity inputs reduce history. Retrain and retune both sides inside the same inner folds. Report the change in out-of-sample loss, its uncertainty, coverage and complexity; increased in-sample R² alone is not incremental predictive value.

A small exploratory interaction study may test revenue/earnings improvement × beginning valuation, addressing whether comparable operating improvements receive different return responses at different initial prices. Define no more than two such interactions in advance, retain their main effects and respect the capacity gates. Label interactions as associations, not causal price responses.

## 11. Scoring, uncertainty and diagnostic checks

For each issuer, target, model and feature set, retain every dated forecast and calculate:

```text
error_t      = realized_t - forecast_t
RMSE         = sqrt(mean(error_t^2))
MAE          = mean(abs(error_t))
R2_OOS       = 1 - sum(error_model_t^2) / sum(error_benchmark_t^2)
directional_accuracy = mean(sign(forecast_t) == sign(realized_t))
```

Define a fixed zero/tie convention for directional accuracy and compare it with always-up and a training-only majority-direction benchmark. More than 50% accuracy is not automatically useful when positive months are common. Negative out-of-sample R² means the model lost to the stated benchmark. Do not replace the denominator with deviations from the future test-sample mean.

Report native return units, observations, forecast dates and benchmark. Show in-sample/adjusted R² only as fit diagnostics. For variance models, report RMSE/MAE on the original variance scale, a log-scale score separately, and optionally QLIKE with positive forecasts; do not mix variance and volatility losses.

Report each issuer separately. Any aggregate score must give issuers declared weights and also show a training-volatility-normalized comparison so the most volatile issuer does not silently determine the result. Resample the common calendar jointly across issuers; four issuers are not four independent macro histories or a reliable large-cluster sample.

### Uncertainty and multiple comparisons

Use 2,000 synchronized moving-block resamples of the out-of-sample forecast/loss records, seed `20260918`, initially with six-month blocks and three-/twelve-month sensitivities. Preserve paired model forecasts and cross-company dates. Report intervals for mean loss differences and key metrics. These intervals are conditional on the fitted evaluation procedure and observed history; they do not by themselves include all uncertainty from discovering the protocol or selecting the companies.

If claiming a statistically significant forecast improvement, use an appropriate forecast-comparison procedure. Non-nested and nested comparisons can require different treatment; do not indiscriminately apply an ordinary independent-sample t-test or unadjusted Diebold–Mariano test to selected nested models. A suitable refit bootstrap or justified nested-model adjustment may be used, with assumptions and small-sample limitations stated. If reliable inference is infeasible, report the estimated loss difference and descriptive interval without a discovery claim.

Freeze four primary one-month-return contrasts per eligible established issuer: valuation added to otherwise identical full controls; selected transformations versus level representations; common-input ARIMAX versus static; and common-input distributed-lag versus static. If all four issuers qualify, this is a 16-comparison family. Apply Holm adjustment to any valid formal p-values in this family. All other horizons, targets, ablations and interactions are exploratory. Pointwise intervals are not simultaneous confidence statements.

### Regimes and stability

- Report calendar-year performance, rolling forecast bias/error and training-window sensitivity.
- Define high/low market-volatility regimes at each origin using its then-available VIX/realized-volatility value relative to a trailing historical median; require adequate prior history. Define rising/falling-rate regimes from a specified prior three-month yield change. Never choose regime cutoffs to maximize the apparent winner.
- If a regime has fewer than 12 forecast observations, retain descriptive results and mark the uncertainty; do not assert stable regime superiority.
- Inspect coefficient paths, signs, selection frequency, forecast sensitivity, AR/MA roots and convergence. Distinguish instability caused by collinear interchangeable variables from disappearance of an entire economic block's value.
- Diagnose residual autocorrelation, autocorrelation of squared errors and calibration using training data for model decisions. Outer residual diagnostics are reported after forecasts and cannot trigger retrospective retuning.
- Report factor correlations, scaled condition numbers and VIF for small unpenalized models. Check algebraic duplication before relying on regularization to hide it.
- Show largest-move and exceptional-accounting sensitivities with the untouched full sample primary. Do not delete jumps to improve scores.

### Information criteria

Record AIC = `-2 log-likelihood + 2k` and BIC = `-2 log-likelihood + k log(n)` for feasible likelihood-based time-series models, with `k` and effective sample/burn-in defined. Compare only compatible targets, scales, likelihood conventions and training observations. Do not rank regularized models with naive OLS AIC/BIC or compare a differenced-target likelihood directly with an incompatible levels likelihood.

AIC/BIC and training residual diagnostics can screen or break ties among time-series specifications. The final comparison is chronological out-of-sample loss and stability. Lower in-sample information criteria do not establish a better forecast.

## 12. Feasibility, implementation priorities and stop rules

Implement in this order:

1. Audit the old dataset; repair availability, financial denominator and security-claims issues needed for the new predictors.
2. Deliver the monthly as-known financial/valuation feature registry, exposure map and coverage report.
3. Freeze targets, core/optional features, model budgets, splits, grids, fallbacks and comparison families in configuration.
4. Build historical-mean/AR benchmarks and the static financial-plus-valuation model; verify all timing before comparing more models.
5. Implement the common-input distributed-lag and ARIMAX comparisons, then broad regularized candidates and the required ablations.
6. Add optional historical consensus, EV, industry-demand and commodity datasets where they materially expand a testable economic question. Run the separate variance target and secondary horizon within the declared budget.
7. Generate the report, audit the forecasts and preserve all failures/deferrals.

Every requested factor must be marked `implemented`, `unavailable`, `incomparable`, `sample-gated` or `redundant-with-tested-representation`, with evidence and reason. Data collection cost or statistical infeasibility can justify deferring a peripheral feature; lack of significance cannot. If company valuation variables cannot be built credibly, say the central revised experiment is incomplete rather than replacing them with HML and declaring success.

Prefer a credible smaller experiment to manufactured data. Do not expand to hundreds of indicators, arbitrary lag combinations, neural networks or a large trading-strategy search. Broader peer-universe collection can be proposed separately if cross-sectional comparisons remain underpowered; it does not magically lengthen MTRN's time series. Defer a task only with a concrete explanation of its expected analytical benefit and blocking limitation.

## 13. Required artifacts and verification

Write under `MTRN/experiments/financial_valuation_models/`:

```text
README.md
config.json
code/                         # separate retrieval, features, splits, models, scoring, reporting
data/raw/                     # only newly needed immutable source archives
data/processed/feature_registry.csv
data/processed/exposure_map.csv
data/processed/feature_availability_audit.csv
data/processed/monthly_features_as_known.csv
data/processed/targets.csv
data/processed/split_manifest.csv
data/processed/forecasts.csv
data/processed/model_scores.csv
data/processed/ablation_scores.csv
data/processed/parameter_paths.csv
data/processed/model_failures.csv
data/processed/coverage_and_deferrals.csv
data/processed/experiment_registry.csv
data/processed/metric_registry.csv
data/processed/figure_manifest.csv
data/processed/table_manifest.csv
sources/manifest.json
figures/                       # consistent publication-quality exports and figure source tables
final/Financial_Valuation_Model_Comparison.html
```

The forecast ledger must identify origin, target start/end, model/feature version, training interval, chosen transformation/penalty/order, forecast, actual, benchmark forecast, source cutoff and fallback status. Save train-fitted preprocessing parameters and selected features so each forecast is traceable.

Provide pinned dependencies, deterministic seeds, a separate download command and a single offline rebuild command. Check mathematically meaningful cases: first difference versus lag; absence of exact duplicate features; release-date joining; future-data perturbations leaving earlier features/forecasts unchanged; label purging; corporate actions and EPS/share alignment; EV/FCF identities; matched ablation dates; ARMA exogenous alignment; no future smoothed state; and benchmark/out-of-sample R² calculations. Verify that new outputs are reproducible and the frozen original files retain their hashes.

The report must explain features and models in ordinary financial language, with examples, and answer:

- Which company financial and valuation variables were actually tested?
- Did valuation improve performance beyond financials and common market conditions?
- Did changes, accelerations or lagged values help beyond levels?
- Did a model with error dynamics improve on a static model with the same information?
- Which findings persisted across origins, firms, regimes and reasonable timing/lag choices?
- Were improvements economically material relative to forecast error and uncertainty?
- What could not be tested, especially for ELMT or unavailable historical estimates?
- What do the results illuminate about the historical investment comparison, without equating predictability with intrinsic value or causal explanation?

Display out-of-sample forecast-versus-realization plots, cumulative paired forecast-loss differences, block-ablation charts, parameter paths and a compact coverage matrix. Do not turn a small p-value or the best point estimate among many models into an investment recommendation.

## 14. Required final judgment and expected model conditions

Recommend the simplest model supported by the out-of-sample evidence, or retain the benchmark if no candidate improves reliably. Explain these expectations as hypotheses to check:

- **Static factor model:** most appropriate when the latest financial/valuation state contains the useful information, residual serial dependence is weak, or the sample is too small for additional dynamic parameters. Regularization is especially relevant when many related ratios are available.
- **Distributed-lag model:** can help when economic effects arrive gradually or past disclosures contain information not captured by current levels. It can hurt when persistent/carried-forward fundamentals make lags almost redundant and estimation noise dominates.
- **ARIMAX/regression with ARMA errors:** can help when conditional residual dependence is stable and forecastable after the explanatory variables are included. It can hurt when returns have little remaining serial dependence, regimes shift, innovations cannot be estimated stably, or extra parameters overfit a short sample.

The recommended starting design is **nested expanding-window, one-month-ahead evaluation of regularized financial-plus-valuation models, with a compact common-input comparison against distributed lags and ARMA errors**. Use the rolling-window and secondary-target analyses to assess robustness. Do not assume ARIMAX is superior because it is more elaborate, or that a plain factor model is superior because it is easier to interpret.

## 15. Continuation review and protection against omitted content

Before implementing or resuming work, review the actual persisted files rather than relying on a conversation summary or assuming the last displayed paragraph marks completion. Inspect the start and end of the protocol, code, report templates and generated report; identify incomplete blocks, placeholders, TODOs, partially written tables, broken links and missing sections. A transcript/tool-output truncation is not evidence that the file itself is truncated: reopen the specific omitted range.

Create a dated continuation audit recording:

1. Which protocol version and instructions govern the work, which files were read, and their hashes.
2. The last completed pipeline stage, validated outputs, uncompleted stages, running jobs if any, and the exact safe point from which to resume.
3. Every required variable family, model, transformation, assumption, target, sample period, comparison, metric, figure and report section, with its implementation/report location and status.
4. Existing results and limitations that must carry forward, including the old factor-data cutoff, point-in-time caveats, approximate EPS construction, deferred EV/ROIC/consensus inputs, ELMT exclusions and announcement-model collinearity/influence findings.
5. Missing or truncated content restored from authoritative files or reproducible outputs. If it cannot be recovered, identify the missing item and rerun only the necessary stage where feasible; do not invent an earlier result.

The existing historical study is a completed **different** experiment. Preserve its seven original figures and source/result tables as archived evidence. New predictive results require new figures and clear model/date labels. Do not relabel an old in-sample factor-fit chart as out-of-sample forecasting evidence. Reuse presentation components where appropriate, but reassess layout against section 17 rather than assuming the earlier formatting satisfies the new requirements.

Maintain a requirements-to-artifacts checklist throughout implementation. A section omitted for a justified data/sample limitation must remain visible as an explicit deferral and must not disappear from the report's scope statement. Do not replace established outputs unnecessarily merely because the conversation resumed.

## 16. Research-report structure and experiment-by-experiment explanation

The final report must let a reader follow the entire chain from motivation and data construction to evidence and conclusion. A collection of scores followed by a verdict is insufficient. Use the existing standalone HTML/source-link structure, with an accessible contents list, linked appendices and reproducible tables.

### Required report order

1. **Purpose, motivation and scope:** explain the historical investment/modeling question, prior study, the change introduced by this protocol, information cutoff and limits of the population studied. A brief orientation may describe the design; reserve the substantive model-selection conclusion for after the evidence.
2. **Data and information timeline:** sources, security identities, as-known dates, accounting reconciliation, sample coverage, missingness, exclusions and the distinction between available financial history and public return history.
3. **Variable construction and economic mechanisms:** readable category-level explanation and the complete variable dictionary described below.
4. **Common evaluation design:** targets, forecast origins/horizons, training/inner-validation/outer-testing chronology, baselines, model families, preprocessing, tuning, availability/overlap rules and metric definitions.
5. **Major experiments:** give each the full research-question-to-conclusion sequence below, with results and figures located beside the interpretation.
6. **Cross-experiment synthesis:** compare the evidence from factor additions, transformations, lagged effects and ARMA dynamics. Reconcile disagreements across metrics, horizons, issuers or regimes before drawing the overall conclusion.
7. **Overall conclusion:** state which questions the evidence answers, what remains uncertain and what it means for historical financial/valuation comparisons. Distinguish predictive evidence from claims of intrinsic value or causation.
8. **Limitations and further research:** sample size, observed-history selection, survivorship, look-ahead/data-vintage risk, missing data, multicollinearity, structural changes, regime dependence, overfitting and model instability; prioritize follow-ups by the uncertainty they could resolve.
9. **Reproducibility and appendices:** exact configuration, full variable/metric registries, all eligible model results, exclusions/failures, forecast/source ledgers, code/environment references and continuation/consistency audits.

### Major experiment registry

Use stable experiment IDs so tables, figures, tests and conclusions can be traced. The following questions are required wherever eligible data permit:

| ID | Research question | Intended test / motivation |
|---|---|---|
| E1 | Do company financial characteristics add predictive information beyond simple return benchmarks and common market conditions? | Test whether disclosed operating/cash-flow/balance-sheet information adds information beyond general price movements. |
| E2 | Does starting valuation add information beyond the same financial and external controls? | Test whether what investors paid matters separately from operating performance; include relative valuation only where a credible historical/peer reference exists. |
| E3 | Do first differences, percentage changes or changes in growth rates improve on factor levels? | Test financial/valuation dynamics on matched dates, recognizing equivalent parameterizations and invalid denominator cases. |
| E4 | Do market, industry and relevant commodity/business drivers add value beyond financial and valuation variables? | Distinguish broad conditions from specific economic exposures; include the full ordered ablation and leave-one-block-out checks. |
| E5 | Do older predictor observations improve forecasts beyond the latest information? | Compare static and distributed-lag models on the same base inputs and test sensitivity to lag length. |
| E6 | Does a forecastable AR/MA error process improve on a static model using the same information? | Test the need for additional target/error dynamics rather than assuming a more complex time-series model is superior. |
| E7 | Do the main comparisons remain stable across forecast horizons, training windows and market regimes? | Examine whether apparent improvement depends on one horizon, period or market state. |
| E8 | Can the same information improve a separately defined forecast of realized variance? | Secondary first/second-moment extension; do not confuse it with improvement in mean-return prediction. |

These questions organize overlapping comparisons rather than require duplicate fits. Link each ID to the relevant predefined statistical comparison family. Eligibility failure yields a documented unanswered question, not a silently omitted experiment.

### Mandatory sequence inside every major experiment

**A. Research question and motivation.** State one answerable question in ordinary financial language. Explain why it matters, what information source or modeling assumption is being tested, and the predeclared comparison that could support or fail to support it. Do not rewrite the hypothesis to match the observed winner.

**B. Reproducible setup.** Include an experiment specification table showing:

- Target and units; dependent-variable construction and forecast horizon.
- Predictors, controls and economic blocks; exact selected variables and their registry IDs.
- Levels, differences, percentage changes, lags and interaction terms; specify the lag clock.
- Exact first/last training, inner-validation and outer-test dates; number of origins and matured labels.
- Expanding or rolling window, window length, refit/tuning schedule and overlap/purge rules.
- Model equation, estimator, regularization/order/lag grid, capacity restrictions and realized choices.
- Baseline and comparison models; what is held fixed and what changes.
- Preprocessing, outlier policy, missingness rules, scaling, feature-selection procedure and where each is fitted.
- Relevant sources, availability rules, sample exclusions, fallback behavior and links to configuration/split manifests.

Readers must be able to reproduce the experiment without inferring missing settings from the graphs. Put bulky date-by-date hyperparameter histories in a linked table, with an informative summary in the main report.

**C. Variables and mechanism.** Explain the important variables actually used in this experiment, referring to the shared dictionary for complete formulas. Explain why each is relevant to the issuer or control group, what a positive/negative change means, and why the economic sign may be ambiguous. A plausible mechanism is motivation, not evidence that the estimated coefficient is causal.

**D. Evaluation criteria.** Define the primary and secondary scores and what would count as a better result. Explain the benchmark, uncertainty, multiplicity treatment and any minimum evidence requirement before presenting outcomes. Do not determine success using whichever metric happens to favor a model afterward.

**E. Results.** Show baseline and all eligible prespecified comparison families, not only the best model. Include matched-sample counts, metrics, uncertainty, convergence/fallback counts and incremental score changes. Present unsuccessful ablations and null results with the same visibility as improvements. Preserve the full candidate/selection record in the appendix; selected-pipeline performance must be distinguished from individual tuned candidates.

**F. Figures and diagnostics.** Introduce each numbered figure in the text, explain the question it answers and discuss its relevant pattern. Quantitative results must support any statement about a visible difference. Explain why a diagnostic is included—for example, residual ACF asks whether unexplained serial dependence remains; coefficient paths ask whether the fitted relationship is stable.

**G. Interpretation.** Discuss which information helped, which did not, whether older observations or AR/MA dynamics mattered, and whether differences are economically material relative to forecast uncertainty. Investigate plausible explanations such as redundancy, sparse disclosure updates, measurement noise, regime changes or omitted expectations. Label explanations as supported diagnostics or hypotheses. Reconcile tables and graphs and disclose metric disagreements rather than forcing a single ranking.

**H. Experiment conclusion.** Only after its setup, results and interpretation, answer the research question directly. State what the data support, what they do not establish, which specification differs under which conditions, and whether the estimated improvement is precise enough to support a superiority claim. A valid answer is that added information or dynamics did not improve reliably.

**I. Limitations and next test.** Identify the limitations specific to that comparison and a focused next test, if useful. Separate a missing dataset from a well-measured null result and from a result with a wide interval. Do not propose more complexity merely to obtain significance.

### Complete variable dictionary

For every implemented factor and transformation, record: reader-facing name; internal ID; category; meaning; exact formula; numerator/denominator conventions; units; native observation frequency; release/update frequency; forecast-table frequency; source and availability rule; reason for inclusion; hypothesized financial mechanism and possible sign; level/difference/change/lag form; lag length and clock; scaling method and training window; validity/missingness handling; companies exposed; and experiments using it.

Explain the core variables in the main text with small numerical examples and put the full registry in an appendix. Do not show only identifiers such as `rev_yoy_d1_z`. Use “Change in year-over-year revenue growth, percentage points” and explain how the variable was standardized if applicable. Industry/commodity explanations must connect the specific issuer's revenues, costs, contracts or capital needs to the selected series.

### Complete metric dictionary and balanced judgment

Use a common registry for formulas, units, benchmark, interpretation, preferred direction and caveats:

| Criterion | Reader-facing interpretation | Preferred direction / caution |
|---|---|---|
| RMSE | Typical forecast-error size with extra weight on large misses; in the target's units. | Lower; primary return-model selection score, but sensitive to unusually large moves. |
| MAE | Average absolute forecast miss, in the target's units. | Lower; checks whether an RMSE gain also reflects improvement outside the largest errors. |
| Out-of-sample R² | Proportional reduction in total squared error relative to the stated real-time benchmark. | Higher; negative means worse than that benchmark, and zero means equal total squared error. |
| Directional accuracy | Fraction of correctly forecast signs under the fixed tie rule. | Higher relative to relevant directional baselines; ignores error magnitude. |
| AIC/BIC | Training likelihood adjusted for parameter count under compatible likelihood/data definitions. | Lower within a valid comparison; not an out-of-sample performance score. |
| Forecast stability | Bias and loss across time windows, regimes and refits; counts of extreme forecast shifts/fallbacks. | Prefer reliable performance; a stable but consistently inaccurate forecast is not successful. |
| Parameter stability | Coefficient/sign/selection paths and AR/MA behavior across training origins. | Changes require interpretation; correlated features can exchange coefficients without changing forecasts. |
| Incremental value | Paired out-of-sample loss change when a feature block or model component is added. | Define the sign explicitly. Use `loss_reduced − loss_expanded` so positive means improvement, with an uncertainty interval. |
| Horizon robustness | Whether the answer persists at the predefined one- and three-month horizons. | Evaluate each target on its own scale and eligible dates; larger-horizon returns are not directly comparable in magnitude. |

The conclusion must integrate the primary score, secondary scores, uncertainty, stability and data quality. For example, an RMSE gain alongside worse MAE may be concentrated in a few large moves; better directional accuracy with worse RMSE may reflect small correct calls and large incorrect ones. Describe that tradeoff rather than calling one model unconditionally better.

## 17. Professional figure and table specification

### Central style and model naming

Implement one reusable plotting theme and one model-label/style registry; do not rely on plotting-library defaults. Use a restrained accessible palette, readable fonts, consistent sizes/margins and unobtrusive gridlines. Avoid 3-D effects, gradients, shadows and decorative elements without analytical purpose. Export standalone SVG/PDF or high-resolution PNG figures suitable for sharing, and embed readable copies in the standalone HTML report.

Use a stable illustrative encoding: observed outcomes in black solid lines; historical-mean baseline in gray dashed lines; static regression in blue solid lines; distributed-lag regression in orange dashed lines; ARIMAX in purple dash-dot lines. Also use markers or line styles where needed for grayscale accessibility. Distinguish regularization variants with explicit names or separate panels, not an unexplained color change. Freeze the actual mapping before generating final figures and apply it consistently across report and appendices.

Use reader-facing model names, for example “Static regression — Ridge” and “Dynamic regression — ARMA(1,1) errors.” Do not present a selected family as having a fixed order if its order changes by origin; label it “Dynamic regression — order selected in training” and provide the order history. Keep the comparison order consistent: benchmark, static, distributed-lag, dynamic, with declared subordering for variants.

### Every figure must stand on its own

- A descriptive title stating the quantity/comparison, with a subtitle when useful for issuer, dates, model, sample or horizon.
- Clearly labeled axes and units: percentage points, %, USD, variance units, index level, log change or score as appropriate. Show log scales explicitly. Avoid unnecessary decimal places and ambiguous “return” labels.
- A legend whenever multiple models, firms, factors or series appear, placed where it does not obscure evidence. Use meaningful names consistently with tables and prose.
- Legible scales and ticks; disclose rebasing or standardization. Bar lengths normally require a zero baseline. Other axis limits must not exaggerate forecast differences, and comparable panels should share scales when practical.
- A sequential figure number and an informative caption identifying what is shown, the sample, horizon, models/variables, transformations, normalization, uncertainty method and the point to notice. Captions must add interpretation and qualifications, not merely repeat the title.
- A source-data link and a manifest record identifying the experiment, exact input table/columns, plotting configuration and artifact path.

Place figures near their analysis. Refer to each figure explicitly in the text and discuss it; do not insert unexplained charts. Number in report order, update cross-references automatically and verify there are no missing or duplicated numbers.

### Time series and actual-versus-forecast figures

Time runs left to right. Show the forecasting horizon and distinguish actual observations from forecasts and in-sample fits. Include a train/validation/test timeline diagram, with representative expanding/rolling folds and the label-purging boundary. Where boundaries matter on a time-series chart, use light shading or reference lines with a legend. Do not imply one fixed training split if the underlying procedure refits each month.

Do not connect lines across missing observations or absent forecasts. Identify fallbacks and gaps. For equivalent company/model panels, use matching axes where practical; if a volatile issuer requires another scale, label the difference prominently. To avoid clutter, use small multiples or a predeclared focal set of models, retaining complete scores elsewhere.

Display prediction intervals only when actually estimated using an appropriate training-only procedure. State whether a band is an interval for the conditional mean, an individual future outcome, a parameter or a performance statistic; these are not interchangeable. Report nominal level and empirical out-of-sample coverage where applicable. Do not fabricate bands from the variation of fitted values or silently use all future residuals to calibrate earlier predictions.

### Model-comparison and ablation figures

Use horizontal dot/bar charts or clearly labeled small multiples for scores, preserving model order across related charts. State “lower is better” for RMSE/MAE and “higher is better” for out-of-sample R²/directional accuracy. Mark the benchmark and relevant reference lines, including zero for R² and zero for incremental improvement. Show uncertainty when available and identify matched dates/sample sizes.

For ablations retain the sequence **Baseline → Financial → Valuation → First-order transformations → Market → Industry → Commodity/business drivers**. Show absolute performance and, where useful, a companion plot of the incremental paired change. Use the same sign convention as the metric registry: positive loss reduction means improvement. Display a missing/ineligible block as missing, not a zero gain or a connected successful result. Do not imply the ordering uniquely allocates shared predictive information; discuss the leave-one-block-out and market-first checks.

When plotting several horizons, use consistent panels/markers and state the horizon-specific sample. Do not combine differently scaled targets into an unlabeled ranking. A “best model” highlight must be supported by the declared quantitative selection procedure, not chosen because its line looks attractive.

### Factor effects and importance

Name the model, training origin/window and definition of importance. For OLS, show compatible-unit effects or standardized coefficients with correctly described uncertainty. For regularized models, describe coefficient magnitudes as shrinkage-dependent conditional associations, not causal importance or ordinary unbiased effect estimates. A coefficient path or selection-frequency plot may be more honest than unsupported significance bars.

Do not compare raw coefficients for variables measured in different units. If reporting an effect per one training-standard-deviation change, specify the training scaler and target units. Across origins, either convert effects back to consistent economic units or explain that the scaling changes. Separate positive and negative effects around a zero line.

Prefer refitted block-ablation loss changes for predictive importance of economic groups. Do not use ordinary random row permutation that destroys time dependence and then interpret the result as a reliable financial importance estimate. Show a readable subset chosen by an explicit rule, and retain the full coefficient/feature table in the appendix. Do not select just statistically significant coefficients for display without showing the selection rule and omitted results.

### Company/industry-driver figures

State which factor corresponds to which issuer and explain its revenue/cost/demand channel. Do not place unrelated USD prices, percentage returns and ratios on one common axis. Prefer aligned panels or clearly labeled rebased indices for different units. Avoid dual y-axes; if necessary, label both scales and explain why their use is appropriate and why the apparent co-movement should not be overinterpreted.

### Diagnostics, rolling performance and regimes

Select diagnostics to answer a stated question: residual time series for time-varying bias; residual histograms for the distribution of forecast errors; ACF/PACF for remaining serial dependence; actual-versus-predicted scatter with an equality line for calibration; forecast-error charts for large misses; and coefficient paths for model stability. State whether residuals are training residuals or out-of-sample forecast errors. A visually suggestive diagnostic is not a causal test or proof of forecastability.

Residual distribution plots do not reintroduce excluded skewness/kurtosis estimation or investor-motive claims. Do not reproduce unrelated higher-moment output merely because a library summary prints it.

Use a declared 12-month window for primary rolling loss/bias displays, require complete eligible observations or show the effective count, and give the window length in the title/caption. Use the same time axis and score definition across models. Explain that overlapping rolling estimates are dependent. Regime shading must use the previously defined origin-available volatility/rate rules; document them in captions instead of assigning favorable regimes after seeing performance.

### Figure selection and minimum useful inventory

Choose chart type by question: lines for chronology; dot/bar charts for model scores; scatterplots for continuous-variable relationships; coefficient plots for estimated conditional effects; rolling plots for temporal stability; and heatmaps for large comparison grids. A heatmap must identify units, missing cells, its color scale and reference point. Do not use one chart type for everything or create figures only to increase the count.

The useful inventory normally includes: information/split timeline; data coverage; matched model-score comparison; focal actual-versus-forecast panels; ordered ablation and incremental-loss plots; cumulative paired forecast-loss differences; lag/order sensitivity; and a compact stability/diagnostic set. Add driver/financial relationships only when they clarify an experiment. Each figure must link to a research question and a discussion paragraph. Combine redundant plots into readable panels rather than omitting distinct required comparisons.

### Tables

Use the same names, units, ordering, horizon and date definitions as figures. Show sample counts, uncertainty and missingness legends. Identify whether a score belongs to a selected pipeline, fixed candidate, common-input comparison or broader practical-pipeline comparison. Keep exact numbers in machine-readable files; use consistent appropriate rounding in the report. Indicate economically small or statistically uncertain differences explicitly rather than assigning an unsupported definitive rank.

## 18. End-to-end consistency and completion audit

Before finalizing, run automated checks where possible and a visual/narrative review:

1. **Requirements completeness:** every requested factor category, model comparison, transformation, evaluation criterion and report component appears in the implementation/report matrix with an output or an explicit justified deferral. Check resumed or previously cut-down sections against full source files.
2. **Terminology:** variable IDs, readable names, definitions, units, transformations and lag clocks agree across code, registries, prose, tables, captions, legends and axes. Model family/estimator/order labels agree with the saved fit records.
3. **Time and sample:** cutoff, actual feature availability, target endpoints, training/validation/testing dates, forecast horizon and effective counts agree everywhere. Validate missing-month handling and identical dates for comparative tables/figures. Clearly distinguish the old July factor endpoint from new raw-return target coverage.
4. **Numerical traceability:** regenerate table/figure values from saved result files. Every quoted score, gain, interval, sample size, alpha or variance refers to the correct experiment and units. Never manually copy an old result into a new model's column. Validate incremental-improvement signs and R² baselines.
5. **Figures:** each required artifact exists, decodes/renders, has readable title/axes/units/legend, follows the style registry, has a unique number and caption, is referred to in the text and uses the intended source data. Inspect the actual rendered HTML and exported figures for clipping, unreadable fonts, overlapping legends, missing minus signs, broken images and truncated captions. Verify grayscale/line-style distinctions.
6. **Evidence-to-conclusion consistency:** each experiment conclusion directly answers its research question and follows its setup/results/interpretation. Claims of improvement identify quantitative paired evidence and uncertainty. Reconcile countervailing MAE, RMSE, direction, regime or horizon results. A graph's appearance alone never determines the conclusion.
7. **Scientific scope:** forecast results, contemporaneous associations, accounting identities, in-sample fit and out-of-sample evidence are labeled correctly. Causal, intrinsic-value or investor-motive claims do not exceed the design. Correctly distinguish estimated zero effect from an imprecisely measured effect.
8. **Reproducibility and preservation:** the offline build, timing/mathematical checks and saved forecast ledger reproduce the new report; original artifacts retain their hashes. Archive configuration, source versions and all model failures/deferrals.
9. **Honest completion:** no placeholder findings, fabricated metrics, empty result panels disguised as completed experiments or hidden omissions remain. If a required experiment is infeasible, explain what was attempted, why it failed, what evidence is still available and what additional data would make it testable.

Save the completion audit alongside the report. Report clearly what was implemented, what was tested, what was learned and what remains untested.

## Method references to verify during implementation

Use these primary documentation sources for implementation details, while keeping this protocol's information-timing and financial definitions authoritative for this experiment:

- [Statsmodels regression with SARIMA errors](https://www.statsmodels.org/stable/examples/notebooks/generated/statespace_sarimax_stata.html#ARIMA-Example-4:-ARMAX-(Friedman)): distinguishes regressors from the ARMA error process.
- [Statsmodels SARIMAX API](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAX.html): verify order, exogenous-input, trend and state-space conventions against the pinned version.
- [Scikit-learn chronological splitting](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html): expanding/rolling splits and a gap parameter; actual label-release timing still requires explicit auditing.
- [Scikit-learn preprocessing leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html): fit preprocessing on training data and apply it to later observations.
- [Scikit-learn regularized linear models](https://scikit-learn.org/stable/modules/linear_model.html): Ridge, Lasso and Elastic Net objectives and implementations. Supply chronological inner splits explicitly rather than accepting inappropriate default cross-validation.
