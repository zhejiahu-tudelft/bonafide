# Historical attribution experiment

Open [the standalone report](final/Historical_Attribution.html). Figures are embedded;
the report itself needs no internet connection. Linked CSVs, source archives and
audit records remain alongside it. The controlling [protocol](../prompt.md) and
the earlier MTRN investment report have not been changed.

The [investment interpretation and follow-up design](final/Investment_Interpretation.md)
connects these results to valuation, diagnoses inconclusive estimates, and proposes
financial peer matching. Its additional checks are explicitly post-protocol and
can be reproduced offline with `code/diagnose_inference.py`; their outputs live in
`diagnostics/inference_review/`.

Information/price cutoff: **2026-09-18**. Monthly French factors end **2026-07-31**.
Established issuers: MTRN, ENTG, CRS and ATI. ELMT has 103 public closes from
2026-04-23, supplying 102 matched returns. All numerical statistics concern past
data; the implementation makes no prediction or intrinsic-value attribution.

## Offline rebuild

From the repository root, with Python 3.12:

```bash
python3 -m venv /tmp/mtrn-research-venv
/tmp/mtrn-research-venv/bin/pip install -r MTRN/experiments/historical_attribution/code/requirements.txt
/tmp/mtrn-research-venv/bin/python MTRN/experiments/historical_attribution/code/run_analysis.py
```

Installing dependencies requires network access. The single `run_analysis.py`
command does **not**: it runs method tests, market statistics, event extraction,
financial snapshots, robustness comparisons, context/source checks, report
generation and validation in order, stopping on any failure. Rebuilding can take
several minutes because confidence intervals use 2,000 refits/resamples. Seeds,
dates and sample gates are frozen in `config.json` and `code/settings.py`.

To run only the independent statistical tests:

```bash
/tmp/mtrn-research-venv/bin/python MTRN/experiments/historical_attribution/code/test_methods.py
```

The network retrieval entry point is `code/fetch_data.py --section all` (or
`market`, `sec`, `earnings`, `documents`). Existing archives are reused. Do not
replace them with newer data and still describe the results as this dated study.
Current endpoints cannot prove the exact factor vintage available on September 18.

## Implemented scope

- Daily/weekly/monthly arithmetic means, central variances and volatility;
  synchronized block intervals and MTRN-versus-peer paired contrasts.
- Total-return wealth context, matched IPO-period comparison, covariance and
  correlation matrices, autocorrelation and largest-move influence diagnostics.
- Monthly M0/M1/M2, FF5+momentum, nominal-rate sensitivities, HAC uncertainty,
  exact mean/variance identities, and refitted residual-risk/alpha contrasts.
- Separate daily market/industry models and a common short-panel market model.
- SEC accession-aware financial endpoints, latest-eligible recast operating
  histories, total investment capex/FCF and explicitly defined earnings bridges.
- All 92 established-company quarterly announcements from 2021 through cutoff;
  original GAAP earnings/margin pairs, 12 event specifications each, pooled
  two-covariate/company-intercept analysis and calendar-quarter-block intervals.
- A separate strategic-disclosure register and ELMT IPO/preferred/warrant case.
- Audited sources, exclusions, pinned dependencies, method tests and
  integration validation, including preservation of the original research.

Shared methods live in `common/code/attribution_statistics.py` and
`common/code/point_in_time.py`. Experiment orchestration lives here. No existing
shared financial utilities were replaced.

## Material limitations and declared implementation choices

1. French July2026-vintage files were downloaded September20. The regressions
   are **retrospective-vintage** estimates, not certified cutoff-vintage fits.
   No post-cutoff observations enter analysis. Risk-free-adjusted statistics
   stop in July; raw prices and eligible daily benchmark models run to cutoff.
2. FRED real-yield/credit downloads timed out. M3 and its real/credit block-order
   test are deferred. Existing nominal Treasury changes are a clearly labeled
   sensitivity. No missing factor value is set to zero.
3. Financial availability uses the next trading day after date-only filings.
   Announcement dates come from original release datelines or the 8-K report
   date. Only explicit release timestamps determine pre-open/after-close status;
   uncertain dates use the next session and have a same-date sensitivity.
4. Rolling EPS is annual + current YTD − prior YTD disclosed diluted EPS. This
   is approximate under changing weighted shares. The log-price identity is
   exact for that earnings proxy, not a causal or perfectly reconstructed EPS
   attribution. Negative/near-zero and ELMT-incomparable bridges are excluded.
5. Current actual shares and weighted-average diluted shares are kept separate.
   Fully reconciled EV bridges/multiples and ROIC are deferred. ELMT Q2 cash/debt
   are not presented as post-financing balances; contingent financing, preferred
   claims, warrants and grant-netted capex are separately identified.
6. Annual/recast and conservative as-known data are distinct. Quarter cash-flow
   differences require same-accession cumulative components; unavailable values
   remain missing. FY2021–25 MTRN mining capex is verified from original 10-Ks
   to repair changing custom XBRL tags, with explicit filing-date availability.
7. Historical consensus, guidance/backlog revisions, complete strategic-event
   coverage, historical ETF holdings and broad real-economy time series are
   deferred. They are not replaced by invented observations. Strategic rows
   record a disclosure date, not necessarily the first announcement of a deal.
8. Larger recent monthly models fail the fixed sample gates. ELMT fails the
   formal event-study history gate and full monthly models by design. Lack of
   statistical significance never causes exclusion.
9. Bootstrap intervals are approximate and pointwise. The primary four long-M2
   alpha tests receive BH adjustment. Other tables emphasize estimation rather
   than declaring a family of discoveries. Five selected firms cannot establish
   a general asset-pricing premium.

The implementation keeps all genuine jumps; second-source price checks are
complete for the archived ELMT history and selected original MTRN checks, not
every historical peer jump. This gap is visible in `large_move_audit.csv`.

Weekly aggregation checks each Friday-ending bin against the full saved SPY
session calendar. Complete opening weeks and holiday-shortened weeks are retained;
partial opening/closing bins and weeks missing any required price are excluded.
No weekly bin extends beyond its effective price or risk-free cutoff. Every TTM
component, including prior-year comparatives, records its earliest filing and
whether the selected value differs from that original vintage.

## Outputs and audit

- `data/processed/validation_results.json`: completion checks and failures.
- `data/processed/reproducibility_results.json`: recorded comparison of two
  completed offline rebuilds (104 identical CSV/JSON outputs); ten method tests
  and 28 validation checks passed. This is a completion audit, not a fresh test
  automatically performed by every single rebuild.
- `data/processed/input_hashes.csv`: archived inputs, paths and SHA-256 hashes.
- `baseline_hashes.json`: original report/input/code/protocol preservation check.
- `sources/manifest.json`: retrieval URLs, status, timestamp and hashes;
  failed earlier attempts remain in the audit alongside successful downloads.
- Link-only sources: the earnings 8-K cover documents (their parsed release exhibits
  stay local) and ELMT SEC filings not cited by path were replaced on 2026-09-21 by
  their EDGAR URLs, listed with hashes in [../../RESOURCE_LINKS.md](../../RESOURCE_LINKS.md).
- `data/processed/financial_fact_audit.csv`: selected filing accession, period,
  tag, units implied by metric, availability and assigned as-of date.
- `data/processed/earnings_extractions.json`: original table text and dateline
  evidence for each announcement; `event_exclusions.csv` records duplicates.
- `data/processed/deferrals.json`: unresolved datasets and scope decisions.
- [Data dictionary](data_dictionary.md): output definitions and units.

The source base also references immutable files under `MTRN/data` and
`MTRN/report`, rather than duplicating the original archives. Keep the experiment
inside this repository if rebuilding; the standalone HTML can be shared alone.
