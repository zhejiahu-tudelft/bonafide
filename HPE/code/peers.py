"""Peer benchmarking: TTM fundamentals from SEC XBRL, market values at the valuation date.

Peers (selected by revenue overlap with HPE's segments):
  AI / servers: Dell (DELL), Supermicro (SMCI) · Networking: Cisco (CSCO), Arista (ANET)
  Storage / hybrid cloud: NetApp (NTAP), Everpure (ex-Pure Storage, P)

TTM = last four reported fiscal quarters (quarterly values derived from year-to-date XBRL facts).
Market capitalisation = 11-Sep-2026 close × latest dei:EntityCommonStockSharesOutstanding.
Forward (NTM-proxy) estimates are consensus figures from Yahoo Finance (secondary source).

Outputs: data/processed_data/peers/peer_fundamentals.csv, peer_multiples.csv; charts.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import viz
from common import FIN_DATA, MKT_DATA, PEER_NAMES, PEERS, PROC, VALUATION_DATE

OUT = PROC / "peers"
OUT.mkdir(exist_ok=True)

TAGS = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"],
    "cost_of_revenue": ["CostOfGoodsAndServicesSold", "CostOfRevenue"],
    "gross_profit": ["GrossProfit"],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss"],
    "cfo": ["NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
    "d_and_a": ["DepreciationDepletionAndAmortization", "DepreciationAmortizationAndAccretionNet",
                "DepreciationAndAmortization"],
    "sbc": ["ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"],
    "rd": ["ResearchAndDevelopmentExpense"],
}
INSTANT = {
    "cash": ["CashAndCashEquivalentsAtCarryingValue"],
    "st_investments": ["ShortTermInvestments", "AvailableForSaleSecuritiesDebtSecuritiesCurrent", "MarketableSecuritiesCurrent"],
    "debt_current": ["LongTermDebtCurrent", "DebtCurrent", "ShortTermBorrowings", "CommercialPaper"],
    "debt_noncurrent": ["LongTermDebtNoncurrent", "LongTermDebtAndCapitalLeaseObligations"],
    "equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
}


def facts(tk: str) -> dict:
    return json.loads((FIN_DATA / f"companyfacts_{tk}.json").read_text())["facts"]


def usd_values(f: dict, tags: list[str]) -> list[dict] | None:
    best = None
    for tag in tags:
        node = f.get("us-gaap", {}).get(tag)
        if node and "USD" in node["units"]:
            vals = [v for v in node["units"]["USD"] if v.get("form") in ("10-Q", "10-K")]
            if vals and (best is None or max(v["end"] for v in vals) > max(v["end"] for v in best)):
                best = vals
    return best


def quarterly(vals: list[dict]) -> pd.Series:
    df = pd.DataFrame([v for v in vals if "start" in v])
    df["start"], df["end"] = pd.to_datetime(df["start"]), pd.to_datetime(df["end"])
    df = df.sort_values("filed").drop_duplicates(["start", "end"], keep="last")
    df["days"] = (df["end"] - df["start"]).dt.days
    out = {}
    for _, grp in df.groupby("start"):
        prev = 0.0
        for _, row in grp.sort_values("end").iterrows():
            if row["days"] > 380:
                break
            out.setdefault(row["end"], row["val"] - prev)
            prev = row["val"]
    return pd.Series(out).sort_index()


def ttm(vals: list[dict] | None) -> tuple[float, str]:
    if not vals:
        return np.nan, ""
    q = quarterly(vals)
    q = q[q.index <= pd.Timestamp(VALUATION_DATE)]
    last4 = q.iloc[-4:]
    # require four consecutive quarters (~1 year span)
    if len(last4) < 4 or (last4.index[-1] - last4.index[0]).days > 300:
        return np.nan, ""
    return last4.sum() / 1e6, str(last4.index[-1].date())


def latest_instant(f: dict, tags: list[str]) -> float:
    vals = usd_values(f, tags)
    if not vals:
        return 0.0
    inst = [v for v in vals if "start" not in v and v["end"] <= VALUATION_DATE]
    if not inst:
        return 0.0
    last_end = max(v["end"] for v in inst)
    return sorted([v for v in inst if v["end"] == last_end], key=lambda v: v["filed"])[-1]["val"] / 1e6


def shares_outstanding(f: dict, tk: str) -> float:
    node = f.get("dei", {}).get("EntityCommonStockSharesOutstanding")
    if node is None:  # e.g. multi-class issuers without the dei cover-page fact: use Yahoo implied shares
        info = json.loads((MKT_DATA / "yahoo" / f"yahoo_{tk}_info.json").read_text())
        return (info.get("impliedSharesOutstanding") or info["sharesOutstanding"]) / 1e6
    vals = [v for v in node["units"]["shares"] if v["end"] <= VALUATION_DATE]
    last_end = max(v["end"] for v in vals)
    # multi-class issuers (e.g. Dell Class A/B/C) report one fact per class: sum them
    return sum(v["val"] for v in vals if v["end"] == last_end and v["filed"] == max(
        x["filed"] for x in vals if x["end"] == last_end)) / 1e6


def close_on_valuation_date(tk: str) -> float:
    px = pd.read_csv(MKT_DATA / f"{tk}_daily.csv", parse_dates=["date"]).set_index("date")
    return float(px.loc[:VALUATION_DATE, "close"].iloc[-1])


def consensus(tk: str) -> dict:
    out = {}
    try:
        eps = pd.read_csv(MKT_DATA / "yahoo" / f"yahoo_{tk}_earnings_estimate.csv", index_col=0)
        rev = pd.read_csv(MKT_DATA / "yahoo" / f"yahoo_{tk}_revenue_estimate.csv", index_col=0)
        out = {"eps_next_fy": eps.at["+1y", "avg"], "eps_current_fy": eps.at["0y", "avg"],
               "revenue_next_fy": rev.at["+1y", "avg"] / 1e6, "revenue_current_fy": rev.at["0y", "avg"] / 1e6}
    except (FileNotFoundError, KeyError):
        pass
    return out


def hpe_row() -> dict:
    """HPE from the filing-based analysis (financial_analysis.py) for consistency."""
    fin = pd.read_csv(PROC / "financials" / "hpe_financials.csv", index_col=0)["TTM Q3 FY26"]
    return {"revenue": fin["revenue"], "gross_profit": fin["gross_profit"], "operating_income": fin["operating_income"],
            "net_income": fin["net_income"], "cfo": fin["cfo"], "capex": -fin["capex_net"], "d_and_a": fin["d_and_a"],
            "sbc": fin["sbc"], "rd": fin["rd"], "cash": fin["cash"], "st_investments": 0.0,
            "debt_current": fin["short_term_debt"], "debt_noncurrent": fin["long_term_debt"], "equity": fin["total_equity"],
            "ttm_end": "2026-07-31", "non_gaap_operating_income": fin.get("non_gaap_operating_profit", np.nan)}


def main() -> None:
    rows = {}
    for tk in ["HPE", *PEERS]:
        if tk == "HPE":
            row = hpe_row()
            row["shares_out"] = 1328.0  # common shares outstanding 31-Jul-2026 (Q3 FY26 balance sheet)
        else:
            f = facts(tk)
            row = {}
            for m, tags in TAGS.items():
                row[m], end = ttm(usd_values(f, tags))
                if m == "revenue":
                    row["ttm_end"] = end
            if np.isnan(row.get("gross_profit", np.nan)) and not np.isnan(row.get("cost_of_revenue", np.nan)):
                row["gross_profit"] = row["revenue"] - row["cost_of_revenue"]
            for m, tags in INSTANT.items():
                row[m] = latest_instant(f, tags)
            row["shares_out"] = shares_outstanding(f, tk)
        row["price"] = close_on_valuation_date(tk)
        row.update(consensus(tk))
        rows[tk] = row
    df = pd.DataFrame(rows).T
    num = df.drop(columns=["ttm_end"]).apply(pd.to_numeric, errors="coerce")
    num["market_cap"] = num["price"] * num["shares_out"]
    num["total_debt"] = num["debt_current"].fillna(0) + num["debt_noncurrent"].fillna(0)
    num["cash_total"] = num["cash"].fillna(0) + num["st_investments"].fillna(0)
    num["enterprise_value"] = num["market_cap"] + num["total_debt"] - num["cash_total"]
    num["ebitda"] = num["operating_income"] + num["d_and_a"]
    num["fcf"] = num["cfo"] - num["capex"].abs()
    m = pd.DataFrame(index=num.index)
    m["Company"] = [PEER_NAMES.get(t, t) for t in num.index]
    m["TTM end"] = df["ttm_end"]
    m["Market cap ($bn)"] = num["market_cap"] / 1000
    m["EV ($bn)"] = num["enterprise_value"] / 1000
    m["TTM revenue ($bn)"] = num["revenue"] / 1000
    m["Revenue growth (next FY, cons.)"] = num["revenue_next_fy"] / num["revenue_current_fy"] - 1
    m["Gross margin"] = num["gross_profit"] / num["revenue"]
    m["Operating margin (GAAP)"] = num["operating_income"] / num["revenue"]
    m["FCF margin"] = num["fcf"] / num["revenue"]
    m["R&D % revenue"] = num["rd"] / num["revenue"]
    m["SBC % revenue"] = num["sbc"] / num["revenue"]
    m["Net debt / EBITDA"] = (num["total_debt"] - num["cash_total"]) / num["ebitda"]
    m["P/E (TTM GAAP)"] = num["market_cap"] / num["net_income"]
    m["P/E (next FY cons.)"] = num["price"] / num["eps_next_fy"]
    m["P/S (TTM)"] = num["market_cap"] / num["revenue"]
    m["P/B"] = num["market_cap"] / num["equity"]
    m["EV/Revenue (TTM)"] = num["enterprise_value"] / num["revenue"]
    m["EV/EBITDA (TTM GAAP)"] = num["enterprise_value"] / num["ebitda"]
    m["EV/EBIT (TTM GAAP)"] = num["enterprise_value"] / num["operating_income"]
    m["EV/Revenue (next FY cons.)"] = num["enterprise_value"] / num["revenue_next_fy"]
    m["FCF yield"] = num["fcf"] / num["market_cap"]
    num.to_csv(OUT / "peer_fundamentals.csv")
    m.to_csv(OUT / "peer_multiples.csv")

    # Chart: growth vs margin positioning (scatter would need >3 colours -> use emphasis)
    fig, ax = viz.figure(8, 3.8)
    for tk in m.index:
        x, y = m.at[tk, "Operating margin (GAAP)"], m.at[tk, "EV/Revenue (TTM)"]
        if np.isnan(x) or np.isnan(y):
            continue
        is_hpe = tk == "HPE"
        ax.scatter(x, y, s=90 if is_hpe else 60, color=viz.GREEN if is_hpe else viz.CONTEXT,
                   edgecolor=viz.SURFACE, linewidth=2, zorder=3)
        ax.annotate(m.at[tk, "Company"].split(" (")[0], (x, y), xytext=(6, 4), textcoords="offset points",
                    fontsize=8, color=viz.INK if is_hpe else viz.INK2)
    viz.pct_axis(ax)
    ax.set_xlabel("TTM GAAP operating margin")
    ax.set_ylabel("EV / TTM revenue (x)")
    ax.grid(axis="x", color=viz.GRID, lw=0.6)
    viz.titles(ax, "The market pays for margin: networking peers trade at multiples of HPE's EV/Sales",
               "EV / TTM revenue vs TTM GAAP operating margin, prices at 11-Sep-2026")
    viz.source(fig, "SEC XBRL filings, Yahoo Finance prices; Bona Fide analysis.")
    viz.save(fig, "peers_margin_vs_multiple")

    pd.set_option("display.width", 250, "display.max_columns", 30)
    print(m.round(3).to_string())


if __name__ == "__main__":
    main()
