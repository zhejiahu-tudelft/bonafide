"""Practitioner Q&A 3 (Experiment 11): is GreenLake becoming a second Juniper for HPE?

Hypothesis: if GreenLake were becoming a second profit engine comparable with the Juniper acquisition, HPE's
disclosures would show (a) recurring revenue growing faster than the company at a scale comparable with networking,
and (b) a profitability profile approaching networking's.

A. ARR series          annualised revenue run-rate by quarter, parsed from the 8-K Ex-99.1 earnings releases
                       (Q4 FY21-Q4 FY25); the Juniper-close quarter and management's FY26 target of ~$3.5bn
B. Customers           GreenLake customers, systems managed and net retention, keyed from the Securities Analyst
                       Meeting (Oct-2025) transcript and FY25-FY26 earnings materials; each value is checked against
                       the text of its source PDF
C. Segment economics   net revenue and earnings from operations for Server, Hybrid Cloud, Networking and Financial
                       Services, FY2023-FY2025, parsed from the FY2025 10-K. Hybrid Cloud (storage, private cloud,
                       GreenLake Flex, infrastructure SaaS) is the last segment in which GreenLake economics were visible;
                       from FY26 it is merged into Cloud & AI.

ARR is not a pure GreenLake measure: it also includes lease income from Financial Services and, from Q3 FY25, software
support and maintenance (HPE: "not material"). HPE has not disclosed the size of GreenLake itself.
Outputs: data/processed_data/qa/q3_*.csv, q3_summary.json; chart qa_q3_greenlake.
"""
from __future__ import annotations

import html
import json
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pymupdf

import viz
from common import CHARTS, EARNINGS, PROC

OUT = PROC / "qa"
OUT.mkdir(parents=True, exist_ok=True)
TEN_K = PROC / "text" / "company_filings" / "10-K" / "HPE_10-K_FY2025_filed2025-12-18.txt"
FY25_ARR_EXACT = 3151.0            # $m, FY2025 10-K
FY26_ARR_TARGET = 3500.0           # $m, "approximately $3.5 billion by the end of '26" (SAM 2025 transcript p.20)
GREENLAKE_ARR_FLOOR = 2000.0       # $m, "generating over $2 billion in ARR" (SAM 2025 transcript p.12)
JUNIPER_CLOSE_QUARTER = "Q3 FY25"

# (fiscal quarter, customers, systems managed (m), net retention, source PDF under report/earnings_materials, page,
#  phrase that must appear on that page, basis)
KEYED = [
    ("Q3 FY24", 37000, None, None, "sam_2025/hpe-sam-2025-transcript.pdf", 12, "44,000 GreenLake customers, an increase of 7,000 new logos",
     "derived: 44,000 less 7,000 new logos in the year"),
    ("Q2 FY25", None, 5.3, None, "FY2026Q2/HPE_Q2FY26_transcript.pdf", 5, "up from 5.3 million a year ago", "reported (prior-year comparison)"),
    ("Q3 FY25", 44000, 5.8, None, "sam_2025/hpe-sam-2025-transcript.pdf", 12, "manage more than 5.8 million devices", "reported at SAM, Oct-2025"),
    ("Q4 FY25", 46000, None, None, "FY2025Q4/HPE_Q4FY25_earnings-presentation.pdf", 6, "ending fiscal 2025 with ~46,000 customers", "reported, approximate"),
    ("Q2 FY26", 50000, 6.7, 1.10, "FY2026Q2/HPE_Q2FY26_transcript.pdf", 5, "remains near 110%", "reported, approximate; net retention 'near 110%'"),
    ("Q3 FY26", 52000, None, None, "FY2026Q3/HPE_Q3FY26_transcript.pdf", 5, "grew 18% to 52,000 up from 44,000", "reported"),
]


# ------------------------------------------------------------------------------------------ A. ARR
def fiscal_quarter(release: pd.Timestamp) -> str | None:
    q = {11: 4, 12: 4, 2: 1, 3: 1, 5: 2, 6: 2, 8: 3, 9: 3}.get(release.month)
    return None if q is None else f"Q{q} FY{release.year % 100:02d}"


def period_end(label: str) -> pd.Timestamp:
    q, fy = int(label[1]), 2000 + int(label[-2:])
    return pd.Timestamp({1: f"{fy}-01-31", 2: f"{fy}-04-30", 3: f"{fy}-07-31", 4: f"{fy}-10-31"}[q])


def arr_series() -> pd.DataFrame:
    rows = []
    for f in sorted((EARNINGS / "sec_8k_ex99").glob("HPE_8-K_Ex99-1_earnings_*.htm")):
        release = pd.Timestamp(f.stem.split("_")[-1])
        label = fiscal_quarter(release)
        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", f.read_text(errors="ignore"))))
        m = re.search(r"annualized revenue run-rate[^$]{0,60}?(for the first time exceeded |of |: )\$([\d.,]+) (million|billion)[^%]{0,40}?up (\d+)%", text, re.I)
        if label is None or m is None:
            continue
        value = float(m.group(2).replace(",", "")) * (1000 if m.group(3).lower() == "billion" else 1)
        rows.append(dict(fiscal_quarter=label, period_end=period_end(label), release=release.date(), arr_m=value,
                         yoy_growth=int(m.group(4)) / 100, lower_bound="exceeded" in m.group(1),
                         precision_m=1 if m.group(3).lower() == "million" else 100, source=f.name))
    df = pd.DataFrame(rows).sort_values(["period_end", "release"]).drop_duplicates("fiscal_quarter", keep="last")
    return df.reset_index(drop=True)


# ------------------------------------------------------------------------------------------ B. customers
def customers() -> pd.DataFrame:
    rows = []
    for label, cust, systems, nrr, src, page, phrase, basis in KEYED:
        page_text = re.sub(r"\s+", " ", pymupdf.open(EARNINGS / src)[page - 1].get_text())
        assert phrase in page_text, (src, page, phrase)          # every keyed value is traceable to its page
        rows.append(dict(fiscal_quarter=label, period_end=period_end(label), customers=cust, systems_managed_m=systems,
                         net_retention=nrr, source=f"{src} p.{page}", basis=basis))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------ C. segments
def segment_economics() -> pd.DataFrame:
    t = re.sub(r"\s+", " ", TEN_K.read_text(errors="ignore"))
    rows = []
    for seg in ("Server", "Hybrid Cloud", "Networking", "Financial Services"):
        m = re.search(rf"{seg} For the fiscal years ended October 31, 2025 \| 2024 \| 2023 .{{0,80}}?Net revenue \| \$ \| ([\d,]+) \| \$ \| ([\d,]+) \| \$ \| ([\d,]+)"
                      rf".{{0,400}}?Earnings from operations \| \$ \| ([\d,]+) \| \$ \| ([\d,]+) \| \$ \| ([\d,]+)", t)
        assert m, seg
        vals = [float(v.replace(",", "")) for v in m.groups()]
        for i, fy in enumerate((2025, 2024, 2023)):
            rows.append(dict(segment=seg, fiscal_year=fy, net_revenue_m=vals[i], operating_profit_m=vals[3 + i]))
    df = pd.DataFrame(rows).sort_values(["fiscal_year", "segment"]).reset_index(drop=True)
    df["operating_margin"] = df["operating_profit_m"] / df["net_revenue_m"]
    tot = df.groupby("fiscal_year")[["net_revenue_m", "operating_profit_m"]].transform("sum")
    df["revenue_share"] = df["net_revenue_m"] / tot["net_revenue_m"]
    df["profit_share"] = df["operating_profit_m"] / tot["operating_profit_m"]
    return df


# ------------------------------------------------------------------------------------------ chart
def chart(arr: pd.DataFrame, seg: pd.DataFrame) -> None:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.6, 3.9), gridspec_kw={"width_ratios": [1.45, 1]})
    x = np.arange(len(arr))
    a1.plot(x, arr["arr_m"] / 1000, color=viz.GREEN, marker="o", ms=4, lw=2, zorder=3, label="ARR, reported")
    xt = len(arr) + 0.6
    a1.scatter([xt], [FY26_ARR_TARGET / 1000], s=46, facecolor="white", edgecolor=viz.GOLD, lw=1.6, zorder=4,
               label="FY26 target (~$3.5bn)")
    j = int(arr.index[arr["fiscal_quarter"] == JUNIPER_CLOSE_QUARTER][0])
    a1.axvline(j - 0.5, color=viz.AXIS, lw=0.8, zorder=1)
    a1.text(j - 0.45, 3.45, " Juniper consolidated", fontsize=7, color=viz.INK2, va="top")
    ticks = list(range(0, len(arr), 2)) + [len(arr) - 1]
    a1.set_xticks(sorted(set(ticks)) + [xt], [arr["fiscal_quarter"][i] for i in sorted(set(ticks))] + ["FY26E"], fontsize=7, rotation=0)
    a1.set_xlim(-0.5, xt + 0.6)
    a1.set_ylim(0, 3.8)
    a1.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:.1f}bn"))
    a1.legend(loc="upper left", fontsize=7.5)
    a1.text(0, 1.03, "Annualised revenue run-rate (ARR) by fiscal quarter", transform=a1.transAxes, fontsize=8.5, fontweight="bold", color=viz.INK)

    segs = [("Server", viz.CONTEXT), ("Hybrid Cloud", viz.GOLD), ("Networking", viz.BLUE)]
    years = [2023, 2024, 2025]
    w = 0.26
    for k, (s, col) in enumerate(segs):
        vals = [seg.loc[(seg.segment == s) & (seg.fiscal_year == y), "operating_margin"].iloc[0] for y in years]
        bars = a2.bar(np.arange(3) + (k - 1) * w, vals, width=w, color=col, zorder=3, label=s)
        for b, v in zip(bars, vals):
            a2.text(b.get_x() + b.get_width() / 2, v + 0.005, f"{v:.0%}" if s != "Hybrid Cloud" else f"{v:.1%}",
                    ha="center", va="bottom", fontsize=6.5, color=viz.INK2)
    a2.set_xticks(np.arange(3), [f"FY{y}" for y in years], fontsize=8)
    a2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    a2.set_ylim(0, 0.30)
    a2.legend(loc="upper left", fontsize=7.5, ncol=3)
    a2.text(0, 1.03, "Segment operating margin", transform=a2.transAxes, fontsize=8.5, fontweight="bold", color=viz.INK)

    texts = [fig.text(0.01, 0.995, "GreenLake grows recurring revenue; its segment earns a fraction of networking's margin",
                      fontsize=11, fontweight="bold", color=viz.INK, va="top"),
             fig.text(0.01, 0.945, "ARR Q4 FY21–Q4 FY25 with the FY26 target; Hybrid Cloud (storage, private cloud, GreenLake Flex, SaaS) vs Server and Networking, FY2023–FY2025",
                      fontsize=8.5, color=viz.INK2, va="top"),
             fig.text(0.01, 0.0, "Source: HPE 8-K earnings releases; FY2025 10-K segment note; 2025 Securities Analyst Meeting; Bona Fide analysis. "
                                 "ARR includes Financial Services lease income and, from Q3 FY25, software support.",
                      fontsize=7, color=viz.MUTED, va="top")]
    fig.tight_layout(rect=(0, 0.02, 1, 0.88))
    fig.savefig(CHARTS / "qa_q3_greenlake.svg", bbox_inches="tight")
    fig.savefig(CHARTS / "qa_q3_greenlake.png", dpi=220, bbox_inches="tight")
    for txt in texts:
        txt.set_visible(False)
    fig.savefig(CHARTS / "qa_q3_greenlake_deck.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    arr, cust, seg = arr_series(), customers(), segment_economics()
    arr.to_csv(OUT / "q3_arr_series.csv", index=False)
    cust.to_csv(OUT / "q3_customers.csv", index=False)
    seg.to_csv(OUT / "q3_segment_economics.csv", index=False)
    chart(arr, seg)

    by_q = arr.set_index("fiscal_quarter")["arr_m"]
    s = lambda name, fy, col: float(seg.loc[(seg.segment == name) & (seg.fiscal_year == fy), col].iloc[0])
    hc25, net25 = s("Hybrid Cloud", 2025, "operating_margin"), s("Networking", 2025, "operating_margin")
    summary = dict(
        arr=dict(first=dict(quarter=arr.iloc[0]["fiscal_quarter"], arr_m=float(arr.iloc[0]["arr_m"])),
                 q4_fy24_m=float(by_q["Q4 FY24"]), q2_fy25_m=float(by_q["Q2 FY25"]), q3_fy25_m=float(by_q["Q3 FY25"]),
                 q4_fy25_m=float(by_q["Q4 FY25"]), fy25_exact_m=FY25_ARR_EXACT,
                 cagr_q4fy21_q4fy24=float((by_q["Q4 FY24"] / by_q["Q4 FY21"]) ** (1 / 3) - 1),
                 yoy_q2_fy25=float(arr.set_index("fiscal_quarter").loc["Q2 FY25", "yoy_growth"]),
                 yoy_q3_fy25=float(arr.set_index("fiscal_quarter").loc["Q3 FY25", "yoy_growth"]),
                 step_q2_to_q3_fy25_m=float(by_q["Q3 FY25"] - by_q["Q2 FY25"]),
                 fy26_target_m=FY26_ARR_TARGET, fy26_implied_growth=FY26_ARR_TARGET / FY25_ARR_EXACT - 1,
                 greenlake_arr_floor_m=GREENLAKE_ARR_FLOOR, arr_to_ttm_revenue=FY25_ARR_EXACT / 41871.0),
        customers=dict(latest=int(cust.iloc[-1]["customers"]), year_ago=44000, growth=52000 / 44000 - 1,
                       systems_managed_m_q2_fy26=6.7, systems_growth=6.7 / 5.3 - 1, net_retention_q2_fy26=1.10,
                       greenlake_arr_per_customer_floor=GREENLAKE_ARR_FLOOR * 1e6 / 44000,
                       systems_per_customer_q2_fy26=6.7e6 / 50000),
        segments=dict(
            hybrid_cloud_margin={y: s("Hybrid Cloud", y, "operating_margin") for y in (2023, 2024, 2025)},
            networking_margin={y: s("Networking", y, "operating_margin") for y in (2023, 2024, 2025)},
            server_margin={y: s("Server", y, "operating_margin") for y in (2023, 2024, 2025)},
            hybrid_cloud_revenue_share_fy25=s("Hybrid Cloud", 2025, "revenue_share"),
            hybrid_cloud_profit_share_fy25=s("Hybrid Cloud", 2025, "profit_share"),
            networking_profit_share_fy25=s("Networking", 2025, "profit_share"),
            revenue_needed_at_hc_margin_to_match_networking_profit_m=s("Networking", 2025, "operating_profit_m") / hc25,
            margin_needed_at_hc_revenue_to_match_networking_profit=s("Networking", 2025, "operating_profit_m") / s("Hybrid Cloud", 2025, "net_revenue_m"),
            margin_gap_fy25_pp=(net25 - hc25) * 100),
    )
    (OUT / "q3_summary.json").write_text(json.dumps(summary, indent=2, default=float))
    print(arr[["fiscal_quarter", "arr_m", "yoy_growth", "lower_bound"]].to_string(index=False))
    print(cust[["fiscal_quarter", "customers", "systems_managed_m", "net_retention", "source"]].to_string(index=False))
    print(seg.round(3).to_string(index=False))
    print(json.dumps(summary, indent=1, default=float))


if __name__ == "__main__":
    main()
