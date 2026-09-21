# Investment interpretation and follow-up experiment

Prepared September 20, 2026. All investment observations retain the **September
18, 2026 cutoff**. Monthly factor estimates stop on **July 31, 2026**. This is an
interpretive addendum to the [completed historical study](Historical_Attribution.html)
and the [original investment report](../../../final/MTRN_Investment_Research.html).
The new diagnostics are exploratory checks made after reviewing the original
results; they are not new confirmatory hypothesis tests.

## 1. Reframed investment conclusion

**Materion's operating improvement is credible, but the historical experiment
does not establish that its cutoff valuation offers attractive compensation for
the cash-conversion and execution risks. The original cautious entry-price view
therefore remains a valuation judgment, rather than a statistically demonstrated
forecast of poor returns.**

At $251.53, the original report calculated approximately 35.9 times management's
2026 adjusted-EPS guidance midpoint and a 0.6% trailing free-cash-flow yield.
Trailing FCF was $32.4 million after equipment and mine-development spending.
Those facts make sustained cash generation the key investment question. High
growth investment can temporarily suppress FCF, so a low trailing yield alone
does not prove overvaluation.

The experiment changes how confidently we can use several supporting arguments:

| Evidence | Investment implication | Interpretation limit |
|---|---|---|
| MTRN's long monthly factor alpha is +0.64%, with a 95% HAC interval of -0.63% to +1.90%; none of the four primary long-model alphas survives the specified multiple-testing adjustment. | Historical factor-adjusted mean returns do not establish a superior-return ranking among these companies. | Failure to reject zero is not proof that alpha is zero, that shares are fairly valued, or that future returns will be weak. |
| Long daily total-return variance is lower for MTRN than for ENTG, CRS and ATI. In the April 24–September 18 matched window, MTRN/ATI variance is 3.07 and MTRN/CRS variance is 3.11. | The risk advantage depends on the period. Long-history volatility should not be treated as a permanent reason to accept a premium valuation or a larger position. | Recent estimates use only 102 returns and are sensitive to large moves. Separate window estimates do not constitute a formal structural-break test. |
| MTRN's average primary earnings-window abnormal return is about +4.08%, with a pointwise 95% interval of +0.27% to +7.25%. | Earnings dates have been economically important to its historical repricing. | Only 23 events; the interval is unadjusted for the wider set of event comparisons. This is not an independently validated announcement trading edge. |
| Earnings/multiple bridges differ sharply by starting date. | Both earnings recovery and repricing matter; attributing all appreciation to expanding multiples would be misleading. | The identity is mechanical, and GAAP impairment bases and the approximate rolling-EPS construction affect the split. |

The cutoff financial snapshots put FCF yields at approximately 0.62% for MTRN,
2.65% for ENTG, 1.79% for CRS and 2.02% for ATI. These are useful questions for due
diligence, not a valuation ranking: investment cycles, acquisitions, working
capital and business mix differ. ELMT lacks a comparable trailing basis.

For a new MTRN investment, the evidence needed to strengthen the case is recurring
value-added sales growth, durable cash conversion after total investment, and
acceptable returns on the capital already deployed. A lower purchase price could
also improve the valuation case. The experiment does not statistically validate
the original report's $205 earnings scenario or $98 DCF; those remain conditional
valuation exercises. It also does not establish which peer will outperform.

## 2. Why some results are inconclusive

### A. The valuation question and the return-model question differ

The regressions ask how realized returns covary with traded exposures and whether
a conditional mean remains. They do not directly estimate the cash flows needed
to justify a share price. Even the profitability and investment factors are
returns on portfolios, rather than the issuer's own profitability or investment
data. See the [French factor definitions](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_5_factors_2x3.html).

Consequently, better return-model fit would not resolve fair value. Conversely,
a wide alpha interval does not invalidate the accounting evidence on weak cash
conversion. These questions require different evidence.

### B. Mean estimates are imprecise at the available effective sample size

The long monthly model has 127 observations; the recent model has 67. MTRN's
alpha interval spans approximately 2.53 percentage points per month. That directly
shows the uncertainty around the historical conditional mean. Thousands of daily
prices do not supply thousands of independent years of economic experience.

The pooled event study has 92 announcements, but only four issuers and 23 calendar
quarters. ELMT contributes only 102 public daily returns to the matched panel and
cannot support the same long-horizon models. Enlarging the peer list would improve
cross-company comparisons, but would not by itself lengthen MTRN's return history
or narrow its separately estimated alpha interval.

### C. The announcement variables measure changes, not unexpected news

Year-over-year EPS and margin changes may already have been anticipated. A company
can report strong growth and fall after an announcement if expectations were
higher, or if guidance weakens. Historical consensus, guidance revisions and the
full set of simultaneous disclosures were not assembled. Timing is also uncertain
for 84 of the 92 releases; the original study includes alternative date mappings
and event windows to show that limitation.

The inconclusive slopes therefore cannot establish that financial performance
does not matter to prices. They describe the limited relationship between these
particular disclosed changes and the selected event returns.

### D. A measurable specification problem affects the pooled event regression

The new [diagnostics](../diagnostics/inference_review/summary.json) reproduce the
original coefficients and then examine the inputs after removing company means:

| Diagnostic | Result | Meaning |
|---|---:|---|
| Correlation between EPS change/price and margin change | 0.981 | The model has little independent variation with which to distinguish their separate slopes. |
| ATI share of within-company EPS-variable sum of squares | 97.0% | Most variation used to estimate the pooled relationship comes from ATI. |
| ATI share of within-company margin-variable sum of squares | 92.0% | The concentration affects both explanatory variables. |
| Partial R² from the two variables beyond company intercepts | 4.21% | They account for little additional event-return variation in this sample. This is an in-sample descriptive fit statistic. |
| Largest observation leverage | 0.588 | One observation is unusually influential in determining the fitted relationship. |

ATI's January 2021 release reported a quarterly EPS loss of $8.85 and large
impairment/restructuring charges. The following year's comparison uses that loss
as its base. The large change back toward ordinary earnings is not equivalent to
a similarly sized recurring operating-growth surprise. The archived
[original ATI release](../sources/earnings/ATI_0001628280-21-000940_release.html)
identifies the charges and notes that the underlying restructuring decision had
previously been announced. The year-over-year improvement does not imply that the
impairment itself was reversed.

The earnings coefficient is -0.140 in the two-variable model, +0.255 when used
alone, and +1.563 when ATI is omitted from the two-variable model. These are
descriptive sensitivity estimates, without new confidence intervals. Their sign
changes demonstrate specification sensitivity; none establishes a return effect.
See [all single-variable and leave-one-company-out checks](../diagnostics/inference_review/event_specification_diagnostics.csv).

This is the clearest identifiable design weakness. Standardizing units would not
remove the near-redundancy. Dropping ATI after seeing the results would change the
question, so its exclusion belongs in a disclosed sensitivity, not a replacement
headline result.

### E. The traded factors are useful, although incomplete

Long-sample R² values, using the same 127 months, are:

| Company | Market only | Market plus style | Plus semiconductor and defense proxies |
|---|---:|---:|---:|
| MTRN | 24.2% | 42.2% | 45.3% |
| ENTG | 27.5% | 32.3% | 55.9% |
| CRS | 28.5% | 43.8% | 52.2% |
| ATI | 18.4% | 32.9% | 47.7% |

The industry block adds approximately 23.6 percentage points for ENTG, 8.4 for CRS,
14.8 for ATI and 3.0 for MTRN. This supports economic relevance of the chosen
exposures, without constituting a causal attribution or a formal test of the
increment. Adjusted R² also improves for all four when this block is added.

MTRN's nominal-rate sensitivity barely changes fit, and the FF5-plus-momentum
alternative does not improve fit over the primary industry model. Thus the
available checks do not support blaming the inconclusiveness mainly on an
obviously bad traded-factor selection. Real yields, credit spreads and better
operating-demand data remain missing, but their explanatory value has not been
measured. Adding many variables to 67 or 127 months could worsen precision.

### F. The peer set is useful for exposure comparisons, less suitable for valuation matching

ENTG, CRS and ATI represent relevant end-market exposures, but differ in product
mix, capital intensity, scale and accounting. MTRN's metal pass-through revenue
also makes unqualified revenue-margin and sales-multiple comparisons misleading.
ELMT combines a short public history with a distinct financing structure.

These are defensible reference companies, not a controlled set of economically
interchangeable businesses. Their heterogeneity matters particularly when pooling
financial-response slopes or inferring a common valuation multiple. It does not
invalidate separately fitted historical return models.

### G. Businesses, risk and accounting bases change over time

Acquisitions, restructuring, exceptional charges and changing end-market exposure
make a constant decade-long coefficient an approximation. The recent reversal in
relative variance illustrates why window sensitivity matters. Block resampling
allows for some dependence but cannot make different business regimes identical.
The factor archives also have a retrospective-vintage limitation, and financial
cash-flow coverage is incomplete in some quarters. These constrain precision and
interpretation; they are not demonstrated explanations for every null result.

The primary alpha family appropriately adjusts for multiple comparisons. A
coefficient that looks significant in one window or standard-error specification
is weaker evidence than a stable result across declared checks. The goal of the
next experiment should be a more relevant and better measured comparison, rather
than a higher count of significant tests.

## 3. Recommended alternative: financial peer matching and historical valuation

**Question:** At each historical information date, how did MTRN's valuation compare
with companies with similar operating economics, and how did that valuation gap
move alongside disclosed improvements in cash generation and profitability?

This answers the investment-comparison question more directly than another large
return-factor regression. Clustering can assist peer selection, but it should
not be the result we are trying to prove.

### Proposed design

1. **Broader, economically screened universe.** Seek roughly 30–60 US-listed
   materials/component/process-supply businesses, subject to data and business
   comparability, over about 8–10 years. These are practical targets, not statistical
   sufficiency thresholds. Define eligibility before inspecting returns. Include
   historically eligible acquired/delisted firms where obtainable and disclose
   omissions. Record semiconductor, aerospace/defense and specialty-materials
   exposure to prevent financially similar but economically irrelevant matches.

2. **As-known annual snapshots.** Use common calendar dates and only filings
   available then. Preserve original and recast accounts separately. Annual
   comparisons suit the existing cash-flow coverage better than inventing missing
   quarterly figures. Acquisitions and major accounting-policy changes require
   explicit comparability flags. A second snapshot in the same year is not another
   independent year of evidence.

3. **Six price-free matching characteristics.** Start with three-year gross-profit
   growth, aggregate operating income/gross profit, aggregate CFO/gross profit,
   aggregate total investment capex/gross profit, net debt/assets, and size measured
   by log gross profit. Aggregate ratios use sums over the same three fiscal years.
   Positive meaningful denominators and compatible accounting are eligibility
   requirements. Gross profit can reduce the metal pass-through distortion but
   does not eliminate accounting differences. MTRN value-added sales remain a
   separate issuer-specific cross-check. Use equal economic-dimension weights,
   inspect redundancy, and freeze definitions before comparing valuation outcomes.

4. **Transparent matches first; clustering second.** Scale characteristics by
   cross-sectional medians and interquartile ranges at each information date.
   Identify up to five close eligible peers and publish distances and individual
   characteristics. Require adequate overlap instead of forcing a match. Use
   hierarchical clustering as a secondary description of the broader universe.
   Check membership stability when firms, periods and reasonable feature weights
   change. If groups are unstable, retain continuous similarity distances. With
   the present five issuers, a distance heatmap is descriptive; it cannot establish
   a reliable industry taxonomy. K-means also requires a chosen number of clusters
   and geometric assumptions; an internally coherent partition is not evidence of
   a valuation effect. See the [clustering methodology documentation](https://scikit-learn.org/stable/modules/clustering.html).

5. **Keep valuation and stock returns out of the grouping variables.** Compare
   reconciled EV/operating EBITDA where denominators are positive, and FCF yields
   with consistent total-capex definitions, only after matches are fixed. Completing
   the historical enterprise-to-equity reconciliation is required before publishing
   EV multiples; it is currently deferred. Report the valuation gap, its position
   within the peer distribution, and comparisons with the company's own history.
   Relate changes in those gaps to disclosed operating changes. A premium relative
   to observed characteristics can still reflect unmeasured growth or risk.

6. **Estimate uncertainty without manufacturing observations.** Recompute matches
   when resampling firms and calendar-year blocks; show leave-one-peer/year-out
   sensitivity. Do not treat repeated company-years as independent companies.
   Treat the small number of independent years as a continuing limitation. If
   return comparisons are included, use only historical periods ending by the
   cutoff, select matches from information available at their start, and report
   matched mean-return differences and variance ratios with dependence-aware
   intervals. Do not tune groups to improve those return results. Keep ELMT
   descriptive until its financial history and common-share claims are sufficiently
   comparable; private operating records never substitute for public returns.

The useful deliverable would show **which businesses are defensible peers, the
size and stability of MTRN's historical valuation gap, and which differences in
cash generation or capital needs remain relevant after matching**. An unstable
peer set or a wide interval is still an informative result. The design cannot
prove intrinsic mispricing or identify investor motives.

### Smaller repair to the existing announcement experiment

Before increasing model complexity, estimate one financial variable at a time,
retain GAAP as the primary accounting basis, and add a consistently reconciled
exceptional-item sensitivity. Preserve the full sample and display the
leave-one-company-out checks. For a better news measure, assemble archived
pre-announcement consensus where obtainable or management's last published
guidance for a precisely matching period and metric. A guidance comparison is
not a substitute for investor consensus and should be labeled accordingly.

The peer-matching study has higher priority for comparing investment value. The
event repair addresses a narrower question about what was newly disclosed around
announcements. Neither follow-up should be judged by whether it produces a
statistically significant result.

## Reproduction of the added diagnostics

Run from the repository root:

```bash
/tmp/mtrn-research-venv/bin/python -B MTRN/experiments/historical_attribution/code/diagnose_inference.py
```

The script uses cached outputs only and writes to `diagnostics/inference_review/`.
It reproduces the original pooled coefficients, checks input dates and algebraic
identities, and verifies preservation of all 171 baseline files plus its primary
input tables and the experiment HTML. The original protocol and result tables
remain the basis for the confirmatory results. The broader proposed experiment
has not been run.
