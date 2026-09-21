# Financial, valuation and business-driver forecasting experiment

Open [the standalone report](final/Financial_Valuation_Model_Comparison.html). All eighteen
figures are embedded; the report needs no internet connection. Linked CSVs, registries and
audit records sit alongside it. The controlling
[protocol](../prompt_v2_financial_valuation_models.md), the earlier
[historical-attribution study](../historical_attribution/) and the original MTRN investment
report are preserved unchanged and hash-verified.

**Question.** Standing at a month-end close with only the information published by then, do a
company's disclosed financial characteristics and the valuation investors were paying carry
information about next month's return — and does adding time-series structure improve on a
static regression using the same inputs? A separate risk task asks the same of next month's
realized variance.

**Answer, in one line.** No reliable improvement on the return task; the expanding historical
mean remains the model the evidence supports. The variance task does improve on its persistence
benchmark. See the report for the uncertainty behind both statements — these are imprecise
estimates from a short sample, not measured zeros.

Information and price cutoff: **2026-09-18**. Targets run January 2023 – August 2026, 44 matured
monthly outcomes per issuer. Established issuers: MTRN, ENTG, CRS, ATI. ELMT listed in April 2026
and contributes five monthly observations, far below the 84-month training gate, so it is
excluded from every fitted model and appears only as a descriptive case.

## Offline rebuild

From the repository root, with Python 3.12:

```bash
python3 -m venv /tmp/mtrn-research-venv
/tmp/mtrn-research-venv/bin/pip install -r MTRN/experiments/financial_valuation_models/code/requirements.txt
/tmp/mtrn-research-venv/bin/python MTRN/experiments/financial_valuation_models/code/run_experiments.py
```

Installing dependencies needs network access; the rebuild command does not. It runs method tests,
features, return models, variance models, pools, controlled transformations, scoring,
diagnostics, dependence, documentation, the report and finally `validate.py`, stopping if any
stage or check fails. Seeds are fixed at 20260918 and the pipeline is deterministic: a rerun
reproduces the saved forecast ledger exactly.

`code/fetch_external.py` is the separate network retrieval entry point. It never overwrites an
existing archive — a historical price or macro snapshot cannot be reconstructed from a live
endpoint.

## How the experiment is put together

* `code/features.py` — the monthly as-known feature table, the availability audit and the
  exposure map. Every accounting value is selected by verified publication date; commodity, FX,
  volatility and macro series are delayed a further US session.
* `code/learning.py` — the estimator wrapper (training-only clipping, imputation, scaling),
  chronological inner tuning, and the feature-set definitions including both ablation ladders and
  the dependency-aware block removal.
* `code/return_models.py` — benchmarks, static, regularized, tree, distributed-lag and ARIMAX
  forecasts at each origin, plus the excess-return secondary target.
* `code/variance_models.py` — the separate risk task: historical variance, EWMA, ARCH, GARCH,
  GARCH-X and regularized/tree variance forecasts, with a training-only smearing retransformation.
* `code/pooling.py` — company-indicator pools, business pairs and the three-month horizon.
* `code/transform_models.py` — controlled level/difference/percentage/lag comparisons and the
  grouped block-permutation diagnostic.
* `code/score.py` — matched scores, ablation tables, paired block-bootstrap comparisons and the
  frozen sixteen-contrast family with Holm adjustment.
* `code/report.py` — the figures and the standalone HTML report.
* `code/validate.py` — fail-closed checks; results in `data/processed/validation_results.json`.
* `tests/test_methods.py` — statistical invariants that protect the historical simulation.

## What the data support, and what it does not

Four issuers and 44 monthly outcomes each. Monthly equity returns are dominated by noise at this
length, so the study is underpowered against any plausible effect size; that is the binding
constraint on every conclusion here. "No reliable improvement" is not "no effect".

These companies and much of their history were reviewed before the protocol was frozen. The
protocol is newly frozen, not preregistered on unseen data.

Inputs recorded as unavailable rather than approximated: archived analyst consensus (so forward
P/E, earnings surprise and estimate revisions could not be tested at all), a fully reconciled
enterprise-value and ROIC claims bridge, historical index membership, historical bid-ask spreads,
and tungsten/molybdenum price history. The high-yield credit-spread archive begins in 2023 and
fails the training coverage gate. Each remains visible in `data/processed/deferrals.json` and in
the report's scope statement.

## Data repairs made during this continuation

Three extraction defects were found and corrected; each changes the archived numbers, and the
`CONTINUATION_AUDIT.json` records what moved.

* **Entegris book equity.** The parent-only equity tag stops in 2019; Entegris reports a
  consolidated equity line thereafter. That line is now used where the issuer's own earlier
  filings show a noncontrolling interest within a 1% tolerance, and the substitution and measured
  tolerance are recorded per observation. ATI, whose noncontrolling interest is material, never
  uses the fallback.
* **Carpenter trailing earnings.** Each disclosed flow now keeps its own as-known reporting
  period. The previous rule forced every line item onto the revenue clock, which voided
  Carpenter's trailing earnings — and with them its earnings yield, ROA and net margin — whenever
  its revenue tag reported a different period end. The shared-period requirement now applies only
  where a ratio genuinely combines two flows.
* **Materion free cash flow.** Mine development is disclosed only annually, so it cannot form a
  quarter-aligned trailing measure. Free cash flow is modelled on equipment capital expenditure;
  the mine-inclusive series is retained for the audit trail and tested as an explicit MTRN-only
  sensitivity. The mine-inclusive value still reconciles to the preserved earlier study.

A fourth correction is methodological rather than extractive: block removal now follows declared
parent dependencies, so a model described as valuation-free no longer retains a P/E percentage
change. That affects the study's central comparison.
