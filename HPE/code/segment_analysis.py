"""Segment analysis on HPE's FY26 reporting structure (Networking / Cloud & AI / Corporate Investments).

HPE recast segments retrospectively only back to FY24/FY25, so segment history here covers the seven
quarters Q1 FY25–Q3 FY26 (data keyed from earnings releases in data/financial_data/hpe_segments_quarterly.csv;
Q2 FY25 is derived from nine-month totals). Juniper is consolidated from 2-Jul-2025, so Networking
growth before Q4 FY26 comparisons is largely inorganic.

Outputs: data/processed_data/segments/*.csv; charts.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import viz
from common import FIN_DATA, PROC

OUT = PROC / "segments"
OUT.mkdir(exist_ok=True)
SEG_COLORS = {"Networking": viz.GREEN, "Cloud & AI": viz.GOLD, "Corporate Investments and Other": viz.BLUE}


def main() -> None:
    df = pd.read_csv(FIN_DATA / "hpe_segments_quarterly.csv")
    order = list(dict.fromkeys(df["quarter"]))
    tot = df[df.line == "Total"].pivot(index="quarter", columns="segment", values="revenue").loc[order]
    op = df[df.line == "Total"].pivot(index="quarter", columns="segment", values="operating_profit").loc[order]
    lines = df[df.line != "Total"].pivot_table(index="quarter", columns=["segment", "line"], values="revenue").loc[order]

    # consistency: sub-lines sum to segment totals every quarter
    for seg in ["Networking", "Cloud & AI"]:
        diff = (lines[seg].sum(axis=1) - tot[seg]).abs().max()
        assert diff < 1, f"{seg} sub-lines do not sum to total (max diff {diff})"

    ttm_q = order[-4:]
    ttm = pd.DataFrame({"revenue": tot.loc[ttm_q].sum(), "operating_profit": op.loc[ttm_q].sum()})
    ttm["margin"] = ttm["operating_profit"] / ttm["revenue"]
    ttm["revenue_share"] = ttm["revenue"] / ttm["revenue"].sum()
    seg_op_total = ttm.loc[["Networking", "Cloud & AI"], "operating_profit"].sum() + ttm.at["Corporate Investments and Other", "operating_profit"]
    ttm["profit_share"] = ttm["operating_profit"] / seg_op_total
    ttm.to_csv(OUT / "segments_ttm.csv")

    line_ttm = lines.loc[ttm_q].sum().rename("ttm_revenue").to_frame()
    line_ttm["q3fy26_yoy"] = lines.loc["Q3 FY26"] / lines.loc["Q3 FY25"] - 1
    line_ttm["share_of_total"] = line_ttm["ttm_revenue"] / tot.loc[ttm_q].sum().sum()
    line_ttm.to_csv(OUT / "segment_lines_ttm.csv")
    margins = op / tot
    margins.to_csv(OUT / "segment_margins_quarterly.csv")
    tot.to_csv(OUT / "segment_revenue_quarterly.csv")

    summary = {
        "ttm_quarters": ttm_q,
        "ttm_revenue_by_segment": ttm["revenue"].round(0).to_dict(),
        "ttm_margin_by_segment": ttm["margin"].round(4).to_dict(),
        "networking_share_of_revenue": round(ttm.at["Networking", "revenue_share"], 4),
        "networking_share_of_segment_profit": round(ttm.at["Networking", "profit_share"], 4),
        "q3fy26_yoy_by_segment": (tot.loc["Q3 FY26"] / tot.loc["Q3 FY25"] - 1).round(4).to_dict(),
    }
    (OUT / "segment_summary.json").write_text(json.dumps(summary, indent=2))

    # Chart 1: quarterly revenue by segment (stacked, 2px surface gaps)
    x = np.arange(len(order))
    fig, ax = viz.figure(8, 3.4)
    bottom = np.zeros(len(order))
    for seg in ["Cloud & AI", "Networking", "Corporate Investments and Other"]:
        vals = tot[seg].values / 1000
        ax.bar(x, vals, bottom=bottom, width=0.55, color=SEG_COLORS[seg], edgecolor=viz.SURFACE, linewidth=1.5,
               label=seg.replace("Corporate Investments and Other", "Corporate Inv. & Other"))
        bottom += vals
    for i, v in enumerate(bottom):
        ax.text(i, v + 0.15, f"${v:.1f}bn", ha="center", fontsize=7.5, color=viz.INK2)
    ax.set_xticks(x, order)
    ax.set_ylabel("$bn")
    ax.set_ylim(0, bottom.max() * 1.15)
    ax.legend(loc="upper left")
    viz.titles(ax, "Juniper doubled Networking; Cloud & AI supplied the 2026 acceleration",
               "Quarterly revenue by segment (recast FY26 structure); Juniper consolidated from 2-Jul-2025")
    viz.source(fig, "HPE earnings releases Q1 FY26–Q3 FY26; Bona Fide analysis. Q2 FY25 derived from 9M totals.")
    viz.save(fig, "seg_revenue_quarterly")

    # Chart 2: segment operating margins (2 series)
    fig, ax = viz.figure(8, 3.0)
    for seg in ["Networking", "Cloud & AI"]:
        ax.plot(x, margins[seg], color=SEG_COLORS[seg], marker="o", ms=5, label=seg)
        viz.end_label(ax, x[-1], margins[seg].iloc[-1], f"{margins[seg].iloc[-1]:.1%}", dx=8)
    ax.set_xticks(x, order)
    viz.pct_axis(ax)
    ax.set_ylim(0, 0.35)
    ax.legend(loc="upper right")
    viz.titles(ax, "Networking earns ~2x Cloud & AI margins; Cloud & AI jumped on pricing in Q3",
               "Segment operating profit margin by quarter")
    viz.source(fig, "HPE earnings releases; Bona Fide analysis.")
    viz.save(fig, "seg_margins_quarterly")

    # Chart 3: TTM revenue by business line (single series, sorted)
    lt = line_ttm.sort_values("ttm_revenue")
    fig, ax = viz.figure(8, 3.4)
    y = np.arange(len(lt))
    ax.barh(y, lt["ttm_revenue"] / 1000, height=0.55, color=[SEG_COLORS[s] for s, _ in lt.index])
    for i, (idx, row) in enumerate(lt.iterrows()):
        ax.text(row["ttm_revenue"] / 1000 + 0.2, i, f"${row['ttm_revenue'] / 1000:.1f}bn · Q3 YoY {row['q3fy26_yoy']:+.0%}",
                va="center", fontsize=7.5, color=viz.INK2)
    ax.set_yticks(y, [f"{l} ({s.split(' ')[0]})" for s, l in lt.index])
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=viz.GRID, lw=0.6)
    ax.set_xlim(0, lt["ttm_revenue"].max() / 1000 * 1.45)
    ax.set_xlabel("TTM revenue, $bn")
    viz.titles(ax, "Servers are half of revenue; routing and data-centre networking grow fastest",
               "TTM revenue by business line (Q4 FY25–Q3 FY26) and Q3 FY26 year-over-year growth")
    viz.source(fig, "HPE earnings releases; Bona Fide analysis. Routing/DCN growth largely reflects Juniper consolidation.")
    viz.save(fig, "seg_lines_ttm")

    print(ttm.round(3))
    print(line_ttm.round(3))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
