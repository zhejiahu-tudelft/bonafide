# Execution addendum: separate return and variance research

This implements the [versioned protocol](../prompt_v2_financial_valuation_models.md), with the user's subsequent requirements taking precedence. The original experiment is archived; its outputs are not reused as predictive findings.

The return hierarchy is historical mean/market/CAPM-style benchmarks, linear financial-plus-valuation factors, Ridge/Lasso/Elastic Net, distributed lags, AR/ARX and ARMA-error regression, Random Forest and gradient boosting. Scikit-learn gradient boosting is the single primary boosting implementation; duplicative XGBoost/LightGBM and all deep-learning methods are excluded.

The separate risk hierarchy is historical central variance, EWMA, ARCH, GARCH, GARCH-X with market then industry/business volatility inputs, and regularized/tree-based variance forecasting. Target risk is next month's sample central variance of daily returns. Forecasts from daily volatility models are averaged over the target month's exchange sessions. Variance and its square root, volatility, have separate units; covariance and correlation receive a separate descriptive/regime study.

Return ablations follow the latest requested order: market baseline → market variables → financial → valuation → momentum → risk/volatility → industry → company business drivers → selected differences/lags → two fixed interactions. Liquidity features are separately flagged within the risk/liquidity block. Financial-only and financial-plus-valuation comparisons and full-minus-block checks retain the earlier research questions.

Monthly forecasts use expanding training windows with 84 completed targets initially. A rolling 84-month sensitivity is separate. Coefficients refit monthly. To bound redundant computation, hyperparameters retune at the first origin and each January on two prior 12-month chronological validation blocks, then remain fixed until the next scheduled retune. This is a disclosed operational change to the initial draft, not a response to observed results. All preprocessing still refits inside every training fold. Regularization uses five prespecified strengths rather than twelve. Random Forest and gradient boosting each use two shallow, regularized configurations.

Individual models are compared with pooled models containing company indicators and with two transparent business-pair pools (MTRN/ENTG and CRS/ATI), not claimed homogeneous industries. No ARIMA process concatenates different issuers. ELMT has insufficient months for the common primary training gate; its five-stock public sample and financial/financing context remain visible, while long-horizon formal modeling uses the four eligible issuers.

Market forecasts use only historical market information: the market-mean benchmark predicts the stock using the market's trailing mean; CAPM-style forecasts estimate its historical relationship with SPY and supply a historical-mean SPY forecast. Realized future market returns never enter these forecasts. Commodity, FX and macro observations are delayed by at least one US session to avoid ambiguous same-date closing/release times.

The report must address RQ1 factor value, RQ2 cross-firm differences, RQ3 transformations/lags, RQ4 nonlinear models, RQ5 variance dynamics, RQ6 external volatility factors, RQ7 temporal/regime stability and RQ8 pooling. Each follows the research question → reproducible setup → variable mechanisms → criteria → results/figures → interpretation → conclusion → limitations sequence and the professional figure contract in protocol sections 15–18.

Actual coverage, justified deferrals, failures and all validated specifications are recorded in machine-readable artifacts. No unavailable consensus, historical bid–ask spread, financing claim, commodity series or private return is fabricated. Statistical significance is not a completion requirement.

## Continuation addendum, September 21, 2026

These are the disclosed changes made when the implementation was resumed. They are recorded here
so the frozen specification and the code agree; `CONTINUATION_AUDIT.json` holds the machine-readable
version with the effect of each change.

Block removal now follows declared parent dependencies rather than name prefixes. A model described
as valuation-free previously retained the P/E percentage change, which biased the estimated
contribution of the valuation block toward zero. This affects the study's central comparison.

Each disclosed accounting flow keeps its own as-known reporting period. The shared-period
requirement applies only where a ratio combines two flows, such as a margin or a payout ratio; a
market-capitalisation-denominated valuation ratio no longer depends on an unrelated line item's
clock. Common book equity falls back to the consolidated tag only where the issuer's own earlier
filings show a noncontrolling interest within a 1% tolerance, recorded per observation. Free cash
flow is modelled on equipment capital expenditure, with Materion's annually disclosed mine
development retained in the audit trail and tested as an MTRN-only sensitivity.

Per-issuer alias columns, `industry_return` and `driver_return`, are kept in the compact core but
removed from the broad feature set, where they exactly duplicated a named series.

Both ablation ladders are reported: the protocol's own order, financials first, and the
market-first order requested later. They answer different questions and neither uniquely allocates
information shared between blocks.

Elastic Net tunes the mixing parameter over {0.2, 0.5, 0.8} alongside the five prespecified penalty
strengths. A zero-return benchmark and a secondary excess-return target, the stock's return minus
the market's realised return over the identical month, are scored as separate tasks.

Four one-month-return contrasts per eligible issuer are frozen as the primary comparison family and
carry Holm adjustment across the resulting sixteen comparisons. Everything else is exploratory.

## Version 4 revision addendum (2026-09-21)

Version 4 applies the justified recommendations of the methodological review in
`../prompt__revision.md`. The binding decisions are in `REVISION_SPEC.md`, frozen before rescoring,
with later amendments logged in `revision_freeze.json`; where they differ from the text above,
`REVISION_SPEC.md` governs. In summary: a per-observation ridge penalty with a λ grid from 1e-4 to
100 plus an intercept-only candidate for every tuned procedure; inner validation that refits at
each of the last 24 training origins on matured labels; a rolling window tuned on its own history;
one circular block bootstrap giving compatible intervals and p-values (B = 1999); four declared
families (R16, RJ4, V20, VJ5) with Holm within each; a controlled individual/pooled ×
persistence/external variance matrix; Clark–West for fixed nested OLS pairs; loss-only influence,
calibration and detectable-effect diagnostics; and the market-relative rename of the secondary
target.

Correction to the addendum above: it stated that retaining the P/E percentage change in the
valuation-free model "biased the estimated contribution of the valuation block toward zero". That
direction is not established — a regularised model can use or ignore a leaked column — and the
correction is one of validity, not of a predictable shift in the estimate.
