"""Historical financial analysis of HPE: FY2020 (growth base) to FY2025, plus TTM to Q3 FY26.

Source hierarchy
  1. Consolidated statements parsed from the 10-K / 10-Q filings (parse_statements.py). For each
     fiscal year the most recent 10-K presenting that year is used (captures re-presentations).
  2. SEC XBRL company facts — used only as an independent cross-check of the parsed values.
  3. Company-reported non-GAAP figures keyed from earnings releases (hpe_non_gaap_annual.csv).

TTM (four quarters to 31-Jul-2026) = FY2025 + 9M FY2026 − 9M FY2025 for flow items; balance-sheet
items are as of 31-Jul-2026.

Outputs: data/processed_data/financials/*.csv, financial_checks.csv; charts in processed_data/charts.
"""
from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd

import viz
from common import FIN_DATA, PROC

OUT = PROC / "financials"
OUT.mkdir(exist_ok=True)
YEARS = [2020, 2021, 2022, 2023, 2024, 2025]
TTM = "TTM Q3 FY26"
Q3_10Q = "HPE_10-Q_FY2026Q3_2026-07-31"

LONG = pd.read_csv(FIN_DATA / "hpe_statements_long.csv")

# metric -> (statement, label regex, optional section regex)
MAP = {
    "revenue": ("IS", r"^(Total net revenue|Net revenue)$", None),
    "rev_products": ("IS", r"^Products$", None),
    "rev_services": ("IS", r"^Services$", None),
    "rev_financing": ("IS", r"^Financing income$", None),
    "cost_products": ("IS", r"^Cost of products", None),
    "cost_services": ("IS", r"^Cost of services", None),
    "financing_cost": ("IS", r"^Financing (cost|interest)$", None),
    "cost_of_sales_direct": ("IS", r"^Cost of sales", None),
    "rd": ("IS", r"^Research and development$", None),
    "sga": ("IS", r"^Selling, general and administrative$", None),
    "amortization": ("IS", r"^Amortization of intangible assets$", None),
    "impairment": ("IS", r"^Impairment (charges|of goodwill)", None),
    "transformation": ("IS", r"^Transformation costs$", None),
    "disaster": ("IS", r"^Disaster charges", None),
    "acq_dispo": ("IS", r"^Acquisition, disposition and other", None),
    "operating_income": ("IS", r"from (continuing )?operations$", None),
    "pretax_income": ("IS", r"before .*taxes$", None),
    "net_income": ("IS", r"^Net (earnings|\(loss\) earnings|earnings \(loss\))( attributable to HPE)?$", None),
    "preferred_dividends": ("IS", r"^Preferred stock dividends$", None),
    "eps_diluted": ("IS", r"^Diluted$", r"(?i)per share"),
    "shares_basic": ("IS", r"^Basic$", r"(?i)shares used"),
    "shares_diluted": ("IS", r"^Diluted$", r"(?i)shares used"),
    # balance sheet
    "cash": ("BS", r"^Cash and cash equivalents$", None),
    "accounts_receivable": ("BS", r"^Accounts receivable", None),
    "financing_receivables_current": ("BS", r"^Financing receivables", None),
    "inventory": ("BS", r"^Inventory$", None),
    "current_assets": ("BS", r"^Total current assets$", None),
    "lt_financing_receivables_other": ("BS", r"^Long-term financing receivables", None),
    "equity_investments": ("BS", r"^Investments in equity interests$", None),
    "goodwill": ("BS", r"^Goodwill$", None),
    "intangibles": ("BS", r"^Intangible assets", None),
    "goodwill_and_intangibles": ("BS", r"^Goodwill and intangible assets$", None),
    "total_assets": ("BS", r"^Total assets$", None),
    "short_term_debt": ("BS", r"^Notes payable and short-term borrowings$", None),
    "accounts_payable": ("BS", r"^Accounts payable$", None),
    "deferred_revenue": ("BS", r"^Deferred revenue$", None),
    "current_liabilities": ("BS", r"^Total current liabilities$", None),
    "long_term_debt": ("BS", r"^Long-term debt$", None),
    "hpe_equity": ("BS", r"^Total HPE stockholders' equity$", None),
    "total_equity": ("BS", r"^Total stockholders' equity$", None),
    "total_liabilities_and_equity": ("BS", r"^Total liabilities and stockholders' equity$", None),
    # cash flow
    "cfo": ("CF", r"^Net cash provided by operating activities$", None),
    "d_and_a": ("CF", r"^Depreciation and amortization$", None),
    "sbc": ("CF", r"^Stock-based compensation expense$", None),
    "capex_gross": ("CF", r"^Investment in property, plant and equipment", None),
    "ppe_proceeds": ("CF", r"^Proceeds from sale of property, plant and equipment$", None),
    "fx_effect": ("CF", r"^Effect of exchange rate changes", None),
    "acquisitions": ("CF", r"^Payments made in connection with business acquisitions", None),
    "buybacks": ("CF", r"^Repurchases? of common stock$", None),
    "dividends_common": ("CF", r"^Cash dividends paid to (common stockholders|shareholders)$", None),
    "dividends_preferred": ("CF", r"^Cash dividends paid to preferred", None),
    "debt_issued": ("CF", r"^Proceeds from debt", None),
    "debt_repaid": ("CF", r"^Payment of debt$", None),
    "preferred_issued": ("CF", r"^Proceeds from issuance of 7\.625", None),
    "wc_receivables": ("CF", r"^Accounts receivable$", None),
    "wc_financing_receivables": ("CF", r"^Financing receivables$", None),
    "wc_inventory": ("CF", r"^Inventory$", None),
    "wc_payables": ("CF", r"^Accounts payable$", None),
    "interest_paid": ("CF", r"^Interest expense paid$", None),
}

# Q3 FY26 press-release values for items the condensed 10-Q cash-flow statement parse does not
# cover (source: HPE Q3 FY26 earnings press release, pp. 13-16; report/earnings_materials/FY2026Q3)
Q3_RELEASE_9M = {
    "cfo": (4229, 454), "d_and_a": (2613, 1860), "sbc": (599, 447), "capex_gross": (-1897, -1651),
    "ppe_proceeds": (288, 254), "fx_effect": (-39, 9), "acquisitions": (0, -12278), "buybacks": (-447, -102),
    "dividends_common": (-568, -513), "dividends_preferred": (-87, -83), "debt_issued": (2546, 5333),
    "debt_repaid": (-4686, -1663), "wc_receivables": (-997, -1130), "wc_financing_receivables": (-224, -3),
    "wc_inventory": (-5847, 1385), "wc_payables": (5870, -2595), "preferred_issued": (0, 0),
}


def pick(metric: str, period: str, forms=("10-K",)) -> float:
    st, pattern, section = MAP[metric]
    d = LONG[(LONG.statement == st) & (LONG.period == period) & LONG.form.isin(forms)]
    for filing in sorted(d.filing.unique(), reverse=True):
        rows = d[(d.filing == filing) & d.label.str.contains(pattern, regex=True)]
        if section:
            rows = rows[rows.section.fillna("").str.contains(section, regex=True)]
        if not rows.empty:
            return float(rows.value.iloc[0])
    return np.nan


def annual_table() -> pd.DataFrame:
    data = {}
    for fy in YEARS:
        col = {m: pick(m, f"FY{fy}") for m in MAP}
        data[f"FY{fy}"] = col
    df = pd.DataFrame(data)

    # TTM: FY2025 + 9M FY26 - 9M FY25 (flows); 31-Jul-2026 balance sheet
    ttm = {}
    for m, (st, _, _) in MAP.items():
        if st == "BS":
            ttm[m] = pick(m, "July 31, 2026", forms=("10-Q",))
        elif st == "IS":
            cur, prev = pick(m, "9M_2026", ("10-Q",)), pick(m, "9M_2025", ("10-Q",))
            ttm[m] = df.at[m, "FY2025"] + cur - prev if not (np.isnan(cur) or np.isnan(prev)) else np.nan
        else:  # prefer the parsed 10-Q cash-flow statement; fall back to the press-release values
            cur, prev = pick(m, "9M_2026", ("10-Q",)), pick(m, "9M_2025", ("10-Q",))
            if np.isnan(cur) or np.isnan(prev):
                cur, prev = Q3_RELEASE_9M.get(m, (np.nan, np.nan))
            ttm[m] = df.at[m, "FY2025"] + cur - prev
    df[TTM] = pd.Series(ttm)
    # TTM share counts / EPS are not additive: use Q3 FY26 quarter share count and sum of quarterly EPS
    df.at["shares_diluted", TTM] = pick("shares_diluted", "3M_2026", ("10-Q",))
    df.at["shares_basic", TTM] = pick("shares_basic", "3M_2026", ("10-Q",))
    df.at["eps_diluted", TTM] = np.nan
    return df


def derive(df: pd.DataFrame) -> pd.DataFrame:
    f = df.copy()
    z = lambda m: f.loc[m].fillna(0)
    cos_split = z("cost_products") + z("cost_services") + z("financing_cost")
    f.loc["cost_of_sales"] = np.where(f.loc["cost_of_sales_direct"].notna(), f.loc["cost_of_sales_direct"], cos_split)
    f.loc["gross_profit"] = f.loc["revenue"] - f.loc["cost_of_sales"]
    f.loc["goodwill_and_intangibles"] = f.loc["goodwill_and_intangibles"].fillna(z("goodwill") + z("intangibles"))
    f.loc["gross_debt"] = z("short_term_debt") + z("long_term_debt")
    f.loc["net_debt"] = f.loc["gross_debt"] - f.loc["cash"]
    f.loc["special_items"] = z("impairment") + z("transformation") + z("disaster") + z("acq_dispo")
    f.loc["ebitda"] = f.loc["operating_income"] + f.loc["d_and_a"]
    # Analyst adjusted EBITDA: GAAP OP + D&A + SBC + impairment/transformation/acquisition charges
    f.loc["adj_ebitda_analyst"] = f.loc["ebitda"] + z("sbc") + f.loc["special_items"]
    f.loc["adj_operating_income_analyst"] = f.loc["operating_income"] + z("amortization") + z("sbc") + f.loc["special_items"]
    f.loc["capex_net"] = f.loc["capex_gross"] + z("ppe_proceeds")          # negative = outflow
    f.loc["fcf_hpe_definition"] = f.loc["cfo"] + f.loc["capex_net"] + z("fx_effect")
    f.loc["fcf_simple"] = f.loc["cfo"] + f.loc["capex_net"]
    f.loc["capital_returned"] = -(z("buybacks") + z("dividends_common"))
    return f


def ratios(f: pd.DataFrame) -> pd.DataFrame:
    cols = list(f.columns)
    r = pd.DataFrame(index=[], columns=cols, dtype=float)
    rev = f.loc["revenue"]
    fy_cols = [c for c in cols if c.startswith("FY")]
    r.loc["revenue_growth_yoy"] = rev[fy_cols].pct_change()
    r.loc["gross_margin"] = f.loc["gross_profit"] / rev
    r.loc["operating_margin"] = f.loc["operating_income"] / rev
    r.loc["adj_operating_margin_analyst"] = f.loc["adj_operating_income_analyst"] / rev
    r.loc["ebitda_margin"] = f.loc["ebitda"] / rev
    r.loc["adj_ebitda_margin_analyst"] = f.loc["adj_ebitda_analyst"] / rev
    r.loc["net_margin"] = f.loc["net_income"] / rev
    r.loc["rd_pct_revenue"] = f.loc["rd"] / rev
    r.loc["sga_pct_revenue"] = f.loc["sga"] / rev
    r.loc["fcf_margin"] = f.loc["fcf_hpe_definition"] / rev
    r.loc["fcf_conversion_of_net_income"] = f.loc["fcf_hpe_definition"] / f.loc["net_income"]
    r.loc["cfo_to_adj_ebitda"] = f.loc["cfo"] / f.loc["adj_ebitda_analyst"]
    r.loc["capex_net_pct_revenue"] = -f.loc["capex_net"] / rev
    r.loc["sbc_pct_revenue"] = f.loc["sbc"] / rev
    r.loc["current_ratio"] = f.loc["current_assets"] / f.loc["current_liabilities"]
    r.loc["debt_to_equity"] = f.loc["gross_debt"] / f.loc["total_equity"]
    r.loc["net_debt_to_adj_ebitda"] = f.loc["net_debt"] / f.loc["adj_ebitda_analyst"]
    r.loc["goodwill_intangibles_pct_assets"] = f.loc["goodwill_and_intangibles"] / f.loc["total_assets"]
    r.loc["dso_days"] = f.loc["accounts_receivable"] / rev * 365
    r.loc["dio_days"] = f.loc["inventory"] / f.loc["cost_of_sales"] * 365
    r.loc["dpo_days"] = f.loc["accounts_payable"] / f.loc["cost_of_sales"] * 365
    r.loc["cash_conversion_cycle_days"] = r.loc["dso_days"] + r.loc["dio_days"] - r.loc["dpo_days"]
    r.loc["diluted_share_change_yoy"] = f.loc["shares_diluted"][fy_cols].pct_change()
    r.loc["revenue_per_diluted_share"] = rev / f.loc["shares_diluted"]
    r.loc["fcf_per_diluted_share"] = f.loc["fcf_hpe_definition"] / f.loc["shares_diluted"]
    r.loc["book_value_per_diluted_share"] = f.loc["hpe_equity"] / f.loc["shares_diluted"]
    r.loc["payout_of_fcf"] = f.loc["capital_returned"] / f.loc["fcf_hpe_definition"]
    # simple ROIC: after-tax adjusted operating income / (equity + gross debt - cash), 15% tax assumption
    invested = f.loc["total_equity"] + f.loc["gross_debt"] - f.loc["cash"]
    r.loc["roic_adj_after_tax_15pct"] = f.loc["adj_operating_income_analyst"] * 0.85 / invested
    r.loc["roic_gaap_after_tax_15pct"] = f.loc["operating_income"] * 0.85 / invested
    return r


def cagr(series: pd.Series, start: str, end: str) -> float:
    n = int(end[2:]) - int(start[2:])
    return (series[end] / series[start]) ** (1 / n) - 1


def checks(f: pd.DataFrame) -> pd.DataFrame:
    """Cross-check parsed statement values against SEC XBRL facts, and internal identities."""
    facts = json.loads((FIN_DATA / "companyfacts_HPE.json").read_text())["facts"]["us-gaap"]
    tags = {"revenue": "Revenues", "operating_income": "OperatingIncomeLoss", "cfo": "NetCashProvidedByUsedInOperatingActivities",
            "cash": "CashAndCashEquivalentsAtCarryingValue", "total_assets": "Assets"}
    rows = []
    for metric, tag in tags.items():
        vals = facts[tag]["units"]["USD"]
        for fy in YEARS[1:]:
            end = f"{fy}-10-31"
            cand = [v for v in vals if v["end"] == end and v.get("form") == "10-K"
                    and ("start" not in v or v["start"][:4] == str(fy - 1))]
            if not cand:
                continue
            xbrl = sorted(cand, key=lambda v: v["filed"])[-1]["val"] / 1e6
            parsed = f.at[metric, f"FY{fy}"]
            rows.append(dict(check=f"{metric} FY{fy}: parsed vs XBRL", parsed=parsed, reference=xbrl,
                             diff_pct=abs(parsed / xbrl - 1), passed=abs(parsed / xbrl - 1) <= 0.005))
    for col in f.columns:
        ta, tle = f.at["total_assets", col], f.at["total_liabilities_and_equity", col]
        if not np.isnan(tle):
            rows.append(dict(check=f"balance sheet balances {col}", parsed=ta, reference=tle,
                             diff_pct=abs(ta / tle - 1), passed=abs(ta - tle) < 1))
    # Q3 FY26 press release anchors for TTM inputs (9M FY26 revenue 32,192; 9M FY25 24,617)
    rows.append(dict(check="TTM revenue = FY25 + 9M26 - 9M25", parsed=f.at["revenue", TTM],
                     reference=34296 + 32192 - 24617, diff_pct=0.0,
                     passed=abs(f.at["revenue", TTM] - (34296 + 32192 - 24617)) < 1))
    ng = FIN_DATA / "hpe_non_gaap_annual.csv"
    if ng.exists():
        nga = pd.read_csv(ng)
        for _, row in nga[nga.metric == "free_cash_flow_reported"].iterrows():
            col = row["period"]
            if col in f.columns:
                explained = isinstance(row["note"], str) and row["note"].startswith("Explained")
                rows.append(dict(check=f"FCF (HPE definition) {col} vs company-reported", parsed=f.at["fcf_hpe_definition", col],
                                 reference=row["value"], diff_pct=abs(f.at["fcf_hpe_definition", col] / row["value"] - 1),
                                 passed=abs(f.at["fcf_hpe_definition", col] - row["value"]) <= 25 or explained,
                                 note="explained difference (see hpe_non_gaap_annual.csv)" if explained else ""))
    return pd.DataFrame(rows)


def charts(f: pd.DataFrame, r: pd.DataFrame, ng: pd.DataFrame | None) -> None:
    cols = list(f.columns)
    labels = [c.replace("TTM Q3 FY26", "TTM\nQ3 FY26") for c in cols]
    x = np.arange(len(cols))

    # Revenue with growth labels (single series; growth as text, no second axis)
    fig, ax = viz.figure(8, 3.4)
    rev = f.loc["revenue"] / 1000
    colors = [viz.GREEN] * (len(cols) - 1) + [viz.GOLD]
    ax.bar(x, rev, width=0.55, color=colors)
    for i, c in enumerate(cols):
        g = r.at["revenue_growth_yoy", c] if c != TTM else f.at["revenue", TTM] / f.at["revenue", "FY2025"] - 1
        lab = f"${rev[c]:.1f}bn" + ("" if np.isnan(g) else f"\n{g:+.0%}" + (" vs FY25" if c == TTM else ""))
        ax.text(i, rev[c] + 0.4, lab, ha="center", va="bottom", fontsize=7.5, color=viz.INK2)
    ax.set_xticks(x, labels)
    ax.set_ylim(0, rev.max() * 1.25)
    ax.set_ylabel("$bn")
    viz.titles(ax, "Revenue was flat for four years, then Juniper and AI demand re-rated growth",
               "Net revenue, fiscal years ending 31 October; TTM to 31-Jul-2026 in gold")
    viz.source(fig, "HPE 10-K FY2020–FY2025, 10-Q Q3 FY26; Bona Fide analysis.")
    viz.save(fig, "fin_revenue")

    # Margins: GAAP gross, GAAP operating, adjusted operating (analyst) and company non-GAAP where available
    fig, ax = viz.figure(8, 3.4)
    series = [("gross_margin", "GAAP gross margin", viz.GREEN), ("non_gaap_operating_margin", "Non-GAAP operating margin (company)", viz.GOLD),
              ("operating_margin", "GAAP operating margin", viz.BLUE)]
    for key, lab, col in series:
        ax.plot(x, r.loc[key], color=col, marker="o", ms=5, label=lab)
        viz.end_label(ax, x[-1], r.at[key, TTM], f"{r.at[key, TTM]:.1%}", dx=8)
    ax.axhline(0, color=viz.AXIS, lw=0.8, zorder=1)
    ax.set_xticks(x, labels)
    viz.pct_axis(ax)
    ax.legend(loc="center left", bbox_to_anchor=(0, 0.62))
    viz.titles(ax, "Margins troughed in FY25 on Juniper costs and impairments, then rebounded",
               "GAAP gross and operating margin vs company non-GAAP operating margin (ex SBC, amortisation, special items)")
    viz.source(fig, "HPE 10-K/10-Q; Bona Fide analysis.")
    viz.save(fig, "fin_margins")

    # Free cash flow with margin labels
    fig, ax = viz.figure(8, 3.2)
    fcf = f.loc["fcf_hpe_definition"] / 1000
    ax.bar(x, fcf, width=0.55, color=[viz.GREEN if v >= 0 else viz.CONTEXT for v in fcf])
    for i, c in enumerate(cols):
        ax.text(i, fcf[c] + (0.1 if fcf[c] >= 0 else -0.1), f"${fcf[c]:.1f}bn\n{r.at['fcf_margin', c]:.1%}",
                ha="center", va="bottom" if fcf[c] >= 0 else "top", fontsize=7.5, color=viz.INK2)
    ax.axhline(0, color=viz.AXIS, lw=0.8, zorder=1)
    ax.set_xticks(x, labels)
    ax.set_ylim(min(0, fcf.min()) - 0.6, fcf.max() * 1.35)
    ax.set_ylabel("$bn")
    viz.titles(ax, "Free cash flow collapsed in FY25 and is recovering with working capital",
               "Free cash flow (HPE definition: CFO − net capex ± FX) and FCF margin")
    viz.source(fig, "HPE 10-K/10-Q, Q3 FY26 press release; Bona Fide analysis.")
    viz.save(fig, "fin_fcf")

    # Debt vs cash (grouped bars, 2 series)
    fig, ax = viz.figure(8, 3.2)
    w = 0.3
    ax.bar(x - w / 2 - 0.01, f.loc["gross_debt"] / 1000, width=w, color=viz.GREEN, label="Gross debt (incl. Financial Services)")
    ax.bar(x + w / 2 + 0.01, f.loc["cash"] / 1000, width=w, color=viz.GOLD, label="Cash & equivalents")
    for i, c in enumerate(cols):
        ax.text(i, max(f.at["gross_debt", c], f.at["cash", c]) / 1000 + 0.5, f"Net ${f.at['net_debt', c] / 1000:.1f}bn",
                ha="center", fontsize=7.5, color=viz.INK2)
    ax.set_xticks(x, labels)
    ax.set_ylabel("$bn")
    ax.legend(loc="upper left")
    viz.titles(ax, "Juniper doubled gross debt; deleveraging is under way",
               "Gross debt (short- and long-term) vs cash; year-end balances and 31-Jul-2026")
    viz.source(fig, "HPE 10-K/10-Q; Bona Fide analysis.")
    viz.save(fig, "fin_debt_cash")

    # Working capital days (3 series)
    fig, ax = viz.figure(8, 3.0)
    for key, lab, col in [("dso_days", "DSO", viz.GREEN), ("dio_days", "DIO", viz.GOLD), ("dpo_days", "DPO", viz.BLUE)]:
        ax.plot(x, r.loc[key], color=col, marker="o", ms=5, label=lab)
    ax.set_xticks(x, labels)
    ax.set_ylabel("days")
    ax.legend(loc="upper left", ncol=3)
    viz.titles(ax, "AI backlog build is financed by suppliers: inventory and payables both jumped",
               "Year-end days sales outstanding, inventory and payables (on cost of sales)")
    viz.source(fig, "HPE 10-K/10-Q; Bona Fide analysis. Point-in-time balances; TTM uses 31-Jul-2026 balances.")
    viz.save(fig, "fin_working_capital")

    # SBC and diluted shares (two small panels, one scale each)
    fig, (a1, a2) = viz.figure(8, 4.0, nrows=2, sharex=True)
    a1.bar(x, f.loc["sbc"], width=0.55, color=viz.GREEN)
    for i, c in enumerate(cols):
        a1.text(i, f.at["sbc", c] + 15, f"{r.at['sbc_pct_revenue', c]:.1%} of rev", ha="center", fontsize=7, color=viz.INK2)
    a1.set_ylabel("SBC $m")
    a1.set_ylim(0, f.loc["sbc"].max() * 1.3)
    viz.titles(a1, "SBC is modest (~2% of revenue); dilution is driven by the preferred, not employees",
               "Stock-based compensation ($m) and weighted-average diluted shares (m)")
    a2.plot(x, f.loc["shares_diluted"], color=viz.GOLD, marker="o", ms=5)
    a2.set_ylabel("Diluted shares (m)")
    a2.set_xticks(x, labels)
    viz.source(fig, "HPE 10-K/10-Q; Bona Fide analysis. TTM share count = Q3 FY26 diluted weighted average.")
    viz.save(fig, "fin_sbc_shares")


def main() -> None:
    raw = annual_table()
    f = derive(raw)
    r = ratios(f)
    r.at["revenue_growth_yoy", TTM] = np.nan

    ng_path = FIN_DATA / "hpe_non_gaap_annual.csv"
    ng = pd.read_csv(ng_path) if ng_path.exists() else None
    if ng is not None:  # company-reported non-GAAP figures alongside the GAAP statements
        ngw = ng.pivot_table(index="metric", columns="period", values="value", aggfunc="first")
        for m in ngw.index:
            f.loc[m] = ngw.loc[m].reindex(f.columns)
        r.loc["non_gaap_gross_margin"] = f.loc["non_gaap_gross_profit"] / f.loc["revenue"]
        r.loc["non_gaap_operating_margin"] = f.loc["non_gaap_operating_profit"] / f.loc["revenue"]
        r.loc["gaap_to_non_gaap_operating_gap"] = (f.loc["non_gaap_operating_profit"] - f.loc["operating_income"]) / f.loc["revenue"]
        r.loc["adj_ebitda_company_basis"] = f.loc["non_gaap_operating_profit"] + f.loc["d_and_a"] - f.loc["amortization"]
        r.loc["adj_ebitda_company_basis_margin"] = r.loc["adj_ebitda_company_basis"] / f.loc["revenue"]

    growth = {
        "revenue_cagr_FY2020_FY2025": cagr(f.loc["revenue"], "FY2020", "FY2025"),
        "revenue_cagr_FY2021_FY2025": cagr(f.loc["revenue"], "FY2021", "FY2025"),
        "revenue_cagr_FY2020_FY2024": cagr(f.loc["revenue"], "FY2020", "FY2024"),
        "ttm_revenue_growth_vs_FY2025": f.at["revenue", TTM] / f.at["revenue", "FY2025"] - 1,
        "ttm_vs_prior_ttm_revenue_growth": (32192 / 24617) - 1,  # 9M FY26 vs 9M FY25 (press release)
    }
    f.to_csv(OUT / "hpe_financials.csv")
    r.to_csv(OUT / "hpe_ratios.csv")
    (OUT / "growth_summary.json").write_text(json.dumps({k: round(v, 4) for k, v in growth.items()}, indent=2))
    chk = checks(f)
    chk.to_csv(OUT / "financial_checks.csv", index=False)
    charts(f, r, ng)

    pd.set_option("display.width", 220, "display.max_rows", 200)
    show = ["revenue", "gross_profit", "operating_income", "adj_operating_income_analyst", "net_income", "d_and_a", "sbc",
            "ebitda", "adj_ebitda_analyst", "cfo", "capex_net", "fcf_hpe_definition", "cash", "gross_debt", "net_debt",
            "current_assets", "current_liabilities", "total_equity", "goodwill_and_intangibles", "inventory",
            "accounts_payable", "shares_diluted", "buybacks", "dividends_common", "acquisitions"]
    print(f.loc[show].round(0))
    print((r * 1).round(3))
    print(json.dumps(growth, indent=1))
    print(chk.to_string())
    if not chk.passed.all():
        print("WARNING: some checks failed")


if __name__ == "__main__":
    main()
