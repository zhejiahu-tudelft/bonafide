"""Macro and industry analysis for HPE — only variables with a direct channel into HPE's economics.

Processing (from cached raw data; no network access):
  1. Cloud capex demand  quarterly capex of MSFT, GOOGL, AMZN, META and ORCL from their SEC XBRL facts
                         (cash-flow facts are year-to-date, so quarters are differenced), mapped to calendar quarters
  2. Memory cost cycle   Micron quarterly revenue and gross margin (Q4 = fiscal year less nine months), a proxy
                         for DRAM/NAND contract pricing, one of the largest server input costs
  3. Rates and dollar    10-year Treasury yield and US dollar index (WACC, FS funding cost, FX translation)
  4. Server competition  IDC 2Q26 server vendor revenue (keyed from the IDC release, source S-log)

Outputs: data/financial_data/industry/hyperscaler_capex_quarterly.csv, micron_quarterly.csv,
         data/processed_data/macro/*.csv; charts in data/processed_data/charts.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import viz
from common import FIN_DATA, MKT_DATA, PROC

OUT = PROC / "macro"
OUT.mkdir(exist_ok=True)
IND = FIN_DATA / "industry"
HYPERSCALERS = {"MSFT": "0000789019", "GOOGL": "0001652044", "AMZN": "0001018724", "META": "0001326801", "ORCL": "0001341439"}
CAPEX_TAGS = ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"]
MICRON_CIK = "0000723125"

# IDC Worldwide Quarterly Server Tracker, 2Q26 (released 10-Sep-2026, via IT-Online) — vendor revenue $bn, share, YoY growth
IDC_2Q26 = pd.DataFrame([
    ("Dell Technologies", 22.2, 0.134, 1.654), ("Supermicro", 10.2, 0.061, 0.972), ("Lenovo", 8.4, 0.051, 0.996),
    ("HPE", 5.9, 0.035, 0.460), ("IEIT Systems", 4.0, 0.024, -0.081), ("ODM Direct", 89.7, 0.539, 0.352),
], columns=["vendor", "revenue_bn", "share", "yoy"])


def facts(cik: str) -> dict:
    return json.loads((IND / f"companyfacts_{cik}.json").read_text())["facts"].get("us-gaap", {})


def discrete_quarters(vals: list[dict]) -> pd.Series:
    """Quarterly values keyed by period end from 3-month, year-to-date and annual duration facts."""
    df = pd.DataFrame([v for v in vals if "start" in v and v.get("form") in ("10-Q", "10-K")])
    if df.empty:
        return pd.Series(dtype=float)
    df["start"], df["end"] = pd.to_datetime(df["start"]), pd.to_datetime(df["end"])
    df = df.sort_values("filed").drop_duplicates(["start", "end"], keep="last")
    df["days"] = (df["end"] - df["start"]).dt.days
    out: dict = {}
    for _, grp in df.groupby("start"):
        prev_val, prev_days = 0.0, 0
        for _, row in grp.sort_values("end").iterrows():
            if row["days"] > 380 or row["days"] - prev_days > 100:
                break  # gap in the year-to-date chain: cannot difference safely
            out.setdefault(row["end"], row["val"] - prev_val)
            prev_val, prev_days = row["val"], row["days"]
    return pd.Series(out).sort_index()


def combined_quarters(f: dict, tags: list[str]) -> pd.Series:
    """Merge a concept reported under different tags over time, preferring the most recently used tag."""
    series = [discrete_quarters(f[t]["units"]["USD"]) for t in tags if t in f and "USD" in f[t]["units"]]
    series = [s for s in series if not s.empty]
    series.sort(key=lambda s: s.index.max(), reverse=True)
    merged = series[0]
    for s in series[1:]:
        merged = merged.combine_first(s)
    return merged


def build_capex() -> pd.DataFrame:
    frames = []
    for tk, cik in HYPERSCALERS.items():
        q = combined_quarters(facts(cik), CAPEX_TAGS) / 1e9
        q = q[q.index >= "2015-10-01"]
        frames.append(q.groupby(q.index.to_period("Q")).sum().rename(tk))
    capex = pd.concat(frames, axis=1)
    capex = capex[capex.notna().all(axis=1)]
    capex["total"] = capex[list(HYPERSCALERS)].sum(axis=1)
    capex["total_ttm"] = capex["total"].rolling(4).sum()
    capex["ttm_yoy"] = capex["total_ttm"].pct_change(4)
    capex["yoy"] = capex["total"].pct_change(4)
    capex.index = capex.index.astype(str)
    capex.to_csv(IND / "hyperscaler_capex_quarterly.csv")
    return capex


def build_micron() -> pd.DataFrame:
    f = facts(MICRON_CIK)
    rev = combined_quarters(f, ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"])
    gp = combined_quarters(f, ["GrossProfit"])
    mu = pd.DataFrame({"revenue_bn": rev / 1e9, "gross_profit_bn": gp / 1e9}).dropna()
    mu["gross_margin"] = mu["gross_profit_bn"] / mu["revenue_bn"]
    mu = mu[mu.index >= "2015-10-01"]
    mu.index.name = "end"
    mu.to_csv(IND / "micron_quarterly.csv")
    return mu


def charts(cap: pd.DataFrame, mu: pd.DataFrame) -> None:
    recent = cap[cap.index >= "2023Q1"]
    names = list(HYPERSCALERS)
    fig, ax = viz.figure(8, 3.4)
    x = np.arange(len(recent))
    bottom = np.zeros(len(recent))
    for name, col in zip(names, viz.SERIES):
        ax.bar(x, recent[name], bottom=bottom, width=0.6, color=col, edgecolor=viz.SURFACE, linewidth=1.2, label=name)
        bottom += recent[name].values
    for i, (_, row) in enumerate(recent.iterrows()):
        if i % 2 == 1 or i == len(recent) - 1:
            ax.text(i, row["total"] + 3, f"${row['total']:.0f}bn", ha="center", fontsize=7, color=viz.INK2)
    ax.set_xticks(x, recent.index, fontsize=7)
    ax.set_ylabel("$bn per quarter")
    ax.legend(loc="upper left", ncol=5)
    ttm, yoy = cap["total_ttm"].iloc[-1], cap["ttm_yoy"].iloc[-1]
    viz.titles(ax, f"Cloud capex is running at ${ttm:.0f}bn a year (+{yoy:.0%}): the demand engine behind HPE's backlog",
               "Quarterly capital expenditure (purchases of PP&E) by calendar quarter; fiscal quarters mapped to calendar")
    viz.source(fig, "Company 10-Q/10-K XBRL via SEC EDGAR; Bona Fide analysis.")
    viz.save(fig, "macro_hyperscaler_capex")

    m = mu[mu.index >= "2022-01-01"]
    fig, ax = viz.figure(8, 2.8)
    ax.plot(m.index, m["gross_margin"], color=viz.GREEN, marker="o", ms=4)
    viz.end_label(ax, m.index[-1], m["gross_margin"].iloc[-1], f"{m['gross_margin'].iloc[-1]:.0%}", dx=8)
    viz.pct_axis(ax)
    viz.titles(ax, "Memory makers' margins signal a historic DRAM/NAND price spike — HPE's key input cost",
               "Micron quarterly gross margin (proxy for memory contract pricing)")
    viz.source(fig, "Micron 10-Q/10-K XBRL via SEC EDGAR; TrendForce 3Q26 server DRAM +13–18% QoQ; Bona Fide analysis.")
    viz.save(fig, "macro_memory_cycle")

    dgs = pd.read_csv(MKT_DATA / "macro" / "DGS10.csv", parse_dates=["date"]).dropna().set_index("date")["value"]
    dxy = pd.read_csv(MKT_DATA / "macro" / "DXY.csv", parse_dates=["date"]).dropna().set_index("date")["value"]
    dgs, dxy = dgs[dgs.index >= "2021-01-01"], dxy[dxy.index >= "2021-01-01"]
    fig, (a1, a2) = viz.figure(8, 3.6, nrows=2, sharex=True)
    a1.plot(dgs.index, dgs, color=viz.GREEN, lw=1.5)
    a1.set_ylabel("10Y yield %")
    viz.end_label(a1, dgs.index[-1], dgs.iloc[-1], f"{dgs.iloc[-1]:.2f}%")
    a2.plot(dxy.index, dxy, color=viz.BLUE, lw=1.5)
    a2.set_ylabel("DXY")
    viz.end_label(a2, dxy.index[-1], dxy.iloc[-1], f"{dxy.iloc[-1]:.1f}")
    viz.titles(a1, "Higher-for-longer rates lift HPE's discount rate; a softer dollar helps translation",
               "10-year US Treasury yield (top) and ICE US dollar index (bottom), since 2021")
    viz.source(fig, "FRED (DGS10); Yahoo Finance (DX-Y.NYB).")
    viz.save(fig, "macro_rates_dollar")

    IDC_2Q26.to_csv(OUT / "idc_server_vendors_2q26.csv", index=False)
    oem = IDC_2Q26[IDC_2Q26.vendor != "ODM Direct"].sort_values("revenue_bn")
    fig, ax = viz.figure(8, 2.9)
    y = np.arange(len(oem))
    ax.barh(y, oem["revenue_bn"], height=0.55, color=[viz.GREEN if v == "HPE" else viz.CONTEXT for v in oem["vendor"]])
    for i, r in enumerate(oem.itertuples()):
        ax.text(r.revenue_bn + 0.3, i, f"${r.revenue_bn:.1f}bn · {r.share:.1%} share · {r.yoy:+.0%} YoY", va="center",
                fontsize=7.5, color=viz.INK2)
    ax.set_yticks(y, oem["vendor"])
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=viz.GRID, lw=0.6)
    ax.set_xlim(0, oem["revenue_bn"].max() * 1.6)
    ax.set_xlabel("2Q26 server revenue, $bn")
    viz.titles(ax, "HPE is growing, but losing server share to Dell, Supermicro and Lenovo",
               "IDC 2Q26 worldwide server vendor revenue (ODM Direct, 53.9% share, excluded)")
    viz.source(fig, "IDC Worldwide Quarterly Server Tracker 2Q26 (10-Sep-2026), via IT-Online.")
    viz.save(fig, "industry_idc_server_share")


def main() -> None:
    cap = build_capex()
    mu = build_micron()
    charts(cap, mu)
    print(f"capex quarters {cap.index[0]}–{cap.index[-1]} ({len(cap)}); last TTM ${cap['total_ttm'].iloc[-1]:.0f}bn")
    print(f"Micron quarters {mu.index[0].date()}–{mu.index[-1].date()} ({len(mu)})")
    print(cap.tail(4).round(1))
    print(mu.tail(5).round(3))


if __name__ == "__main__":
    main()
