"""Descriptive stock reaction around material HPE events (not a formal event study).

For each event the reaction day (day 0) is the first session that could trade on the news
(after-close announcements -> next session). Returns are dividend-adjusted closes:
  day-0, next-day (day +1), 3-day [0,+2] and 5-day [0,+4] cumulative, plus excess vs SPY.

Event dates come from 8-K filing dates (earnings = Item 2.02, filed after the close) and dated
company/news sources logged in report/source_log.csv. Windows extending past the valuation date are
left blank.

Outputs: data/processed_data/events/event_returns.csv; chart.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import viz
from common import MKT_DATA, PROC, VALUATION_DATE

OUT = PROC / "events"
OUT.mkdir(exist_ok=True)

# (reaction day, category, event, timing / source note)
EVENTS = [
    ("2024-01-09", "M&A", "Juniper acquisition reported / announced ($14bn, $40/sh cash)", "Press report 8-Jan evening; HPE announcement 9-Jan"),
    ("2024-03-01", "Earnings", "Q1 FY24: revenue miss, FY24 revenue guide cut", "8-K Item 2.02 filed 29-Feb-2024 after close"),
    ("2024-06-05", "Earnings", "Q2 FY24: AI server beat", "8-K Item 2.02 filed 4-Jun-2024 after close"),
    ("2024-09-05", "Earnings", "Q3 FY24 results", "8-K Item 2.02 filed 4-Sep-2024 after close"),
    ("2024-09-10", "Financing", "$1.35bn mandatory convertible preferred + senior notes offering", "Offering announced 9-Sep-2024 after close (424B filings)"),
    ("2024-12-06", "Earnings", "Q4 FY24 results", "8-K Item 2.02 filed 5-Dec-2024 after close"),
    ("2025-01-30", "Regulatory", "US DOJ sues to block Juniper acquisition", "DOJ complaint filed 30-Jan-2025 (intraday)"),
    ("2025-03-07", "Earnings", "Q1 FY25: FY25 guide cut, tariffs, server margin pressure", "8-K Item 2.02 filed 6-Mar-2025 after close"),
    ("2025-04-03", "Macro", "US 'reciprocal' tariff announcement", "Announced 2-Apr-2025 after close"),
    ("2025-04-09", "Macro", "US 90-day tariff pause", "Announced 9-Apr-2025 intraday"),
    ("2025-04-15", "Activism", "Elliott >$1.5bn stake reported", "Bloomberg report 15-Apr-2025 (intraday); CNBC same day"),
    ("2025-06-04", "Earnings", "Q2 FY25 results", "8-K Item 2.02 filed 3-Jun-2025 after close"),
    ("2025-06-30", "Regulatory", "DOJ settlement clears Juniper deal", "Settlement announced 28-Jun-2025 (Saturday)"),
    ("2025-07-02", "M&A", "Juniper acquisition closes", "Closing announced 2-Jul-2025"),
    ("2025-07-16", "Activism", "Elliott cooperation agreement; new director, Strategy Committee", "8-K filed 16-Jul-2025"),
    ("2025-09-04", "Earnings", "Q3 FY25 results (first Juniper month)", "8-K Item 2.02 filed 3-Sep-2025 after close"),
    ("2025-10-16", "Guidance", "Securities Analyst Meeting: FY26 outlook below expectations", "SAM held 15-Oct-2025; outlook 8-K same day"),
    ("2025-12-05", "Earnings", "Q4 FY25 results", "8-K Item 2.02 filed 4-Dec-2025 after close"),
    ("2026-03-10", "Earnings", "Q1 FY26 results", "8-K Item 2.02 filed 9-Mar-2026 after close"),
    ("2026-05-29", "Peer", "Dell Q1 FY27: AI server backlog $51bn, sector rally", "Dell results 28-May-2026 after close"),
    ("2026-06-02", "Earnings", "Q2 FY26: +40% revenue, FY26 guide raised, FY27 framework", "8-K Item 2.02 filed 1-Jun-2026 after close"),
    ("2026-07-09", "Product", "ProLiant DL394 Gen12 (NVIDIA Vera) launch; AI-server rally", "News reports 9-Jul-2026"),
    ("2026-09-03", "Earnings", "Q3 FY26: record results, FY26/FY27 raised, Oracle collaboration + warrant", "8-K Item 2.02 filed 2-Sep-2026 after close"),
    ("2026-09-11", "Sector", "Enterprise AI infrastructure rally; reassessment of Q3 and Oracle", "News reports 11-Sep-2026"),
]


def cum(r: pd.Series, i: int, n: int) -> float:
    if i + n > len(r):
        return np.nan
    return float((1 + r.iloc[i:i + n]).prod() - 1)


def main() -> None:
    px = {tk: pd.read_csv(MKT_DATA / f"{tk}_daily.csv", parse_dates=["date"]).set_index("date")["adj_close"]
          for tk in ("HPE", "SPY")}
    rets = pd.DataFrame(px).pct_change().loc[:VALUATION_DATE]
    rows = []
    for date, cat, name, note in EVENTS:
        d = pd.Timestamp(date)
        i = rets.index.searchsorted(d)  # first session on/after the date
        h, s = rets["HPE"], rets["SPY"]
        row = dict(reaction_day=rets.index[i].date(), category=category_label(cat), event=name, timing=note,
                   day_minus1=h.iloc[i - 1], day0=h.iloc[i], day1=h.iloc[i + 1] if i + 1 < len(h) else np.nan,
                   cum_3d=cum(h, i, 3), cum_5d=cum(h, i, 5), spy_3d=cum(s, i, 3), spy_5d=cum(s, i, 5))
        row["excess_day0"] = row["day0"] - s.iloc[i]
        row["excess_3d"] = row["cum_3d"] - row["spy_3d"]
        row["excess_5d"] = row["cum_5d"] - row["spy_5d"]
        rows.append(row)
    ev = pd.DataFrame(rows)
    # where a 3-day window runs into the next event's reaction day, chart the day-0 excess instead
    pos = np.array([rets.index.searchsorted(pd.Timestamp(d)) for d in ev["reaction_day"]])
    overlap = np.array([any(0 < pj - pi <= 2 for pj in pos) for pi in pos])
    use_day0 = overlap | ev["excess_3d"].isna().values
    ev["chart_value"] = np.where(use_day0, ev["excess_day0"], ev["excess_3d"])
    ev["chart_basis"] = np.where(use_day0, "day 0", "3-day")
    ev.to_csv(OUT / "event_returns.csv", index=False)

    earn = ev[ev.category == "Earnings"]
    stats = {"earnings_events": len(earn), "mean_abs_day0": earn["day0"].abs().mean(),
             "share_positive_day0": (earn["day0"] > 0).mean(), "mean_abs_day0_all_days": rets["HPE"].abs().mean()}
    pd.Series(stats).to_csv(OUT / "earnings_reaction_stats.csv")

    # Chart: 3-day excess return by event, chronological (horizontal bars)
    e = ev.iloc[::-1].reset_index(drop=True)
    fig, ax = viz.figure(8, 6.2)
    y = np.arange(len(e))
    vals = e["chart_value"]
    ax.barh(y, vals, height=0.6, color=[viz.GREEN if v >= 0 else viz.GOLD for v in vals])
    for i, (v, basis) in enumerate(zip(vals, e["chart_basis"])):
        ax.text(v + (0.004 if v >= 0 else -0.004), i, f"{v:+.1%}" + (" (day 0)" if basis == "day 0" else ""),
                va="center", ha="left" if v >= 0 else "right", fontsize=7, color=viz.INK2)
    ax.set_yticks(y, [f"{r.reaction_day:%d-%b-%y}  {r.event[:52]}" for r in e.itertuples()], fontsize=7)
    ax.axvline(0, color=viz.AXIS, lw=0.8, zorder=1)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=viz.GRID, lw=0.6)
    ax.xaxis.set_major_formatter(viz.mtick.PercentFormatter(1.0, decimals=0))
    ax.set_xlim(vals.min() - 0.07, vals.max() + 0.08)
    viz.titles(ax, "Earnings and guidance, not deals, drove the biggest stock reactions",
               "HPE return in excess of the S&P 500: 3-day from reaction day, day 0 where windows overlap (gold = negative)")
    viz.source(fig, "Yahoo Finance prices; SEC 8-K filing dates; news sources in source log; Bona Fide analysis.")
    viz.save(fig, "events_excess_returns")

    pd.set_option("display.width", 220, "display.max_colwidth", 60)
    print(ev[["reaction_day", "category", "event", "day0", "cum_3d", "excess_3d", "cum_5d"]].round(3).to_string())
    print(stats)


def category_label(c: str) -> str:
    return c


if __name__ == "__main__":
    main()
