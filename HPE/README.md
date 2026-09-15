# HPE — Equity research project (Bona Fide Student Investment Society)

Fundamental research on **Hewlett Packard Enterprise Company (NYSE: HPE, CIK 0001645590)**.

- Report date: 14-Sep-2026.
- Valuation: at the **11-Sep-2026 close of $62.09**.
- Output: value ranges only — no rating or price target.

## Deliverables (`final/`)

| File | What it is |
|---|---|
| `final/HPE_Investment_Research.html` | Full research report; self-contained page, also published as a private Artifact. Section 12 holds the Practitioner Q&A |
| `final/HPE_Investment_Presentation.pptx` | 25-minute investment pitch on `../Template.pptx`: 20 main slides in four parts (business model → structure vs cycle → what the price assumes → market, risks and decision), each with a takeaway line under the title (a "Conclusion" or "Pattern" headline plus the evidence behind it), including two Q3 FY26 slides (scorecard vs guidance and consensus; margin-led beat and guidance ratchet); 10 appendix slides (industry, macro, moat, capital structure, technicals, catalysts, Practitioner Q&A). Body text in the template's embedded Helvetica Neue; deck charts re-rendered in Liberation Sans. Speaker notes in every slide's notes pane |
| `final/HPE_Pitch_Speaker_Notes.md` | Speaker script for one presenter: timing plan (24:10), per-slide script, numbers to say, reasoning pattern and transition; appendix guidance; 13 prepared Q&A answers; pattern toolkit |

The report, deck and Excel workbooks were generated from the analysis outputs by builder scripts. Those scripts and the QC script were removed from `/code` after delivery, at the user's request, so `/code` holds only data analysis. Nothing is lost:
- The Excel models keep live formulas.
- The final QC results are stored in `data/processed_data/qc/qc_report.json`.

## Headline results

**Valuation**
- **Base-case DCF:** $38.80 per fully diluted share. The range is $35–43 with WACC ±0.5pp and terminal growth ±0.25pp.
- **Scenarios:** bear $22.19, bull $53.93; probability-weighted $38.43.
- **Damodaran FCFF Ginzu** (fully completed, own conventions): $31.57 per share at an 11.06% cost of capital.
- **Reverse DCF:** $62.09 requires an 18.4% long-term non-GAAP margin, a 10.8% FY27–36 revenue CAGR, or a 7.0% WACC.
- **Relative value:** peer multiples imply $67–106. That depends on today's AI-hardware sector multiples persisting.

**Statistics** (`code/statistical_analysis.py`, statsmodels)
- **ARIMA baseline** — a SARIMA fitted to FY2018–Q2 FY25 revenue:
  - backtest error 4.8%, vs 5.8% for a random walk and 8.6% for seasonal naive;
  - all 5 quarters since the Juniper close sit above its 95% band;
  - TTM revenue is +44% vs this no-structural-change counterfactual.
- **R1 — revenue growth vs cloud capex growth** (HAC OLS, n = 34):
  - capex coefficients sum to 0.19 across lags, with no lag significant at 5%;
  - Juniper quarters +15pp (p < 0.001).
- **R2 — gross-margin change vs Micron gross-margin change** (n = 31):
  - −0.046 (p = 0.002): memory-price spikes dent HPE margins only modestly;
  - Juniper quarters +6.8pp.
- **Returns:**
  - no significant autocorrelation (Ljung-Box p = 0.06);
  - strong volatility clustering (ARCH-LM p < 0.001);
  - excess kurtosis 7.0; 3σ days occur 6.8x as often as under a normal distribution.

## Repository map

```
HPE/
├── final/      deliverables only: research report (HTML), pitch deck (PPTX), pitch speaker notes (MD)
├── code/       data retrieval (one reusable fetcher) + data processing and analysis; run_all.sh
├── excel/      HPE_financial_analysis.xlsx (statements, ratios, segments, Statistics sheet)
│               HPE_valuation_model.xlsx (live-formula WACC and three DCFs, sensitivities, comps, dilution)
│               HPE_Damodaran_fcffsimpleginzu.xlsx (all sheets completed; "HPE notes" sheet sources every input)
├── report/     evidence: company_filings/ (10-K, 10-Q FY2016–FY26, 8-K, proxy, prospectuses),
│               earnings_materials/, industry_research/, macro_research/, competitor_research/,
│               other_evidence/ (IR pages, Damodaran datasets, ownership, news), source_log.csv
└── data/       financial_data/ (XBRL facts, parsed statements, keyed non-GAAP/segment tables, Form 4 XML,
                industry XBRL), market_data/ (prices, estimates, macro series),
                processed_data/ (all analysis outputs, statistics/, charts/, qc/)
```

### `/code`

| Script | Purpose |
|---|---|
| `fetch_company_data.py` | Reusable, ticker-agnostic retrieval of SEC filings, XBRL, Form 4, prices, estimates, rates and Damodaran data (raw data only) |
| `common.py`, `viz.py` | Shared paths and constants; chart style (template palette, gridlines behind marks) |
| `parse_statements.py` | Extracts IS/BS/CF from 10-K and 10-Q filings (also creates text copies) |
| `financial_analysis.py` | FY2020–FY2025 and TTM metrics, ratios, 40 reconciliation checks, charts |
| `segment_analysis.py` | Segment economics on the FY26 structure |
| `capital_structure.py` | Dilution, debt maturities, liquidity |
| `stock_analysis.py` | Returns, technical indicators (`ta`), drawdowns, big moves, correlations, Nasdaq price cross-check |
| `event_analysis.py` | Descriptive stock reaction around material events |
| `insider_ownership.py` | Form 4 insider transactions |
| `peers.py` | Peer TTM fundamentals and multiples |
| `macro_industry_analysis.py` | Hyperscaler capex and Micron margin series from cached XBRL; macro and industry charts |
| `statistical_analysis.py` | Driver regressions, SARIMA baseline and backtest, return diagnostics |
| `valuation.py` | WACC, three-scenario DCF, sensitivities, reverse DCF, comps, M&A, football field |
| `security_exposure_analysis.py` | Practitioner Q&A 1: CISA Known Exploited Vulnerabilities entries for Juniper vs other network and security vendors |
| `earnings_analysis.py` | Latest earnings: quarterly scorecard Q2 FY25–Q3 FY26, beats vs guidance and consensus, Q3 operating-profit bridge (volume vs margin), FY26 guidance ladder; every keyed figure verified against its PDF |
| `business_model_analysis.py` | Practitioner Q&A 2: landlords (DLR, KEEL) vs neoclouds (IREN, CRWV, NBIS) vs server providers (HPE, DELL) — financial profile, stylised phase-shift model, AI elasticity regressions, efficient frontier with bootstrap |

Rerun the analysis from cached data:

```bash
uv venv .venv && uv pip install --python .venv/bin/python -r code/requirements.txt
bash code/run_all.sh                 # analysis only, no network
FETCH=1 bash code/run_all.sh         # refresh raw data first (set SEC_USER_AGENT="Name email@domain")
```

## Reusing for another ticker

**1. Raw data**

```bash
python code/fetch_company_data.py --ticker NTAP --peers DELL,P --benchmarks SPY,XLK \
    --xbrl-extra MSFT,MU --since 2016-01-01 --end 2026-09-11 --all --out ../NTAP
```

Sections can be selected individually: `--sec --form4 --xbrl --prices --estimates --rates --damodaran`. Files land in the same `report/` and `data/` layout, and each source is logged in `report/source_log.csv`.

**2. Documents the fetcher does not crawl (collected by search), with the keywords that worked here**

| Need | Search keywords / source |
|---|---|
| IR documents | `"<Company> Q<q> fiscal <year> earnings presentation"`, `"<Company> earnings call transcript Q<q> <year>"`, `"<Company> securities analyst meeting slides"`; the company IR site "Quarterly results" page (PDF links follow a quarter pattern) |
| Latest results and guidance | `"<Company> reports fiscal <year> <quarter> results"` (Business Wire / company newsroom); 8-K Exhibit 99.1 via the fetcher |
| Industry size and share | servers: `"IDC Worldwide Quarterly Server Tracker <quarter>"`; networking: `"Dell'Oro campus switch <quarter>"`, `"IDC Ethernet switch tracker <quarter>"`; storage: `"IDC enterprise storage systems tracker"`; IT spend: `"Gartner forecasts worldwide IT spending <year>"` |
| Input costs | `"TrendForce DRAM contract prices <quarter>"`, `"TrendForce NAND flash contract prices"`; memory makers' XBRL (e.g. MU via `--xbrl-extra`) |
| Demand proxies | customer capex from XBRL (`--xbrl-extra MSFT,GOOGL,AMZN,META,ORCL`); `"hyperscaler capex <year> guidance"` |
| Credit | `"S&P Global Ratings <Company> outlook"`, `"Moody's <Company> rating action"` |
| Catalyst attribution for big moves | `"<TICKER> stock jumps <date>"`, `"why is <Company> stock down today"`, `"stock market today <date> <Company>"` |
| Analyst actions | `"<Company> price target raised <month year>"`, `"these analysts revise their forecasts on <Company>"`; yfinance `upgrades_downgrades` via the fetcher |
| Activism and governance | `"<Company> activist stake"`, `"<Company> cooperation agreement board"`; DEF 14A and SC 13D/G via the fetcher |
| Regulation and M&A | `"DOJ lawsuit <Company> acquisition"`, `"<Company> to acquire <target> per share premium"` |

**3. Endpoints used**
- **SEC:**
  - submissions `https://data.sec.gov/submissions/CIK##########.json`;
  - XBRL `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json`;
  - filing index `https://www.sec.gov/Archives/edgar/data/<cik>/<accession>/index.json`.
- **Prices:**
  - Yahoo chart `https://query2.finance.yahoo.com/v8/finance/chart/<TICKER>`;
  - Nasdaq `https://api.nasdaq.com/api/quote/<TICKER>/historical`.
- **Rates:** FRED `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10`.
- **Damodaran:** `https://pages.stern.nyu.edu/~adamodar/pc/datasets/` and `pc/fcffsimpleginzu.xlsx`.

## Key conventions and assumptions

- **Fiscal year and TTM:** fiscal years end 31 October. TTM Q3 FY26 = FY2025 + 9M FY2026 − 9M FY2025; the balance sheet is as of 31-Jul-2026.
- **Share count:** 1,445.2m fully diluted = 1,328m basic + 37m employee awards (treasury-stock method) + 76.1m mandatory convertible preferred as converted + 4.2m Oracle warrant (maximum).
- **DCF treatment:** SBC is treated as an expense. Financial Services is valued on a consolidated basis, with all $20.2bn of debt deducted.
- **Price adjustments:** prices are adjusted for the 2017 DXC and Micro Focus spin-offs, which data vendors book as splits of 1.3348 and 1.289.
- **Statistics:**
  - quarterly series are aligned to the calendar quarter each fiscal quarter mostly covers;
  - FY2016 quarterly XBRL revenue is excluded because it straddles the spin-off restatements;
  - regressions use Newey-West errors, and samples are short (29–34 quarters), so coefficients are indicative.
- **Evidence labels** in the report: Reported / Calculated / Estimate / Assumption / Interpretation.

## Known limitations

- Paywalled research (Gartner, IDC, Dell'Oro) is represented by public releases or press coverage.
- Consensus estimates and 13F compilations come from Yahoo Finance.
- Social-media sentiment endpoints were blocked, so that data is recorded as unavailable.
- FY26-structure segment history starts in Q1 FY25.
- The Damodaran workbook's dropdown validations were not preserved by openpyxl; the values entered match the dropdown options.
