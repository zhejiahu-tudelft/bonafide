"""Latest-earnings analysis for HPE: quarterly scorecard, beats against guidance and consensus, guidance ladder.

Questions answered
  1. How did each quarter land against the guidance given one quarter earlier (revenue and non-GAAP EPS)?
  2. Q3 FY26 against consensus, and how much of the year-over-year operating-profit increase came from
     margin rather than volume?
  3. How fast did full-year guidance ratchet up between the October 2025 analyst meeting and Q3 FY26?

Inputs (report/earnings_materials)
  Earnings press releases Q2 FY25-Q3 FY26 (source log S015, S030, S032, S042, S054, S063), the SAM 2025 press
  release (S071), Q3 FY26 presentation and transcript (S065, S066), Zacks consensus via Yahoo Finance (S252);
  exact quarterly revenue from XBRL (statistical_analysis.hpe_quarterly_revenue) and segment data
  (data/financial_data/hpe_segments_quarterly.csv).
  Every keyed figure is checked against the text of its source document before it is used.

Outputs: data/processed_data/earnings/*.csv, earnings_summary.json; charts earn_beat_guidance, earn_guidance_ladder.
"""
from __future__ import annotations

import html
import json
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pymupdf

import business_model_analysis as bma
import viz
from common import EARNINGS, FIN_DATA, PROC
from statistical_analysis import hpe_quarterly_revenue

OUT = PROC / "earnings"
OUT.mkdir(exist_ok=True)

DOCS = {
    "Q2 FY25": "FY2025Q2/HPE_Q2FY25_earnings-press-release.pdf", "Q3 FY25": "FY2025Q3/HPE_Q3FY25_earnings-press-release.pdf",
    "Q4 FY25": "FY2025Q4/HPE_Q4FY25_earnings-press-release.pdf", "Q1 FY26": "FY2026Q1/HPE_Q1FY26_earnings-press-release.pdf",
    "Q2 FY26": "FY2026Q2/HPE_Q2FY26_earnings-press-release.pdf", "Q3 FY26": "FY2026Q3/HPE_Q3FY26_earnings-press-release.pdf",
    "SAM": "sam_2025/hpe-sam-2025-press-release.pdf", "Q3 FY26 slides": "FY2026Q3/HPE_Q3FY26_earnings-presentation.pdf",
    "Q3 FY26 call": "FY2026Q3/HPE_Q3FY26_transcript.pdf", "consensus": "FY2026Q3/HPE_Q3FY26_consensus_zacks_yahoo_2026-08-28.html",
}
PERIOD_END = {"Q2 FY25": "2025-04-30", "Q3 FY25": "2025-07-31", "Q4 FY25": "2025-10-31", "Q1 FY26": "2026-01-31",
              "Q2 FY26": "2026-04-30", "Q3 FY26": "2026-07-31"}

# Reported results, keyed from each quarter's press release ($bn unless stated). `check` strings must appear verbatim.
QUARTERS = [
    dict(quarter="Q2 FY25", released="2025-06-03", revenue_bn=7.6, gm=0.294, eps=0.38, eps_lo=0.28, eps_hi=0.34, fcf_bn=-0.847,
         check=["Revenue: $7.6 billion", "Non-GAAP(1) of 29.4%", "Non-GAAP(1) of $0.38", "$0.28 - $0.34", "$(847) million"]),
    dict(quarter="Q3 FY25", released="2025-09-03", revenue_bn=9.1, gm=0.299, eps=0.44, eps_lo=0.40, eps_hi=0.45, fcf_bn=0.790,
         check=["Revenue: $9.1 billion", "Non-GAAP(1) of 29.9%", "Non-GAAP(1) of $0.44", "$0.40 - $0.45", "$790 million"]),
    dict(quarter="Q4 FY25", released="2025-12-04", revenue_bn=9.7, gm=0.364, eps=0.62, eps_lo=0.56, eps_hi=0.60, fcf_bn=1.9,
         check=["Revenue: $9.7 billion", "Non-GAAP(1) of 36.4%", "Non-GAAP(1) of $0.62", "$0.56 - $0.60", "$1.9 billion, an increase of $420 million"]),
    dict(quarter="Q1 FY26", released="2026-03-09", revenue_bn=9.3, gm=0.366, eps=0.65, eps_lo=0.57, eps_hi=0.61, fcf_bn=0.7,
         check=["Revenue: $9.3 billion", "Non-GAAP(1) of 36.6%", "Non-GAAP(1) of $0.65", "$0.57 - $0.61", "$0.7 billion, an increase of $1.6 billion"]),
    dict(quarter="Q2 FY26", released="2026-06-01", revenue_bn=10.7, gm=0.369, eps=0.79, eps_lo=0.51, eps_hi=0.55, fcf_bn=0.9,
         check=["Revenue: $10.7 billion", "Non-GAAP(1) of 36.9%", "Non-GAAP(1) of $0.79", "$0.51 - $0.55", "Free cash flow(1)(2): $0.9 billion"]),
    dict(quarter="Q3 FY26", released="2026-09-02", revenue_bn=12.2, gm=0.404, eps=1.11, eps_lo=0.88, eps_hi=0.93, fcf_bn=1.0,
         check=["Revenue: $12.2 billion", "Non-GAAP(1) of 40.4%", "Non-GAAP(1) of $1.11", "$0.88 - $0.93", "Free cash flow(1)(2): $1.0 billion"]),
]
# Next-quarter revenue guidance ($bn), keyed from the release one quarter earlier
REVENUE_GUIDE = [
    dict(given_in="Q2 FY25", quarter="Q3 FY25", lo=8.2, hi=8.5, check=["$8.2 billion and $8.5 billion"]),
    dict(given_in="Q3 FY25", quarter="Q4 FY25", lo=9.7, hi=10.1, check=["$9.7 billion and $10.1 billion"]),
    dict(given_in="Q4 FY25", quarter="Q1 FY26", lo=9.0, hi=9.4, check=["$9 billion to $9.4 billion"]),
    dict(given_in="Q1 FY26", quarter="Q2 FY26", lo=9.6, hi=10.0, check=["$9.6 billion to $10.0 billion"]),
    dict(given_in="Q2 FY26", quarter="Q3 FY26", lo=11.5, hi=12.1, check=["$11.5 billion to $12.1 billion"]),
    dict(given_in="Q3 FY26", quarter="Q4 FY26", lo=13.9, hi=14.8, check=["$13.9 billion to $14.8 billion", "$1.20 to $1.30"]),
]
# FY26 guidance by announcement (revenue growth, non-GAAP EPS, free cash flow $bn; None = open-ended "at least")
LADDER = [
    dict(doc="SAM", label="SAM\nOct-25", date="2025-10-15", rev_lo=0.17, rev_hi=0.22, eps_lo=2.20, eps_hi=2.40, fcf_lo=1.5, fcf_hi=2.0,
         check=["17 to 22% for FY26", "$2.20 and $2.40", "$1.5 billion to $2.0 billion"]),
    dict(doc="Q4 FY25", label="Q4 FY25\nDec-25", date="2025-12-04", rev_lo=0.17, rev_hi=0.22, eps_lo=2.25, eps_hi=2.45, fcf_lo=1.7, fcf_hi=2.0,
         check=["17% to 22%", "$2.25 to $2.45", "$1.7 billion to $2 billion"]),
    dict(doc="Q1 FY26", label="Q1 FY26\nMar-26", date="2026-03-09", rev_lo=0.17, rev_hi=0.22, eps_lo=2.30, eps_hi=2.50, fcf_lo=2.0, fcf_hi=None,
         check=["17% to 22%", "$2.30 to $2.50", "at least $2.0 billion"]),
    dict(doc="Q2 FY26", label="Q2 FY26\nJun-26", date="2026-06-01", rev_lo=0.29, rev_hi=0.33, eps_lo=3.35, eps_hi=3.45, fcf_lo=3.5, fcf_hi=None,
         check=["29% to 33%", "$3.35 to $3.45", "at least $3.5 billion"]),
    dict(doc="Q3 FY26", label="Q3 FY26\nSep-26", date="2026-09-02", rev_lo=0.34, rev_hi=0.37, eps_lo=3.75, eps_hi=3.85, fcf_lo=3.75, fcf_hi=None,
         check=["34% to 37%", "$3.75 to $3.85", "at least $3.75 billion"]),
]
FY27 = [
    dict(doc="Q2 FY26", date="2026-06-01", rev_lo=0.08, rev_hi=0.12, eps_growth_lo=0.12, eps_growth_hi=0.16, margin_lo=0.12, margin_hi=0.16,
         fcf_lo=4.5, check=["8% to 12%", "12% to 16%", "at least $4.5 billion"]),
    dict(doc="Q3 FY26", date="2026-09-02", rev_lo=0.13, rev_hi=0.17, eps_growth_lo=0.16, eps_growth_hi=0.20, margin_lo=0.14, margin_hi=0.15,
         fcf_lo=5.0, check=["13% to 17%", "16% to 20%", "14% to 15%", "at least $5.0 billion"]),
]
SAM_FY28 = dict(eps_at_least=3.00, fcf_more_than=3.5, check=["at least $3.00", "more than $3.5 billion"])
Q3_DETAIL = dict(
    op_margin=0.162, op_margin_yoy_pp=0.077, gaap_gm=0.401, gaap_op_margin=0.114, cfo_bn=1.6, fcf_m=958, orders_growth=0.42,
    ai_backlog_bn=7.6, networking_normalized_growth=0.10, networking_orders_growth=0.36, traditional_server_orders_growth=0.75,
    check_release=["Non-GAAP(1) of 16.2%, up 770 basis points", "GAAP of 40.1%", "GAAP of 11.4%", "operations: $1.6 billion"],
    check_slides=["$958M", "42% Orders growth", "$7.6B AI backlog", "+10% normalized", "orders up 36%",
                  "Traditional server orders up 75%"],
    check_call=["moderate toward more historical levels"],
)
CONSENSUS = dict(revenue_bn=12.1, eps=0.94, check=["pegged at $12.1 billion", "pegged at 94 cents"])


# ------------------------------------------------------------------------------------------ verification
def document_text(key: str) -> str:
    path = EARNINGS / DOCS[key]
    if path.suffix == ".pdf":
        text = " ".join(page.get_text() for page in pymupdf.open(path))
    else:
        raw = path.read_text(errors="ignore")
        text = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)))
    return re.sub(r"\s+", " ", text)


def verify() -> int:
    texts, missing, n = {}, [], 0

    def check(doc: str, strings: list[str]) -> None:
        nonlocal n
        texts.setdefault(doc, document_text(doc))
        for s in strings:
            n += 1
            if s not in texts[doc]:
                missing.append((doc, s))

    for q in QUARTERS:
        check(q["quarter"], q["check"])
    for g in REVENUE_GUIDE:
        check(g["given_in"], g["check"])
    for g in LADDER + FY27:
        check(g["doc"], g["check"])
    check("SAM", SAM_FY28["check"])
    check("Q3 FY26", Q3_DETAIL["check_release"])
    check("Q3 FY26 slides", Q3_DETAIL["check_slides"])
    check("Q3 FY26 call", Q3_DETAIL["check_call"])
    check("consensus", CONSENSUS["check"])
    if missing:
        raise AssertionError(f"keyed figures not found in their source documents: {missing}")
    return n


# ------------------------------------------------------------------------------------------ analysis
def scorecard() -> pd.DataFrame:
    rev = hpe_quarterly_revenue()
    q = pd.DataFrame([{k: v for k, v in d.items() if k != "check"} for d in QUARTERS]).set_index("quarter")
    q["period_end"] = [PERIOD_END[i] for i in q.index]
    q["revenue_m"] = [float(rev[pd.Timestamp(PERIOD_END[i])]) for i in q.index]
    prior = {i: float(rev[pd.Timestamp(PERIOD_END[i]) - pd.DateOffset(years=1) + pd.offsets.MonthEnd(0)]) for i in q.index}
    q["revenue_yoy"] = q["revenue_m"] / pd.Series(prior) - 1
    guide = pd.DataFrame(REVENUE_GUIDE).set_index("quarter")[["lo", "hi"]].rename(columns={"lo": "rev_guide_lo", "hi": "rev_guide_hi"})
    q = q.join(guide)
    q["rev_vs_guide_top"] = q["revenue_m"] / (q["rev_guide_hi"] * 1000) - 1
    q["rev_vs_guide_mid"] = q["revenue_m"] / ((q["rev_guide_lo"] + q["rev_guide_hi"]) / 2 * 1000) - 1
    q["eps_vs_guide_top"] = q["eps"] / q["eps_hi"] - 1
    q["eps_vs_guide_mid"] = q["eps"] / ((q["eps_lo"] + q["eps_hi"]) / 2) - 1
    seg = pd.read_csv(FIN_DATA / "hpe_segments_quarterly.csv")
    tot = seg[seg["line"] == "Total"].pivot_table(index="quarter", columns="segment", values=["revenue", "operating_profit"])
    for s, short in (("Networking", "net"), ("Cloud & AI", "cai")):
        q[f"{short}_revenue_m"] = tot[("revenue", s)].reindex(q.index)
        q[f"{short}_margin"] = (tot[("operating_profit", s)] / tot[("revenue", s)]).reindex(q.index)
    server = seg[seg["line"] == "Server"].set_index("quarter")["revenue"]
    q["server_revenue_m"] = server.reindex(q.index)
    q.to_csv(OUT / "quarterly_scorecard.csv")
    return q


def q3_analysis(q: pd.DataFrame) -> dict:
    now, prior = q.loc["Q3 FY26"], q.loc["Q3 FY25"]
    m_now, m_prior = Q3_DETAIL["op_margin"], Q3_DETAIL["op_margin"] - Q3_DETAIL["op_margin_yoy_pp"]
    op_now, op_prior = now["revenue_m"] * m_now, prior["revenue_m"] * m_prior
    volume = (now["revenue_m"] - prior["revenue_m"]) * m_prior
    margin = now["revenue_m"] * (m_now - m_prior)
    seg = pd.read_csv(FIN_DATA / "hpe_segments_quarterly.csv")
    server_prior = float(seg[(seg["line"] == "Server") & (seg["quarter"] == "Q3 FY25")]["revenue"].iloc[0])
    q4 = next(g for g in REVENUE_GUIDE if g["quarter"] == "Q4 FY26")
    q4_prior = float(hpe_quarterly_revenue()[pd.Timestamp("2025-10-31")])
    out = dict(
        revenue_m=now["revenue_m"], revenue_yoy=now["revenue_yoy"], gm=now["gm"], op_margin=m_now, op_margin_prior=m_prior,
        eps=now["eps"], eps_guide=[now["eps_lo"], now["eps_hi"]], revenue_guide=[now["rev_guide_lo"], now["rev_guide_hi"]],
        consensus_revenue_bn=CONSENSUS["revenue_bn"], consensus_eps=CONSENSUS["eps"],
        revenue_vs_consensus=now["revenue_m"] / (CONSENSUS["revenue_bn"] * 1000) - 1, eps_vs_consensus=now["eps"] / CONSENSUS["eps"] - 1,
        revenue_vs_guide_top=now["rev_vs_guide_top"], eps_vs_guide_top=now["eps_vs_guide_top"],
        op_profit_m=op_now, op_profit_prior_m=op_prior, op_profit_growth=op_now / op_prior - 1,
        bridge_volume_m=volume, bridge_margin_m=margin, margin_share_of_increase=margin / (volume + margin),
        fcf_m=Q3_DETAIL["fcf_m"], fcf_to_op_profit=Q3_DETAIL["fcf_m"] / op_now,
        networking_revenue_m=now["net_revenue_m"], networking_yoy=now["net_revenue_m"] / prior["net_revenue_m"] - 1,
        networking_margin=now["net_margin"], networking_normalized_growth=Q3_DETAIL["networking_normalized_growth"],
        networking_orders_growth=Q3_DETAIL["networking_orders_growth"],
        cloud_ai_revenue_m=now["cai_revenue_m"], cloud_ai_yoy=now["cai_revenue_m"] / prior["cai_revenue_m"] - 1,
        cloud_ai_margin=now["cai_margin"], cloud_ai_margin_prior=prior["cai_margin"],
        server_revenue_m=now["server_revenue_m"], server_yoy=now["server_revenue_m"] / server_prior - 1,
        orders_growth_normalized=Q3_DETAIL["orders_growth"], ai_backlog_bn=Q3_DETAIL["ai_backlog_bn"],
        traditional_server_orders_growth=Q3_DETAIL["traditional_server_orders_growth"],
        q4_guide=[q4["lo"], q4["hi"]], q4_eps_guide=[1.20, 1.30], q4_implied_yoy=[q4["lo"] * 1000 / q4_prior - 1, q4["hi"] * 1000 / q4_prior - 1],
    )
    return out


def guidance() -> tuple[pd.DataFrame, dict]:
    lad = pd.DataFrame([{k: v for k, v in d.items() if k != "check"} for d in LADDER])
    lad.to_csv(OUT / "fy26_guidance_ladder.csv", index=False)
    pd.DataFrame([{k: v for k, v in d.items() if k != "check"} for d in FY27]).to_csv(OUT / "fy27_framework.csv", index=False)
    first, last = lad.iloc[0], lad.iloc[-1]
    eps_raises = int((lad["eps_lo"].diff() > 0).sum())
    rev_raises = int((lad["rev_lo"].diff() > 0).sum())
    return lad, dict(
        fy26_revenue_growth_first=[first["rev_lo"], first["rev_hi"]], fy26_revenue_growth_last=[last["rev_lo"], last["rev_hi"]],
        fy26_revenue_mid_change_pp=(last["rev_lo"] + last["rev_hi"]) / 2 - (first["rev_lo"] + first["rev_hi"]) / 2,
        fy26_eps_first=[first["eps_lo"], first["eps_hi"]], fy26_eps_last=[last["eps_lo"], last["eps_hi"]],
        fy26_eps_mid_change=((last["eps_lo"] + last["eps_hi"]) / 2) / ((first["eps_lo"] + first["eps_hi"]) / 2) - 1,
        fy26_fcf_first=[first["fcf_lo"], first["fcf_hi"]], fy26_fcf_last_at_least=last["fcf_lo"],
        eps_guidance_raises=eps_raises, revenue_guidance_raises=rev_raises,
        sam_fy28_eps_at_least=SAM_FY28["eps_at_least"], sam_fy28_fcf_more_than=SAM_FY28["fcf_more_than"],
        fy27_june={k: v for k, v in FY27[0].items() if k != "check"}, fy27_september={k: v for k, v in FY27[1].items() if k != "check"},
        days_sam_to_q3=(pd.Timestamp(last["date"]) - pd.Timestamp(first["date"])).days,
    )


# ------------------------------------------------------------------------------------------ charts
def chart_beats(q: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 4.0))
    x = np.arange(len(q))
    for ax, (lo, hi, actual, label, fmt) in zip(axes, [
            ("eps_lo", "eps_hi", "eps", "Non-GAAP EPS against guidance range", lambda v: f"${v:.2f}"),
            ("rev_guide_lo", "rev_guide_hi", "revenue_bn", "Revenue against guidance range ($bn)", lambda v: f"${v:.1f}bn")]):
        rng = q[[lo, hi]].astype(float)
        has = rng.notna().all(axis=1).values
        ax.bar(x[has], (rng[hi] - rng[lo]).values[has], bottom=rng[lo].values[has], width=0.5, color=viz.CONTEXT,
               label="Guidance range (one quarter earlier)", zorder=2)
        ax.scatter(x, q[actual], s=46, color=viz.GREEN, zorder=4, label="Reported")
        for xi, v, top in zip(x, q[actual], rng[hi]):
            txt = fmt(v) + ("" if pd.isna(top) else f"\n{(v / top - 1) * 100:+.0f}% vs top")
            ax.annotate(txt, (xi, v), xytext=(0, 7), textcoords="offset points", ha="center", va="bottom", fontsize=7, color=viz.INK2)
        ax.set_xticks(x, q.index, fontsize=7.5)
        ax.set_ylim(0, q[actual].max() * 1.32)
        bma.panel_title(ax, label)
    axes[0].legend(loc="upper left", fontsize=7)
    texts = bma.header(fig, "In FY26, EPS beat guidance by far more than revenue did",
                       "Reported non-GAAP EPS and revenue (dots) against the range guided one quarter earlier; label = % above the top of the range",
                       "HPE earnings press releases Q2 FY25–Q3 FY26; Bona Fide analysis. Q2 FY25 revenue guidance not in the reviewed materials.")
    bma.save(fig, "earn_beat_guidance", texts, top=0.84)


def chart_ladder(lad: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 4.0))
    x = np.arange(len(lad))
    ax = axes[0]
    ax.bar(x, lad["rev_hi"] - lad["rev_lo"], bottom=lad["rev_lo"], width=0.5, color=viz.GREEN, zorder=2)
    for xi, lo, hi in zip(x, lad["rev_lo"], lad["rev_hi"]):
        ax.annotate(f"{lo * 100:.0f}–{hi * 100:.0f}%", (xi, hi), xytext=(0, 4), textcoords="offset points", ha="center", fontsize=7.5, color=viz.INK2)
    ax.set_ylim(0, 0.45)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    bma.panel_title(ax, "FY26 revenue growth guidance")
    ax = axes[1]
    ax.bar(x, lad["eps_hi"] - lad["eps_lo"], bottom=lad["eps_lo"], width=0.5, color=viz.GREEN, zorder=2)
    for xi, lo, hi in zip(x, lad["eps_lo"], lad["eps_hi"]):
        ax.annotate(f"${lo:.2f}–{hi:.2f}", (xi, hi), xytext=(0, 4), textcoords="offset points", ha="center", fontsize=7.5, color=viz.INK2)
    ax.axhline(SAM_FY28["eps_at_least"], color=viz.GOLD, lw=1.4, ls="--", zorder=1)
    ax.text(-0.35, SAM_FY28["eps_at_least"] + 0.05, "SAM target for FY28: ≥$3.00", fontsize=7.5, color=viz.INK2)
    ax.set_ylim(0, 4.5)
    bma.panel_title(ax, "FY26 non-GAAP EPS guidance ($)")
    for a in axes:
        a.set_xticks(x, lad["label"], fontsize=7)
    texts = bma.header(fig, "Guidance ratchet: FY26 EPS guidance raised four times in eleven months",
                       "Guidance ranges at the October 2025 analyst meeting (SAM) and each earnings release since",
                       "HPE SAM 2025 and earnings press releases; Bona Fide analysis.")
    bma.save(fig, "earn_guidance_ladder", texts, top=0.84)


def chart_beat_gap(q: pd.DataFrame) -> None:
    """Single panel for slides: % above the top of guidance, EPS against revenue, by quarter."""
    fig, ax = plt.subplots(figsize=(6.0, 2.9))
    x = np.arange(len(q))
    w = 0.36
    for off, col, colour, label in ((-w / 2, "eps_vs_guide_top", viz.GREEN, "Non-GAAP EPS"),
                                    (w / 2, "rev_vs_guide_top", viz.CONTEXT, "Revenue")):
        vals = q[col].astype(float)
        has = vals.notna().values
        ax.bar(x[has] + off, vals.values[has], width=w, color=colour, label=label, zorder=2)
        for xi, v in zip(x[has] + off, vals.values[has]):
            ax.annotate(f"{v * 100:+.0f}%", (xi, v), xytext=(0, 3 if v >= 0 else -9), textcoords="offset points",
                        ha="center", fontsize=7.5, color=viz.INK2)
    ax.axhline(0, color=viz.AXIS, lw=0.8, zorder=1)
    ax.set_xticks(x, q.index, fontsize=8)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_ylim(min(-0.08, float(q["rev_vs_guide_top"].min()) - 0.04), float(q["eps_vs_guide_top"].max()) + 0.08)
    ax.legend(loc="upper left", fontsize=8)
    texts = bma.header(fig, "EPS beat the top of guidance far more than revenue did",
                       "Reported result vs the top of the range guided one quarter earlier",
                       "HPE earnings press releases Q2 FY25–Q3 FY26; Bona Fide analysis. Q2 FY25 revenue guidance not in the reviewed materials.")
    bma.save(fig, "earn_beat_gap", texts, top=0.80)


def chart_eps_ladder(lad: pd.DataFrame) -> None:
    """Single panel for slides: FY26 non-GAAP EPS guidance by announcement against the SAM FY28 target."""
    fig, ax = plt.subplots(figsize=(4.6, 2.4))
    x = np.arange(len(lad))
    ax.bar(x, lad["eps_hi"] - lad["eps_lo"], bottom=lad["eps_lo"], width=0.55, color=viz.GREEN, zorder=2)
    for xi, lo, hi in zip(x, lad["eps_lo"], lad["eps_hi"]):
        ax.annotate(f"${lo:.2f}–{hi:.2f}", (xi, hi), xytext=(0, 4), textcoords="offset points", ha="center", fontsize=8, color=viz.INK2)
    ax.axhline(SAM_FY28["eps_at_least"], color=viz.GOLD, lw=1.4, ls="--", zorder=1)
    ax.text(-0.4, SAM_FY28["eps_at_least"] + 0.08, "FY28 target set at SAM: ≥$3.00", fontsize=8, color=viz.INK2)
    ax.set_ylim(1.5, 4.3)
    ax.set_xticks(x, lad["label"], fontsize=7.5)
    texts = bma.header(fig, "FY26 EPS guidance passed the FY28 target",
                       "FY26 non-GAAP EPS guidance range at each announcement ($)",
                       "HPE SAM 2025 and earnings press releases; Bona Fide analysis.")
    bma.save(fig, "earn_eps_guidance_ladder", texts, top=0.78)


def main() -> None:
    n = verify()
    q = scorecard()
    q3 = q3_analysis(q)
    lad, g = guidance()
    chart_beats(q)
    chart_ladder(lad)
    chart_beat_gap(q)
    chart_eps_ladder(lad)
    summary = dict(keyed_figures_verified=n, quarterly=json.loads(q.to_json(orient="index")), q3_fy26=q3, guidance=g,
                   consensus_source="Zacks via Yahoo Finance, 28-Aug-2026 (S252)")
    (OUT / "earnings_summary.json").write_text(json.dumps(summary, indent=2, default=float))
    pd.set_option("display.width", 220)
    print(f"verified {n} keyed figures against source documents")
    print(q[["revenue_m", "revenue_yoy", "rev_guide_lo", "rev_guide_hi", "rev_vs_guide_top", "eps", "eps_hi", "eps_vs_guide_top",
             "gm", "fcf_bn", "net_margin", "cai_margin"]].round(3).to_string())
    print(json.dumps({k: (round(float(v), 4) if isinstance(v, (float, int, np.floating, np.integer)) else v) for k, v in q3.items()}, indent=1, default=float))
    print(json.dumps(g, indent=1, default=float))


if __name__ == "__main__":
    main()
