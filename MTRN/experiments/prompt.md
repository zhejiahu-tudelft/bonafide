# Historical attribution experiment: operating performance, repricing, and the first two return moments

**Universe:** Materion (MTRN), Entegris (ENTG), Carpenter Technology (CRS), ATI (ATI), and The Elmet Group (ELMT).

**Design date:** September 19, 2026. **Scope revised:** September 20, 2026. **Information and market cutoff:** September 18, 2026, US market close.

**Purpose:** Explain differences in past shareholder returns and risk, emphasizing estimation of the first moment (mean return) and second central moment (return variance), with volatility as the square root of variance. This is a retrospective observational study, not a forecast, trading strategy, price-target exercise, or identification of investor motives. Covariance, correlation and beta provide related measures of joint variation.

## 1. Role and research question

Act as an equity analyst and empirical-finance researcher. Execute one integrated historical attribution study using the protocol below. Collect evidence, write and run reproducible Python, validate the results, and produce a readable research artifact. Explain methods in ordinary financial language.

Investigate:

> How do these companies differ in historical mean returns and return variance, and how do those differences relate to disclosed operating performance, valuation multiples, common market/industry/macro exposures, and identifiable company news? How much mean excess return and return variance remains unexplained conditional on the chosen models, and how uncertain are those estimates?

Use four connected views of the same history:

1. **Accounting bridge:** How much of the observed price change mechanically accompanies changes in earnings per share and valuation multiples?
2. **Return-risk model:** How do common exposures relate to mean excess returns and return variance?
3. **Disclosure-event analysis:** Do newly disclosed financial changes and strategic developments coincide with abnormal returns, and what is the average event response with uncertainty?
4. **Moment estimation:** What are the raw and unexplained mean returns, variances, volatilities, covariances and their confidence intervals on matched samples?

These are complementary views, not mutually exclusive slices of one pie. Never add their percentages together into a supposed causal attribution totaling 100%.

Treat financial multiples as computed valuation measures. Distinguish company characteristics, such as margins or leverage, from traded factor returns, such as market, value, or momentum. A profitability factor is not the same thing as the company's reported profitability.

## 2. Interpretation rules and hypotheses

The central restriction is to interpret unexplained returns and variance **conditional on the specified model**. A residual can reflect omitted future cash-flow news, changing required returns, model instability, measurement error, liquidity, and unobserved risks. A multiple expansion can reflect rational expectations of future profits. Do not infer investor identity or motivation from aggregate prices and volume. Behavioral-proxy analyses and higher-order moment estimation are outside this experiment's scope.

Freeze the following hypotheses and specifications before fitting the new models:

* H1: The companies differ in the balance between disclosed per-share earnings growth and multiple repricing in their historical price changes.
* H2: Differences in market, style, industry, and macro sensitivities are associated with differences in mean excess returns and return variance, but do not necessarily explain cumulative appreciation.
* H3: Financial announcements and separately documented strategic events coincide with economically meaningful abnormal returns; average announcement responses can be estimated with uncertainty.
* H4: Differences in mean excess returns and unexplained variance across companies can be estimated on matched samples, although their confidence intervals may be too wide to support a stable ranking.

The existing MTRN report and notable price moves have already been reviewed. This is therefore an analysis plan fixed before the new regressions, not a claim of a previously unseen or formally preregistered sample. Record subsequent specification changes and their reasons. An inconclusive result is acceptable.

## 3. Universe, dates, and ELMT treatment

Verify each issuer's legal identity, CIK, exchange, ticker history, corporate actions, reporting currency, and business mix from original disclosures. These companies overlap in selected materials and end markets; they are not interchangeable businesses. Do not estimate a general asset-pricing premium from five selected current firms or generalize their results to the whole market. The selection has survivorship and selection limitations.

Use two explicitly labeled panels:

* **Established-company panel:** MTRN, ENTG, CRS, ATI; January 2016 through the cutoff where comparable data exist. Retrieve earlier prices and financial disclosures only as needed for prior-period comparisons and estimation warm-up.
* **Matched five-company panel:** Start at ELMT's first verified public closing price and end September 18, 2026. Compute comparable close-to-close returns from that common starting close. Compare all five only over identical dates in this panel.

Elmet's April 24, 2026 company announcement states that Nasdaq trading began April 23, 2026. Verify this against the price series and prospectus. Do not splice private-company valuations, IPO offer prices, or a different security's history into ELMT's public return series. Show any offer-to-first-close return separately from an ordinary investor's close-to-close return.

ELMT has less than five months of public history at the cutoff. Include it in descriptive financial, matched-return, event, and capital-structure comparisons. Do not backfill a ten-year return history or estimate the full monthly factor model for it. At most, provide a clearly exploratory daily market-only or market-plus-one-industry sensitivity with at least 60 usable returns. If this gate fails, omit the regression. Report its sample mean and variance with short-history limitations. Do not annualize its short-period return into a headline CAGR or interpret its estimated mean and volatility as stable company attributes.

Monthly regressions use complete months only, ending no later than August 31, 2026, and earlier if factor data stop earlier. September-to-date belongs in the daily/event and descriptive panels. Never fill unavailable factor months with zero or extrapolate them. State each model's actual start, end, observations, and coverage.

The default long-window analysis is supplemented by a 2021-onward comparison where sample-size gates permit. These windows are fixed before examining new regression results.

## 4. Point-in-time data and audit trail

Read the existing `MTRN/README.md`, research artifact, code, and source log before using the cached data. Preserve the existing report and frozen inputs. Reuse shared utilities under `common/code` where appropriate.

The existing financial tables were selected using the report's final cutoff. They are **not automatically point-in-time datasets for every historical month**. Reconstruct historical availability from original releases and filing accessions; do not carry a 2026 restatement or recast backward into a 2018 information set.

For every financial or economic observation, retain:

* issuer/series, units, period start/end, fiscal/calendar basis;
* value, original source URL, accession or document identifier;
* earliest verified public release timestamp, timezone, and first usable trading session;
* original versus revised status, retrieval timestamp, transformation, and missing-data flag.

An earnings release can precede its 10-Q. Use the actual public disclosure date when verified. Otherwise use the later verified date and flag the limitation. Inspect timestamp conventions against the original document; do not blindly trust a timezone suffix. If only a date is known, use the next trading session as a conservative convention and check a wider event window.

Maintain distinct datasets for:

1. **As-known financials and macro releases**, used for valuation snapshots, event analysis, and time-aligned associations.
2. **Latest comparable/recast operating history available by the cutoff**, used only for clearly labeled retrospective business comparisons.

For macro data, prefer ALFRED vintages or archived original releases. A current revised series can be a labeled robustness comparison, not a substitute for what was then known. A raw month-over-month change is not a surprise unless an actual prior expectation is available.

Collect split-adjusted prices, dividends, total-return data or a documented adjusted-close proxy, volume, and shares. Verify major jumps against a second source and corporate actions. Avoid dividends counted twice. Keep shares and EPS on the same split basis as the price used in multiples. Missing returns are not zero returns.

Archive factor data and methodology versions, including any provider changes to return construction. Historical factor returns can be revised; label whether the vintage available at the cutoff was obtained. A later factor vintage may be used only as a separately identified retrospective sensitivity. No post-cutoff economic observations or events enter the main study.

## 5. Financial and operating dataset

Build quarterly histories, with annual and TTM summaries. Respect fiscal-year differences, unequal quarter lengths, 52/53-week years, and acquisitions. Derive discrete quarterly cash flows from cumulative filings correctly; never subtract incompatible vintages without reconciliation.

Use a focused dashboard rather than inserting every ratio into a regression:

| Dimension | Primary measures | Interpretation and controls |
|---|---|---|
| Growth | Revenue growth; organic growth where disclosed; value-added sales where available | Separate volume/mix, metal-price pass-through, FX, acquisitions and disposals |
| Profitability | Gross and operating margins; operating EBITDA; reconciled adjusted EBITDA | GAAP first; identify impairment, restructuring, quality costs and recurring exclusions |
| Shareholder earnings | GAAP EPS attributable to common holders; consistent adjusted EPS as sensitivity | Tax, interest, preferred claims, SBC and dilution can change EPS without operating growth |
| Cash conversion | CFO, total investment capex, FCF, FCF/net income, working capital | Include Materion's separately reported mine development; flag acquisitions, factoring and customer funding |
| Capital efficiency | ROIC with disclosed NOPAT and average invested-capital definitions | Show acquisition/goodwill sensitivity; do not invent missing components |
| Financing | Net debt, interest coverage, debt maturities, cash, leases, preferred securities and warrants | Debt-funded growth, refinancing and new claims affect common shareholders differently |
| Valuation | Trailing P/E, EV/operating EBITDA, FCF yield; P/S and P/B as secondary context | Use historical as-known denominators and contemporaneous prices; mark invalid/negative denominators |

For MTRN, analyze value-added sales and gross revenue separately. Do not manufacture equivalent value-added measures for peers that do not disclose them. Likewise, do not directly compare an EBITDA/VA margin with another company's EBITDA/revenue margin as if they used the same denominator.

Construct an exposure map covering semiconductors, aerospace/defense, industrial demand, critical materials, and other material businesses. Use segment disclosures and their publication dates. Do not apply current segment weights to the distant past. Where quantified exposures are unavailable, use qualitative classifications rather than invented weights.

For ELMT, reconcile predecessor businesses, reorganizations, acquisitions, IPO proceeds, share issuance, and post-IPO financing. Historical private operating results can supply context, but do not create public-market return observations.

## 6. Industry and macro variables

Explain each variable's economic pathway before analyzing it:

`Industry/macro development → demand, pricing, costs or funding → cash flows/required returns → valuation.`

Use two complementary evidence types:

* **Traded exposure proxies:** Broad market and preselected semiconductor and aerospace/defense return benchmarks. Candidate ETF proxies are SOXX and ITA, subject to verifying history and suitability. Freeze choices based on business relevance and coverage, not regression fit. Compare identical proxies across the established-company models. Check constituent overlap and disclose material own-stock contamination; broad benchmark co-movement is not an exogenous causal effect.
* **Real-economy evidence:** Semiconductor demand/production, aerospace deliveries or orders, defense procurement, industrial production, relevant metal/input prices, and important trade/export-control changes. Use primary releases, record lags and revisions, and relate observations to the operating dashboard and event timeline. Do not convert monthly releases into hundreds of independent daily observations by forward-filling them.

For the primary macro regression block use monthly changes in the 10-year real Treasury yield and a broad US high-yield option-adjusted credit spread, in percentage points. Verify official/provider definitions and availability. Record missing real-yield history and source limitations. Use nominal Treasury changes as one declared sensitivity, not an additional search for a favorable result.

Do not automatically add CPI, GDP, PMI, oil, FX, every metal, and all interest-rate tenors to one regression. Add a material omitted input to a separate sensitivity only if the exposure map and data quality justify it. Do not use a broad commodity index as an undisclosed substitute for unavailable tungsten/beryllium price data. Explain overlap between industry returns, credit spreads, and common market risk.

## 7. Stage A — accounting bridge for historical repricing

Report total shareholder return separately from the following **price-return identity**. For endpoints with positive, meaningful TTM EPS:

```text
P = EPS × (P/E)
Δlog(P) = Δlog(EPS) + Δlog(P/E)
```

Use as-known trailing EPS at each endpoint, compatible split adjustments, and an explicit definition of TTM EPS. Show start/end price, EPS, multiple, dates and exact reconciliation. Use log-return contributions, labeled in log points; do not treat them as additive simple-return percentages. Report the dividend/reinvestment difference between the total-return and price-return series separately, without casually adding dividend yield to a compounded result.

Build bridges for the long period, 2021-onward, 2026 year-to-date, and the shared ELMT period where denominators are valid. Explain how share-count changes, taxes, interest and exceptional items affect EPS. Market capitalization requires actual shares; weighted-average diluted shares belong to EPS. Do not interchange them.

If EPS is negative, near zero, or materially incomparable, mark the P/E bridge not meaningful. Provide an enterprise-value bridge using positive, comparable operating EBITDA if available, and reconcile EV to common equity through net debt, leases, preferred claims, minority interests and dilution. Keep the claims convention fixed and explicit. Use a dollar bridge when logs are invalid. Do not force a sales multiple to stand in for missing earnings without explaining the weaker economic interpretation.

An endpoint identity does not prove that earnings caused that fraction of appreciation. Price can anticipate future earnings, and a rerating can represent fundamental news. Never regress contemporaneous stock returns on changes in P/E and present the resulting fit as independent explanatory evidence: price appears on both sides.

## 8. Stage B — parsimonious common-exposure models

For each established company estimate monthly OLS models of arithmetic total return minus the corresponding monthly risk-free return:

```text
M0: r_i,t − rf_t = α_i + β_m,i MKT_t + ε_i,t
M1: M0 + SMB_t + HML_t + MOM_t
M2: M1 + semiconductor benchmark excess return_t
       + aerospace/defense benchmark excess return_t
M3: M2 + Δ10-year real yield_t + Δhigh-yield credit spread_t
```

Use consistent US factors from the Kenneth French Data Library. Explain market, size, value and momentum as return exposures without assigning investor motives to them. FF5 plus momentum is a declared alternative to M1, not an excuse to keep adding correlated controls indefinitely.

Use the same complete-case observations for nested model comparisons. Minimum sample size is `max(60 months, 10 × number of estimated parameters including intercept)`. These are pragmatic gates, not guarantees of statistical power. If a richer model fails the gate, report that fact and retain eligible simpler models.

For each eligible model report coefficients in interpretable units, confidence intervals, mean excess return, alpha, mean fitted factor contributions, adjusted R², explained and residual variance, residual volatility, observations, factor correlations and condition diagnostics. Use heteroskedasticity/autocorrelation-consistent uncertainty, initially Newey–West with three monthly lags; show sensitivity if conclusions depend on it. Do not rely on homoskedastic normal-error p-values.

Compare incremental fit by **blocks**, and reverse the industry/macro entry order as a prespecified check. Correlated blocks have shared explanatory variation: do not assert a unique independent percentage for each. Avoid coefficient rankings when multicollinearity makes signs or magnitudes unstable.

Critical interpretation checks:

* R² measures variation in monthly returns, not the fraction of cumulative shareholder wealth caused by fundamentals.
* In-sample OLS with an intercept has residuals summing to approximately zero. Keep alpha separate; a near-zero cumulative residual is not evidence that all appreciation was explained.
* For the first moment, report `mean(excess return) = alpha + sum(beta × mean(factor))`. Alpha is the model's unexplained average excess return; the fitted residual mean is zero by construction and is not a separate estimate of investment performance.
* The identity `sum(excess returns) = T × alpha + sum(fitted factor contributions) + sum(residuals)` is arithmetic attribution, not compounded wealth attribution.
* A residual wealth curve obtained by compounding residuals is not an investable strategy and is not generally actual wealth minus benchmark wealth. Prefer clearly labeled residual-return or cumulative arithmetic abnormal-return plots.
* Factor covariances matter. Do not sum `beta² × factor variance` and call it total explained variance while omitting covariance terms.
* For an in-sample OLS variance decomposition with an intercept, use the same observations and denominator for total, fitted and residual sample variances. Verify `Var(excess return) = Var(fitted return) + Var(residual)` to numerical tolerance. Keep the degrees-of-freedom-adjusted residual error estimate `SSE / (N − p)` separately labeled; it does not belong in that exact sample decomposition.
* Monthly coefficients are not mechanically reusable for daily residual moments. Use a separately estimated daily market/industry model for daily diagnostics and name that model explicitly.

For full-period daily diagnostics, use a market-plus-the-two-industry-proxies model for established companies, with at least 252 daily observations; market-only is the declared sensitivity. Keep ELMT subject to its simpler short-history rule. These full-period residuals describe co-movement retrospectively; announcement CARs below must instead use coefficients estimated strictly before each event.

## 9. Stage C — company disclosures and fundamental news

Collect all verified quarterly earnings announcements in the eligible history, not only announcements followed by large moves. Map announcement timing to the first affected trading session: pre-open, intraday, after-close, weekend, or uncertain.

For established issuers, estimate a daily market model on trading days `[-252, -21]` before each event, requiring at least 160 usable observations. Use market-plus-industry as a sensitivity. Keep estimation and event windows separate. Define primary cumulative abnormal return (CAR) over `[-1, +1]`, and secondary `[0, +1]` and `[-1, +5]` windows. Window endpoints are trading sessions and must be coded explicitly. Incomplete windows at the cutoff remain incomplete; do not use later prices.

Relate announcement CARs to a small number of prespecified financial updates:

1. **Primary:** Change in quarterly GAAP EPS versus the same fiscal quarter a year earlier, scaled by the pre-announcement share price on a compatible split basis. Call this a price-scaled earnings change, not an analyst-consensus surprise.
2. **Secondary:** Year-over-year change in operating margin, with pass-through and accounting comparability flags.

Show scatterplots, effect sizes and uncertainty by company. If pooling established-company events, use company intercepts, only these two financial covariates, and clearly identify the common-slope assumption. Resample blocks of two consecutive calendar quarters jointly across firms for uncertainty; do not treat four company clusters as a reliable large-cluster approximation. Where sample size, dependence or instability defeats inference, retain descriptive results and say so.

Historical consensus surprises, archived guidance revisions, and backlog revisions can be valuable supplementary evidence **only if their prior information sets are recoverable**. Current consensus cannot reconstruct historical expectations. Missing consensus is not zero surprise. Use actual cash-flow/earnings disclosure updates and prior company guidance as transparent fallbacks, without claiming to observe all market expectations. Distinguish unchanged-horizon guidance revisions from a routine roll into a new fiscal year.

Create a separate strategic-event register for acquisitions, quality failures, plant ramp-ups, large contracts, government financing, equity issuance, buybacks, lockup expirations and material policy changes. Establish events from disclosures, not from the sign of the stock return. Flag overlapping earnings/macro/financing news; an event window seldom isolates one causal mechanism.

**Mandatory ELMT case review:** Its September 14, 2026 announcement and 8-K describe a government investment involving redeemable preferred equity and warrants. The announcement also distinguishes a stockpile-contract ceiling from a smaller funded commitment. Review the actual terms, timing and common-shareholder claims before interpreting any price move. Funding is not earnings, a contract ceiling is not recognized revenue, and dilution is not captured by ordinary debt ratios. Do not assume a favorable or unfavorable return before measuring it. ELMT lacks the prescribed pre-event estimation history, so use benchmark-relative descriptive returns and explicit limitations instead of fabricated event-study precision.

Report the mean CAR and its confidence interval, event count, and event-to-event variance for each company where estimation is feasible. Keep individual strategic-event descriptions separate from pooled earnings-event averages. An observed event-window association does not identify the cause of all price movement in that window.

## 10. Stage D — first and second moment estimation

Make mean return and return variance the primary statistical outputs. For arithmetic returns `r_t` on a sample of `N` matched observations, define:

```text
Sample mean:       mean(r) = sum(r_t) / N
Sample variance:   s² = sum((r_t − mean(r))²) / (N − 1)
Sample volatility: s = sqrt(s²)
```

Use the second **central** moment, variance, rather than confusing it with the raw second moment `mean(r²)`. State whether each estimate describes total returns, excess returns over the risk-free rate, benchmark-relative returns, or model residuals. Use arithmetic returns consistently in the primary moment estimates and factor models; log returns belong to the separately labeled accounting bridge.

For each company and eligible model, on identical dates report:

* sample mean total return and mean excess return, with standard errors and 95% confidence intervals;
* sample variance and volatility, with 95% confidence intervals;
* alpha and mean common-factor contributions, with uncertainty, as the model-based first-moment decomposition;
* fitted and residual sample variance, their shares of total excess-return variance, and residual volatility;
* return and residual covariance/correlation matrices, beta, and autocorrelation diagnostics needed to interpret dependence and uncertainty.

Use synchronized pairwise comparisons of MTRN with each other company as the primary comparison family. Report differences in mean excess returns and ratios of variances or volatilities with confidence intervals; clearly distinguish a variance ratio from a volatility ratio. Apply the same dates and compatible model specifications to both companies. Do not rank companies by the magnitudes of separately estimated point estimates when uncertainty does not distinguish them. In the five-company short-period panel, use raw/excess-return moments and a common eligible market-only model for any residual comparison; keep richer established-company models in their separate long-history panel.

Report daily and weekly moment estimates as descriptive comparisons; monthly observations remain the primary factor-model frequency. Compound daily returns correctly to form weekly and monthly returns. State units, sampling frequency and annualization conventions. Present native-frequency estimates first. If showing annualized arithmetic mean `m × mean(r)` and volatility `sqrt(m) × s`, state that the mean is not CAGR and that the volatility rule assumes negligible serial covariance. Check serial dependence and use an explicitly documented autocovariance adjustment or directly aggregated returns when that approximation is materially misleading. Do not use an IID standard error `s / sqrt(N)` as the default uncertainty estimate when returns are dependent.

Keep cumulative total return and sufficiently long-period CAGR as shareholder-experience context, separate from moment estimates. A Sharpe ratio derived from excess-return mean and volatility may be shown as a secondary summary with uncertainty. Do not subtract the risk-free rate twice or interpret a residual-series Sharpe ratio or CAGR as an investable shareholder outcome. Prioritize the components of the ratio over an apparent ranking based on the ratio alone.

Use synchronized moving-block resampling so cross-company dependence is preserved. Initial choices: 2,000 replications, fixed recorded seed, ten-trading-day blocks for daily moments and three-month blocks for monthly models. Resample paired observations together when estimating mean differences or variance ratios. Re-estimate models inside relevant resamples. Use five-week blocks for weekly moment intervals and check a small declared range of block lengths rather than tuning them to significance. For event regressions use the two-quarter blocks specified above, preserving each event's financial update and CAR together. State that these intervals remain approximate under structural change and short samples.

Keep genuine jumps in the primary data. Correct demonstrable bad prints and corporate-action errors with an audit trail. Show sensitivity of the mean and variance to excluding the largest one/five absolute-return observations and to excluding announcement windows. These are influence diagnostics, not a cleaner preferred history. ELMT's estimates require prominent short-sample uncertainty labels. Historical mean returns are particularly imprecise and must not be presented as reliable estimates of future expected returns.

Conclude with the estimated historical mean, common-exposure-adjusted mean, explained and unexplained variance, and uncertainty for each company. Relate those observations to operating performance and repricing without assigning investor motives or claiming that a variance decomposition measures intrinsic value.

## 11. Robustness and inference discipline

Keep the required checks finite:

1. Long panel versus 2021-onward and common post-IPO periods, subject to model gates.
2. Primary style factors versus FF5-plus-momentum; industry/macro block-order sensitivity.
3. Point-in-time versus clearly labeled comparable/revised operating data.
4. All valid observations versus largest-move and announcement-window sensitivities.
5. Daily versus weekly mean/variance estimates; pre/post major business changes; simpler beta-stability diagnostics where observations permit.
6. Alternative event windows and uncertain announcement-time mapping.

Report economic magnitudes and interval widths before statistical significance. Define testing families before applying a multiple-testing adjustment such as Benjamini–Hochberg. Label remaining exploratory tests; do not rank p-values from dozens of specifications. Five issuers are not thousands of independent firms merely because daily observations are numerous. Avoid ordinary IID bootstraps, unrestricted stepwise selection, complex machine learning, a large forecasting contest, or an elaborate trading backtest.

For a mechanism to receive stronger descriptive support, require: a credible economic pathway, valid timing, material effect size, and stability across the small declared checks. Even meeting these conditions does not turn this observational study into causal identification.

## 12. Required outputs

Keep experiment-specific work under:

```text
MTRN/experiments/
  prompt.md                         # this protocol; preserve it
  historical_attribution/
    README.md
    code/
    data/raw/
    data/processed/
    sources/
    figures/
    final/Historical_Attribution.html
```

Use `common/code` for genuinely reusable point-in-time joins, return statistics, factor estimation and event-window functions. Do not alter the earlier investment conclusions to match this experiment. Extend the source archive without overwriting dated snapshots. Do not create duplicate raw files when an immutable existing input can be referenced with a hash.

Produce one main report with:

* a concise answer to the research question, separating supported findings from unresolved interpretations;
* a coverage/availability matrix and all sample dates;
* business-exposure and comparable-financial dashboards;
* exact historical earnings/multiple bridges where valid;
* factor-loadings, mean-return contributions and adjusted-R² tables with uncertainty and identical-sample comparisons;
* financial-announcement CARs, mean event responses with confidence intervals, all-event scatterplots, and strategic-event evidence;
* raw/excess-return mean, variance and volatility tables with confidence intervals and MTRN-versus-peer comparisons;
* model-based explained/residual variance decompositions and covariance/correlation diagnostics;
* a dedicated ELMT short-history and financing case study;
* limitations, source citations and reproduction commands.

The central synthesis table should have one row per company and these separate columns:

`Operating change | Earnings/multiple bridge | Mean excess return and alpha | Explained/residual variance and volatility | Disclosure/event association | Confidence/limitations`.

Keep the accounting bridge, mean-return decomposition and variance decomposition visibly separate. A useful conclusion may read: “Reported earnings increased and the valuation multiple expanded. Mean excess returns differ across companies, with the reported confidence intervals. Common exposures account for part of monthly return variance; the remaining variance is unexplained conditional on the model.” Use measured results rather than this illustrative wording as the conclusion. Do not combine these different quantities into one percentage of fundamentally justified value.

## 13. Reproducibility and completion checks

Provide a single offline rebuild command, pinned dependencies, a frozen configuration, source manifest, data dictionary, model specifications, excluded-observation log, random seed, and validation results. Cache downloads separately from analysis.

Before completion verify:

* issuer and security mapping, trading dates, splits and dividends;
* every as-known input's availability relative to its assigned date;
* original versus restated financial history, fiscal alignment and TTM construction;
* MTRN metal pass-through/mining capex and peer ratio denominators;
* actual versus diluted shares, preferred claims and warrant treatment;
* no observations or event-window endpoints after September 18, 2026;
* partial months and ELMT's history restrictions;
* factor units, risk-free subtraction, frequency, and complete-case alignment;
* model rank, minimum observations, covariance accounting and coefficient units;
* exact price/EPS/multiple bridge arithmetic and separate total-return treatment;
* earnings timestamps, uncontaminated estimation windows and event overlaps;
* mean/variance definitions, native-frequency units, annualization, sample sizes and dependence-aware uncertainty;
* alpha versus the mechanically zero fitted-residual mean, common variance denominators, and exact sample variance reconciliation;
* matched samples and paired confidence intervals for MTRN-versus-peer mean differences and variance/volatility ratios;
* charts and narrative reconciled to outputs; no causal claim stronger than the evidence.

If a required dataset is unavailable, preserve a clear gap and complete the portions supported by evidence. Do not fill gaps with fabricated consensus, prices, operating exposures or financial observations.

## 14. Starting sources and methodological references

These establish data sources and methodological background; the numerical windows and model choices above are this study's proposed design, not quotations from these references.

* [Kenneth French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html): factor returns and construction notes; preserve the downloaded vintage.
* [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces): filings and XBRL, supplemented with original documents and release timestamps.
* [St. Louis Fed real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html): distinguish historical availability from currently revised values.
* [MacKinlay, Event Studies in Economics and Finance](https://www.bu.edu/econ/files/2011/01/MacKinlay-1996-Event-Studies-in-Economics-and-Finance.pdf): event-window and normal-return methodology.
* [Elmet IPO closing announcement, April 24, 2026](https://investors.theelmetgroup.com/news-events/press-releases/detail/157/the-elmet-group-co-announces-closing-of-upsized-initial-public-offering-and-full-exercise-of-underwriters-option-to-purchase-additional-shares): verified public-listing start and IPO context.
* [Elmet September 14, 2026 announcement](https://investors.theelmetgroup.com/news-events/press-releases/detail/168/department-of-war-makes-landmark-450-million-committed-investment-in-the-elmet-group-to-secure-americas-tungsten-supply-chain) and [corresponding 8-K](https://investors.theelmetgroup.com/sec-filings/content/0001213900-26-099734/ea0304682-8k_elmet.htm): capital-structure and strategic-event evidence relevant to common shareholders.
