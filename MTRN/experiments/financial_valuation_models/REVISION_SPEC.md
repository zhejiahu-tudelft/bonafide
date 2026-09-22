# Revision specification — version 4

Frozen on 21 September 2026 **before** any revised forecast was scored. The SHA-256 of this file and
the freeze time are recorded in `revision_freeze.json`. The validator fails if this file changes
after the freeze without a logged amendment.

**Status: post-hoc revision.** Every decision below was made after reading the version-3 results.
Freezing the decisions before rerunning does not make the 2023–2026 evaluation sample unseen, and it
does not turn this into a preregistered study. Read the revised results as a methodological repair
of an exploratory study, not as an independent replication.

- **Source:** `MTRN/experiments/prompt__revision.md`, reviewed critically. Each recommendation's
  verdict, with its evidence, is in `data/processed/issue_register.csv`.
- **Baseline:** version 3 at git commit `bef7b32`. Its headline tables and a slim forecast ledger are
  frozen in `baseline_v3/`.

## What does not change

- Information cutoff 2026-09-18, final complete target month 2026-08-31.
- Established issuers MTRN, ENTG, CRS and ATI. ELMT stays descriptive: 5 monthly observations against
  an 84-month gate.
- Targets, predictors, point-in-time accounting selection, one-session delays on external series, and
  the 70% training-coverage gate with training-only clipping, imputation and scaling.
- The expanding window, refitted at every origin, with an 84-month initial training history.
- **Evaluation dates.** Each issuer has 44 one-month *target months*, January 2023 – August 2026. The
  matching *forecast origins* are the last exchange closes from 30 December 2022 to 31 July 2026. A
  month-end label such as `2022-12-31` identifies the origin month; the origin itself is the actual
  last close.
- **Retuning.** Hyperparameters are retuned at the first origin and at every December origin. A December
  origin forecasts the following January's target.
- **Compact interpretable model:** `revenue_growth`, `operating_margin`, `earnings_yield`,
  `market_return`, `industry_relative`, `driver_return`. Definitions are unchanged. The broad
  catalogue remains a sensitivity analysis.
- The version-3 frozen family of 16 return contrasts, kept for traceability.

## What changes

1. **Shrinkage grid and penalty convention.**
   - Ridge minimises (1/n)·‖y − Xb‖² + λ‖b‖². In scikit-learn's convention that is α = λ·n_train,
     so one λ means the same per-observation penalty in individual and pooled fits.
   - Lasso and Elastic Net already use a per-observation objective in scikit-learn, so α = λ.
   - Grid: λ ∈ {1e-4, 1e-3, 1e-2, 1e-1, 1, 10, 100}, Elastic Net mixing ∈ {0.2, 0.5, 0.8}.
   - Every tuned procedure — Ridge, Lasso, Elastic Net, random forest and gradient boosting — may
     also select an **intercept-only** candidate, which forecasts the training mean.
   - Ties go to the simpler candidate: intercept-only first, then larger λ, then a larger L1 share.
   - This replaces the version-3 grid α ∈ {0.01 … 100}. Its upper bound was selected in 156 of 176
     broad-Ridge fits and 176 of 176 variance-Ridge fits.
   - The recorded parameter is the λ or capacity actually selected.
2. **Inner validation mirrors the outer procedure.**
   - Validation uses two consecutive 12-month blocks at the end of each training history.
   - At each of the 24 inner origins the candidate is refitted on rows dated before that origin whose
     targets had matured by it: `label_end ≤ origin`.
   - Candidates are scored on the pooled inner loss: MSE for returns, QLIKE with smearing for variance.
   - ARIMAX order selection uses the same monthly-refit scheme.
3. **Rolling 84-month sensitivity.** Retuned on its own 84-month training window with the same
   scheme. It no longer reuses the expanding model's penalty.
4. **Inference.** One compatible procedure, `code/inference.py`:
   - **Test.** Paired calendar-month loss differentials d = loss(reduced) − loss(expanded).
     Positive favours the expanded model. H0: E[d] = 0, two-sided.
   - **Resampling.** Circular block bootstrap, B = 1999, seed 20260918. Blocks of 3, 6 and 12
     months, with **6 primary**.
   - **Interval and p-value.** A 95% percentile interval from order statistics 50 and 1950, and the
     p-value that inverts it: p = 2(min(#d*≤0, #d*≥0)+1)/(B+1). Unadjusted p ≤ 0.05 exactly when
     the interval excludes zero. The Monte Carlo resolution of p is 0.001.
   - **Joint results.** A joint cross-company result averages the companies' differentials within
     each calendar month and resamples whole months.
   - **Scope.** Intervals condition on the saved forecasts. They exclude estimation,
     hyperparameter-selection and specification-search uncertainty.
5. **Declared comparison families.** Holm adjustment applies within each family only; every other
   comparison is exploratory. All families use the one-month horizon and the 6-month block.

   | Family | Size | Contrasts | Loss |
   |---|---|---|---|
   | R16 | 4 × 4 issuers | Per issuer: `ridge_full` vs `without_valuation`; `core_pe_difference` vs `core_pe_level`; `arimax` vs `arma_static`; `distributed_all_lag1` vs `core_ridge` | MSE |
   | RJ4 | 4 | The same four contrasts, equal-weight cross-issuer average | MSE |
   | V20 | 5 × 4 issuers | Per issuer: `variance_ridge_persistence` vs `historical_variance63`; `pooled_variance_persistence` vs `variance_ridge_persistence`; `pooled_variance_external` vs `variance_ridge_external`; `variance_ridge_external` vs `variance_ridge_persistence`; `pooled_variance_external` vs `pooled_variance_persistence` | QLIKE |
   | VJ5 | 5 | The same five contrasts, joint | QLIKE |

   Every family row carries one status:
   - `tested`
   - `identical_by_exclusion` — forecasts are identical at every origin because the distinguishing
     predictor failed the coverage gate
   - `identical_by_selection` — forecasts are identical at every origin because validation chose the
     intercept-only candidate, or an equivalent fit, on both sides
   - `ineligible`

   Identical forecasts are an untested contrast, never evidence of no effect.
6. **Clark–West sensitivity (fixed nested OLS only).** One-sided, with Newey–West standard errors.
   It is kept separate from the operational loss comparison and is never applied to tuned
   penalised or tree models. Pairs:
   - `core_ols` vs `historical_mean`
   - `ar1` vs `historical_mean`
   - `arx` vs `core_ols`
   - `core_ols_financial_ext` vs `core_ols`
7. **Controlled variance matrix.** The pooled models reuse the exact column lists of the individual
   models and add company indicators:
   - `pooled_variance_persistence` uses the `variance_ridge_persistence` columns.
   - `pooled_variance_external` uses the `variance_ridge_external` columns.
8. **Exploratory additions.** Declared now, and outside every family:
   - `core_ridge_financial_ext` and `core_ols_financial_ext`: the compact model plus
     `fcf_equipment_assets` and `debt_assets`, evaluated as one group. This is equipment-capex cash
     flow, not reconciled free cash flow.
   - `without_equity_inputs` (ENTG only): matched exclusion of `roe`, `roe_diff`, `book_yield` and
     `debt_equity`. It is the sensitivity of the conclusions to the consolidated-equity substitution.
9. **Influence diagnostics.** Loss-only: forecasts and fitted models are held fixed. Applied to every
   family contrast and to the headline contrasts against the benchmarks.
   - Leave one target month out, and leave one calendar year out.
   - Named rows for MTRN August 2024 and ENTG April 2025.
   - These rows are not refit robustness tests.
10. **Calibration.**
    - **Procedure.** Estimate the empirical size of the paired test at nominal 5% by simulation:
      500 samples per series, blocks 3, 6 and 12. Each sample resamples a demeaned observed
      differential with a stationary bootstrap.
    - **Series.** For each issuer, `boost_full` − `historical_mean` for returns and `garch11` −
      `historical_variance63` for variance.
    - **Decision rule, declared now.** If the empirical size at the 6-month block exceeds 0.10 for a
      task, that task's p-values are reported as descriptive only, and no discovery claim is made.
11. **Detectable effects.**
    - **Formula.** The minimum detectable mean loss reduction at 80% power and 5% two-sided is
      2.80 × the bootstrap standard error, under a normal approximation.
    - **Scale.** It is also expressed in out-of-sample R² points: divide by the mean benchmark loss.
    - **Purpose.** This replaces any unqualified statement about statistical power.
12. **Naming.** The secondary task is stock return minus SPY return over the same month. It is
    renamed `market_relative_return`. It is a market-relative return, not alpha, not a
    risk-adjusted return and not a return above the risk-free rate.
13. **Successful-fit comparisons.** Each pair is compared on the intersection of origins where both
    fitted successfully. The operational comparison, which includes documented fallbacks, is
    reported separately.

## Reporting rules

- The report distinguishes four levels for every experiment: explanatory association, predictive
  usefulness, statistical evidence, and investment relevance. A lower RMSE is not alpha, and a
  lower variance loss is not a demonstrated portfolio improvement.
- Claims about which intervals exclude zero are generated from the tables, never hard-coded.
- The report states no universal power claim, no equivalence or zero-effect claim, and no claim
  that a performance difference establishes the mechanism of pooling.
- Variance, measured as the within-month sample variance of daily returns, is reported apart from
  volatility, its square root in daily units. The square root of a variance forecast is not an
  expected volatility.
