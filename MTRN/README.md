# Materion Corporation — MTRN

The completed research is [MTRN_Investment_Research.html](final/MTRN_Investment_Research.html).
Open it in a browser. Six charts are embedded; no internet connection is required.
The [Excel model](excel/MTRN_Research_Model.xlsx) supports the report with formulas,
independent Python-calculated caches, historical data, and source references.

Market and valuation cutoff: **September 18, 2026**, close **$251.53**. Prepared and
sources retrieved September 19. Financial statements extend through July 3, 2026.
The FY2025 + H1 2026 − H1 2025 trailing calculation spans **371 days**.
The later Cboe file timestamp is preserved explicitly; the underlying trade date
matches September 18, but individual quote update times are unavailable.

## Rebuild from the saved inputs

Python 3.12 was used. From the repository root:

```bash
python3 -m venv /tmp/mtrn-research-venv
/tmp/mtrn-research-venv/bin/pip install -r MTRN/code/requirements.txt
/tmp/mtrn-research-venv/bin/python MTRN/code/run_analysis.py
```

Dependency installation requires network access; the analysis command does not.
Each script can also run separately. `run_analysis.py` executes the scripts in
dependency order and stops if an analysis or validation check fails. Validation
results are saved in `data/processed_data/validation_results.json`.

## Evidence and methodology

* `report/company_filings`: the five annual reports (validation also parses the 2025 10-K), the
  July 2026 10-Q and the 2026 proxy. Quarterly reports and 8-Ks that the report does not link to
  are link-only; see [RESOURCE_LINKS.md](RESOURCE_LINKS.md).
* Other `report/` subfolders: earnings, macro, industry, competitor and options evidence.
* `report/source_log.csv`: original URLs, archive paths, dates and source types.
* `data/financial_data`: raw SEC company facts and explicit valuation assumptions.
* `data/market_data`: saved daily OHLCV, adjusted closes and corporate-action records.
* `data/options_data`: original Cboe snapshot and normalized contracts.
* `data/processed_data`: reconciled tables, financial fact audit, manual-input audit,
  source hashes, retrieval outcomes, charts and model results.
* `code/research_template.md`: narrative with citation and calculated-table fields.
* `code/build_report.py`: generates the single final HTML artifact.
* `../common/code`: reusable financial, market, options, chart and workbook functions.

FCF subtracts both equipment capex and separately reported mine development. The
2023 mining outflow is $9.326 million. Value-added sales use comparable recast
2021–2022 figures. The model keeps GAAP, company adjustments, and analyst forecasts
distinct. Prospective DCF years end September 18, 2027–2031; terminal reinvestment
is recalculated at terminal growth. The separate 12-month price scenarios use
estimated fiscal-2027 adjusted EPS and assumed multiples.

The options snapshot fails the stated liquidity/activity policy. No MTRN strategy
or calculated higher-order Greek is presented as reliable. Generic BSM and
position-aggregation tools are provided and independently checked with finite
differences and payoff identities.

## Retrieval and historical reproducibility

SEC filings that no code parses and no report links to were replaced on September 21, 2026 by
their permanent EDGAR URLs; derived plain-text renderings were removed. Each removal is listed in
[RESOURCE_LINKS.md](RESOURCE_LINKS.md) with its URL and hash, and recorded in
`resource_changes.json`, which the validators check.

`fetch_research.py --section sec|prices|sources|options|all` is the separate
network retrieval entry point. Preserve the original evidence for this dated
report. Existing files are reused, and the saved option chain is not overwritten:
a live endpoint cannot reconstruct a historical chain. SEC fact selection excludes
filings after the cutoff, and market analysis explicitly truncates at the cutoff.
Running a new dated study requires new source snapshots, updated configuration,
and a fresh review of the narrative and assumptions; it is not just a live-price refresh.

Some direct macro downloads failed. Official-source web extracts are retained as
described in `retrieval_outcomes.csv`; the report does not imply missing PDFs were
downloaded. The image-based historical deck has a corresponding preserved web
extract. External links can change after the cutoff; archived evidence is the
reproducibility record.

The pre-existing HPE retrieval entry point delegates to the shared implementation
and retains its original HPE output default. Other HPE analyses were not modified.
