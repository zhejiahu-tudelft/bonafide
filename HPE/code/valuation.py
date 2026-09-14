"""Valuation of HPE at the 11-Sep-2026 close: DCF (three scenarios), sensitivities, reverse DCF,
trading comparables, an M&A / control-premium view and a football field.

Conventions
  * Valuation date 11-Sep-2026; price $62.09; fully diluted shares from capital_structure.py.
  * Fiscal years end 31-Oct. Explicit forecast FY27E–FY36E plus a Q4 FY26E stub; mid-period discounting.
  * FCFF = EBIT × (1 − tax) + depreciation − capex − ΔNWC, where EBIT = non-GAAP operating profit
    less stock-based compensation (SBC treated as a real expense) less remaining restructuring cash costs.
  * Financial Services is valued on a consolidated basis (its revenue, capex and receivables are inside
    the drivers), so all consolidated debt — including debt funding FS receivables — is deducted.
  * No rating or price target is produced: outputs are value ranges.

Outputs: data/processed_data/valuation/*.csv, valuation_summary.json, key_metrics.json; charts.
"""
from __future__ import annotations

import datetime as dt
import json

import numpy as np
import pandas as pd

import viz
from common import FIN_DATA, MKT_DATA, PROC, VALUATION_DATE

OUT = PROC / "valuation"
OUT.mkdir(exist_ok=True)
CAP = json.loads((PROC / "capital" / "capital_summary.json").read_text())
FIN = pd.read_csv(PROC / "financials" / "hpe_financials.csv", index_col=0)
SEG = json.loads((PROC / "segments" / "segment_summary.json").read_text())

# ----------------------------------------------------------------------------- cost of capital
RF = float(pd.read_csv(MKT_DATA / "macro" / "DGS10.csv").dropna()["value"].iloc[-1]) / 100   # 10Y UST, last obs.
ERP = 0.0397            # Damodaran implied ERP at start of 2026 (histimpl.xls, 2025 row)
UNLEVERED_BETA = {"Computers/Peripherals": 1.324587, "Telecom. Equipment": 0.887251}  # Damodaran betas.xls, Jan-2026, cash-corrected
BBB_SPREAD = 0.011113   # Baa2/BBB default spread, large firms (Damodaran synthetic-rating table, Jan-2026); HPE rated BBB by S&P
MARGINAL_TAX = 0.21
OPERATING_TAX = 0.17    # HPE structural non-GAAP tax rate 14% (FY26) plus a margin for cash-tax leakage


def cost_of_capital() -> dict:
    net_share = SEG["networking_share_of_segment_profit"]
    beta_u = net_share * UNLEVERED_BETA["Telecom. Equipment"] + (1 - net_share) * UNLEVERED_BETA["Computers/Peripherals"]
    e, d = CAP["market_cap_fully_diluted_m"], CAP["gross_debt_m"]
    beta_l = beta_u * (1 + (1 - MARGINAL_TAX) * d / e)
    ke = RF + beta_l * ERP
    kd = RF + BBB_SPREAD
    wacc = e / (e + d) * ke + d / (e + d) * kd * (1 - MARGINAL_TAX)
    return dict(risk_free=RF, erp=ERP, networking_profit_weight=net_share, unlevered_beta=beta_u, debt_to_equity=d / e,
                levered_beta=beta_l, cost_of_equity=ke, pre_tax_cost_of_debt=kd, after_tax_cost_of_debt=kd * (1 - MARGINAL_TAX),
                equity_weight=e / (e + d), debt_weight=d / (e + d), wacc=wacc)


# ----------------------------------------------------------------------------- scenarios
FY26E_REVENUE = 46_500   # guidance +34–37% on FY25 $34,296m → $45,957–46,986m; consensus $46,377m
FY26E_Q4_FCFF = 1_100    # analyst estimate: FY26 FCF guide ≥$3.75bn less 9M $2.58bn, plus after-tax interest, less SBC
YEARS = [f"FY{y}E" for y in range(2027, 2037)]

SCENARIOS = {
    "Bear": dict(
        growth=[0.10, -0.03, 0.02, 0.025, 0.025, 0.025, 0.02, 0.02, 0.02, 0.02],
        margin=[0.130, 0.110, 0.105, 0.105, 0.105, 0.105, 0.105, 0.105, 0.105, 0.105],
        nwc=0.07, terminal_growth=0.0225, probability=0.25,
        story="AI-server digestion and memory-cost normalisation reverse FY26 ASP gains; networking share loss to Cisco/Arista; "
              "margins revert toward the pre-Juniper mix-adjusted ~10–11%."),
    "Base": dict(
        growth=[0.15, 0.06, 0.05, 0.045, 0.04, 0.0375, 0.035, 0.0325, 0.03, 0.0275],
        margin=[0.145, 0.135, 0.130, 0.125, 0.125, 0.125, 0.125, 0.125, 0.125, 0.125],
        nwc=0.06, terminal_growth=0.0275, probability=0.50,
        story="FY27 in line with the raised framework (+13–17% revenue, 14–15% non-GAAP margin); growth fades to "
              "IDC/Gartner-consistent mid-single digits; margin settles at 12.5% as AI mix offsets networking mix."),
    "Bull": dict(
        growth=[0.17, 0.09, 0.07, 0.06, 0.05, 0.045, 0.04, 0.04, 0.035, 0.035],
        margin=[0.150, 0.150, 0.148, 0.145, 0.145, 0.145, 0.145, 0.145, 0.145, 0.145],
        nwc=0.05, terminal_growth=0.0325, probability=0.25,
        story="Networking (Oracle, Helios scale-up switches) lifts mix toward 30%+ of revenue at mid/high-20s margins; "
              "enterprise AI inference sustains server demand; margins hold near FY27 levels."),
}
SBC_PCT = 0.018           # TTM SBC / revenue 1.9%
RESTRUCTURING_CASH = [300, 150] + [0] * 8   # SAM 2025 FAQ: ~$450m cash costs FY27–FY28
DEPRECIATION_PCT = 0.050  # depreciation (ex acquired-intangible amortisation) / revenue: TTM 5.3%
CAPEX_OVER_DEP = 0.002    # net capex slightly above depreciation (growth + FS operating-lease equipment)
TERMINAL_RONIC = 0.12     # return on new invested capital in perpetuity (sets terminal reinvestment)


def years_from_valuation(fy_end_year: int, mid: bool = True) -> float:
    vd = dt.date.fromisoformat(VALUATION_DATE)
    end = dt.date(fy_end_year, 10, 31)
    point = end - dt.timedelta(days=182) if mid else end
    return (point - vd).days / 365.25


def dcf(s: dict, wacc: float, overrides: dict | None = None, detail: bool = False):
    s = {**s, **(overrides or {})}
    rev_prev = FY26E_REVENUE
    rows, pv = [], 0.0
    pv += FY26E_Q4_FCFF / (1 + wacc) ** (30 / 365.25)
    for i, fy in enumerate(YEARS):
        rev = rev_prev * (1 + s["growth"][i])
        ebit = rev * (s["margin"][i] - SBC_PCT) - RESTRUCTURING_CASH[i]
        nopat = ebit * (1 - OPERATING_TAX)
        dep = rev * DEPRECIATION_PCT
        capex = rev * (DEPRECIATION_PCT + CAPEX_OVER_DEP)
        dnwc = s["nwc"] * (rev - rev_prev)
        fcff = nopat + dep - capex - dnwc
        t = years_from_valuation(2027 + i)
        df = 1 / (1 + wacc) ** t
        pv += fcff * df
        rows.append(dict(year=fy, revenue=rev, growth=s["growth"][i], non_gaap_margin=s["margin"][i], ebit=ebit,
                         nopat=nopat, depreciation=dep, capex=capex, delta_nwc=dnwc, fcff=fcff, t=t, discount_factor=df,
                         pv_fcff=fcff * df))
        rev_prev = rev
    g = s["terminal_growth"]
    last = rows[-1]
    nopat_next = last["nopat"] * (1 + g) if RESTRUCTURING_CASH[-1] == 0 else last["nopat"] * (1 + g)
    fcff_next = nopat_next * (1 - g / TERMINAL_RONIC)
    tv = fcff_next / (wacc - g)
    pv_tv = tv / (1 + wacc) ** years_from_valuation(2036, mid=False)
    ev = pv + pv_tv
    equity = ev - CAP["gross_debt_m"] + CAP["cash_m"] - CAP["nci_m"]
    per_share = equity / CAP["fully_diluted_shares_m"]
    out = dict(pv_explicit=pv, terminal_value=tv, pv_terminal=pv_tv, enterprise_value=ev, equity_value=equity,
               value_per_share=per_share, tv_share_of_ev=pv_tv / ev,
               implied_ev_to_fy27_ebitda=ev / (rows[0]["revenue"] * rows[0]["non_gaap_margin"] + rows[0]["depreciation"]))
    return (out, pd.DataFrame(rows)) if detail else out


def solve(fn, target: float, lo: float, hi: float, iters: int = 80) -> float:
    flo = fn(lo) - target
    for _ in range(iters):
        mid = (lo + hi) / 2
        fm = fn(mid) - target
        if np.sign(fm) == np.sign(flo):
            lo, flo = mid, fm
        else:
            hi = mid
    return (lo + hi) / 2


CORE_PEERS = ["DELL", "CSCO", "NTAP", "SMCI"]  # closest models; Arista and Everpure shown in tables but excluded
                                                # from implied values (software-like margins and growth premia)


def own_history_forward_pe() -> pd.Series:
    """HPE fiscal-year-end close / next fiscal year's actual non-GAAP EPS (perfect-foresight forward P/E)."""
    px = pd.read_csv(MKT_DATA / "HPE_daily.csv", parse_dates=["date"]).set_index("date")["close"]
    ng = pd.read_csv(FIN_DATA / "hpe_non_gaap_annual.csv")
    eps = ng[ng.metric == "non_gaap_diluted_eps"].set_index("period")["value"]
    return pd.Series({f"FY{fy}": float(px.loc[:f"{fy}-10-31"].iloc[-1] / eps[f"FY{fy + 1}"]) for fy in range(2020, 2025)})


def comps_values(price: float) -> pd.DataFrame:
    m = pd.read_csv(PROC / "peers" / "peer_multiples.csv", index_col=0)
    core = m.loc[CORE_PEERS]
    eps_fy27 = pd.read_csv(MKT_DATA / "yahoo" / "yahoo_HPE_earnings_estimate.csv", index_col=0).at["+1y", "avg"]
    net_claims = CAP["gross_debt_m"] - CAP["cash_m"] + CAP["nci_m"]
    shares = CAP["fully_diluted_shares_m"]
    gaap_ebitda = FIN.at["ebitda", "TTM Q3 FY26"]
    to_equity = lambda ev_mult, base: (ev_mult * base - net_claims) / shares
    rows = []

    def add(method, metric, base, mults: pd.Series, conv, current, note):
        mults = mults.replace([np.inf, -np.inf], np.nan).dropna()
        mults = mults[mults > 0]
        lo, mid, hi = mults.min(), mults.median(), mults.max()
        rows.append(dict(method=method, metric=metric, base_value=base, multiple_low=lo, multiple_mid=mid, multiple_high=hi,
                         value_low=conv(lo), value_mid=conv(mid), value_high=conv(hi), hpe_current_multiple=current,
                         note=note + " | " + ", ".join(f"{k} {v:.1f}x" for k, v in mults.items())))

    add("P/E next FY (core peers)", "HPE FY27 consensus non-GAAP EPS", eps_fy27, core["P/E (next FY cons.)"],
        lambda x: x * eps_fy27, price / eps_fy27, "Core peers min–median–max")
    add("EV/EBITDA TTM, GAAP basis (core peers)", "HPE TTM GAAP EBITDA", gaap_ebitda, core["EV/EBITDA (TTM GAAP)"],
        lambda x: to_equity(x, gaap_ebitda), (price * shares + net_claims) / gaap_ebitda, "Core peers with data")
    hist = own_history_forward_pe()
    add("HPE own forward P/E history (FY20–FY24)", "HPE FY27 consensus non-GAAP EPS", eps_fy27, hist,
        lambda x: x * eps_fy27, price / eps_fy27, "Year-end price / next-year actual non-GAAP EPS")

    # Sum of the parts on TTM EBIT after SBC: corporate costs, CIO and SBC allocated by segment revenue
    seg = pd.read_csv(PROC / "segments" / "segments_ttm.csv", index_col=0)
    seg_op = seg["operating_profit"]
    corp = FIN.at["non_gaap_operating_profit", "TTM Q3 FY26"] - seg_op.sum()
    shared = corp + seg_op["Corporate Investments and Other"] - FIN.at["sbc", "TTM Q3 FY26"]
    w_net = seg.at["Networking", "revenue"] / (seg.at["Networking", "revenue"] + seg.at["Cloud & AI", "revenue"])
    ebit_net, ebit_cai = seg_op["Networking"] + w_net * shared, seg_op["Cloud & AI"] + (1 - w_net) * shared
    net_mult = m.at["CSCO", "EV/EBIT (TTM GAAP)"]
    hw_mult = m.loc[["DELL", "NTAP"], "EV/EBIT (TTM GAAP)"].median()
    ev_mid = ebit_net * net_mult + ebit_cai * hw_mult
    rows.append(dict(method="Sum of the parts (segment EV/EBIT)", metric="TTM segment EBIT after SBC and corporate costs",
                     base_value=ebit_net + ebit_cai, multiple_low=np.nan, multiple_mid=ev_mid / (ebit_net + ebit_cai),
                     multiple_high=np.nan, value_low=to_equity(0.85, ev_mid), value_mid=to_equity(1.0, ev_mid),
                     value_high=to_equity(1.15, ev_mid), hpe_current_multiple=(price * shares + net_claims) / (ebit_net + ebit_cai),
                     note=f"Networking EBIT ${ebit_net:,.0f}m × Cisco {net_mult:.1f}x; Cloud & AI EBIT ${ebit_cai:,.0f}m × "
                          f"Dell/NetApp median {hw_mult:.1f}x; ±15%"))
    return pd.DataFrame(rows)


def main() -> None:
    price = CAP["price"]
    coc = cost_of_capital()
    wacc = coc["wacc"]

    results, details = {}, {}
    for name, s in SCENARIOS.items():
        res, det = dcf(s, wacc, detail=True)
        results[name], details[name] = res, det
        det.to_csv(OUT / f"dcf_{name.lower()}.csv", index=False)
    prob_value = sum(SCENARIOS[n]["probability"] * results[n]["value_per_share"] for n in SCENARIOS)
    base = SCENARIOS["Base"]

    # Sensitivities (base case)
    waccs = [wacc + d for d in (-0.01, -0.005, 0, 0.005, 0.01)]
    gs = [base["terminal_growth"] + d for d in (-0.0075, -0.005, -0.0025, 0, 0.0025, 0.005)]
    grid_wg = pd.DataFrame([[dcf(base, w, {"terminal_growth": g})["value_per_share"] for g in gs] for w in waccs],
                           index=[f"{w:.2%}" for w in waccs], columns=[f"{g:.2%}" for g in gs])
    grid_wg.to_csv(OUT / "sensitivity_wacc_growth.csv")
    shifts = (-0.02, -0.01, 0, 0.01, 0.02)
    margins_lt = (0.105, 0.115, 0.125, 0.135, 0.145)
    grid_mg = pd.DataFrame(
        [[dcf(base, wacc, {"growth": [g + sh for g in base["growth"]],
                           "margin": base["margin"][:2] + [max(m_lt, 0) if i >= 2 else base["margin"][i] for i in range(2, 10)]})
          ["value_per_share"] for m_lt in margins_lt] for sh in shifts],
        index=[f"{sh:+.0%} p.a. growth" for sh in shifts], columns=[f"{m:.1%} LT margin" for m in margins_lt])
    grid_mg.to_csv(OUT / "sensitivity_growth_margin.csv")

    # One-at-a-time driver sensitivity (tornado)
    def lt_margin(v):
        return {"margin": base["margin"][:2] + [v] * 8}
    drivers = {
        "WACC ±1.0pp": (lambda: dcf(base, wacc + 0.01), lambda: dcf(base, wacc - 0.01)),
        "Long-term non-GAAP margin ±1.5pp": (lambda: dcf(base, wacc, lt_margin(0.11)), lambda: dcf(base, wacc, lt_margin(0.14))),
        "Terminal growth ±0.5pp": (lambda: dcf(base, wacc, {"terminal_growth": base["terminal_growth"] - 0.005}),
                                   lambda: dcf(base, wacc, {"terminal_growth": base["terminal_growth"] + 0.005})),
        "Revenue growth ±2pp p.a.": (lambda: dcf(base, wacc, {"growth": [g - 0.02 for g in base["growth"]]}),
                                     lambda: dcf(base, wacc, {"growth": [g + 0.02 for g in base["growth"]]})),
        "NWC intensity ±3pp of Δrevenue": (lambda: dcf(base, wacc, {"nwc": base["nwc"] + 0.03}),
                                           lambda: dcf(base, wacc, {"nwc": base["nwc"] - 0.03})),
    }
    base_v = results["Base"]["value_per_share"]
    tornado = pd.DataFrame([(k, lo()["value_per_share"], hi()["value_per_share"]) for k, (lo, hi) in drivers.items()],
                           columns=["driver", "low_case", "high_case"])
    tornado["range"] = tornado["high_case"] - tornado["low_case"]
    tornado = tornado.sort_values("range")
    tornado.to_csv(OUT / "driver_sensitivity.csv", index=False)

    # Reverse DCF: what the price implies
    implied_margin = solve(lambda m: dcf(base, wacc, lt_margin(m))["value_per_share"], price, 0.05, 0.40)
    implied_growth_shift = solve(lambda sh: dcf(base, wacc, {"growth": [g + sh for g in base["growth"]]})["value_per_share"],
                                 price, -0.10, 0.15)
    implied_wacc = solve(lambda w: -dcf(base, w)["value_per_share"], -price, 0.05, 0.15)
    both = solve(lambda sh: dcf(base, wacc, {"growth": [g + sh for g in base["growth"]], **lt_margin(0.145)})["value_per_share"],
                 price, -0.10, 0.20)
    reverse = dict(implied_long_term_margin_at_base_growth=implied_margin,
                   implied_growth_uplift_pp_at_base_margin=implied_growth_shift,
                   implied_wacc_at_base_case=implied_wacc,
                   implied_growth_uplift_if_margin_holds_at_fy27_level=both,
                   implied_fy27_36_revenue_cagr_at_base_margin=float(np.prod([1 + g + implied_growth_shift for g in base["growth"]]) ** 0.1 - 1),
                   base_fy27_36_revenue_cagr=float(np.prod([1 + g for g in base["growth"]]) ** 0.1 - 1))

    comps = comps_values(price)
    comps.to_csv(OUT / "comps_implied_values.csv", index=False)

    # M&A view: control premium on the unaffected (1-month average) price and on the base DCF value
    px = pd.read_csv(MKT_DATA / "HPE_daily.csv", parse_dates=["date"]).set_index("date").loc[:VALUATION_DATE, "close"]
    unaffected = float(px.iloc[-21:].mean())
    ma = pd.DataFrame([
        dict(method="Control premium 25–35% on 1-month average price", low=unaffected * 1.25, high=unaffected * 1.35,
             basis=f"1-month average close ${unaffected:.2f}; 25–35% typical US control premium (FactSet/BVR study range); "
                   "HPE paid 32% for Juniper"),
        dict(method="Control premium 25–35% on base-case DCF value", low=base_v * 1.25, high=base_v * 1.35,
             basis="Strategic value incl. synergies proxied by premium to intrinsic value"),
    ])
    ma.to_csv(OUT / "ma_values.csv", index=False)

    # Football field
    stock = json.loads((PROC / "stock" / "stock_summary.json").read_text())
    targets = json.loads((MKT_DATA / "yahoo" / "yahoo_HPE_analyst_price_targets.json").read_text())
    ff = [
        ("52-week trading range (closes)", stock["low52"], stock["high52"]),
        ("Sell-side price targets (low–high)", targets["low"], targets["high"]),
        ("DCF: bear to bull scenarios", results["Bear"]["value_per_share"], results["Bull"]["value_per_share"]),
        ("DCF base: WACC ±0.5pp, g ±0.25pp", float(grid_wg.iloc[1:4, 2:5].min().min()), float(grid_wg.iloc[1:4, 2:5].max().max())),
    ]
    for _, r in comps.iterrows():
        ff.append((r["method"], r["value_low"], r["value_high"]))
    ff.append((ma.iloc[0]["method"], ma.iloc[0]["low"], ma.iloc[0]["high"]))
    ff = pd.DataFrame(ff, columns=["method", "low", "high"])
    ff.to_csv(OUT / "football_field.csv", index=False)

    fair_low = float(np.percentile([results["Bear"]["value_per_share"], ff.iloc[3]["low"]], 50))
    summary = dict(
        valuation_date=VALUATION_DATE, price=price, cost_of_capital=coc,
        scenarios={n: {**{k: v for k, v in results[n].items()}, "probability": SCENARIOS[n]["probability"],
                       "terminal_growth": SCENARIOS[n]["terminal_growth"], "story": SCENARIOS[n]["story"],
                       "fy27_revenue": float(details[n].at[0, "revenue"]), "fy36_revenue": float(details[n].iloc[-1]["revenue"]),
                       "lt_margin": SCENARIOS[n]["margin"][-1]} for n in SCENARIOS},
        probability_weighted_value=prob_value,
        upside_to_probability_weighted=prob_value / price - 1,
        reverse_dcf=reverse,
        dcf_base_sensitivity_range=[float(grid_wg.iloc[1:4, 2:5].min().min()), float(grid_wg.iloc[1:4, 2:5].max().max())],
        fair_value_range_dcf=[results["Bear"]["value_per_share"], results["Bull"]["value_per_share"]],
        fair_value_core_range=[float(grid_wg.iloc[1:4, 2:5].min().min()), float(grid_wg.iloc[1:4, 2:5].max().max())],
        unaffected_price_1m_avg=unaffected,
    )
    (OUT / "valuation_summary.json").write_text(json.dumps(summary, indent=2, default=float))

    # ---------------- charts
    fig, ax = viz.figure(8, 3.6)
    y = np.arange(len(ff))[::-1]
    for yi, r in zip(y, ff.itertuples()):
        ax.barh(yi, r.high - r.low, left=r.low, height=0.5, color=viz.GREEN if "DCF" in r.method else viz.CONTEXT)
        ax.text(r.low - 1, yi, f"${r.low:.0f}", va="center", ha="right", fontsize=7.5, color=viz.INK2)
        ax.text(r.high + 1, yi, f"${r.high:.0f}", va="center", ha="left", fontsize=7.5, color=viz.INK2)
    ax.axvline(price, color=viz.INK, lw=1.2, zorder=4)
    ax.text(price, len(ff) - 0.35, f" Price ${price:.2f}", fontsize=8, color=viz.INK)
    ax.axvline(prob_value, color=viz.GOLD, lw=1.2, zorder=4)
    ax.text(prob_value, -0.85, f"Prob.-weighted DCF ${prob_value:.0f} ", fontsize=8, color=viz.INK2, ha="right")
    ax.set_yticks(y, ff["method"])
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=viz.GRID, lw=0.6)
    ax.set_xlim(0, ff["high"].max() * 1.12)
    ax.set_ylim(-1.2, len(ff) - 0.2)
    ax.xaxis.set_major_formatter(viz.mtick.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    viz.titles(ax, "Valuation range: fundamentals support less than the market price in our base case",
               "Value per fully diluted share by method (DCF in green) vs 11-Sep-2026 close")
    viz.source(fig, "Bona Fide DCF and comps; Yahoo Finance targets and prices; HPE filings.")
    viz.save(fig, "val_football_field")

    fig, ax = viz.figure(8, 2.9)
    yy = np.arange(len(tornado))
    ax.barh(yy, tornado["high_case"] - base_v, left=base_v, height=0.5, color=viz.GREEN, label="Favourable")
    ax.barh(yy, tornado["low_case"] - base_v, left=base_v, height=0.5, color=viz.GOLD, label="Adverse")
    for i, r in enumerate(tornado.itertuples()):
        ax.text(r.high_case + 0.8, i, f"${r.high_case:.0f}", va="center", fontsize=7.5, color=viz.INK2)
        ax.text(r.low_case - 0.8, i, f"${r.low_case:.0f}", va="center", ha="right", fontsize=7.5, color=viz.INK2)
    ax.axvline(base_v, color=viz.INK, lw=1, zorder=1)
    ax.set_yticks(yy, tornado["driver"])
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=viz.GRID, lw=0.6)
    ax.set_xlim(tornado["low_case"].min() - 10, tornado["high_case"].max() + 10)
    ax.xaxis.set_major_formatter(viz.mtick.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.legend(loc="lower right")
    viz.titles(ax, "Long-term margin and WACC move value most; growth matters less",
               f"Base-case DCF value per share (${base_v:.0f}) flexing one driver at a time")
    viz.source(fig, "Bona Fide DCF model (excel/HPE_valuation_model.xlsx).")
    viz.save(fig, "val_driver_sensitivity")

    fig, ax = viz.figure(8, 3.0)
    for name, col in (("Bear", viz.GOLD), ("Base", viz.GREEN), ("Bull", viz.BLUE)):
        d = details[name]
        ax.plot(d["year"], d["fcff"] / 1000, color=col, marker="o", ms=4, label=f"{name} (${results[name]['value_per_share']:.0f}/sh)")
    ax.set_ylabel("FCFF $bn")
    ax.legend(loc="upper left", ncol=3)
    viz.titles(ax, "Scenario free cash flow paths", "Unlevered free cash flow (SBC treated as expense), FY27E–FY36E")
    viz.source(fig, "Bona Fide DCF model.")
    viz.save(fig, "val_scenario_fcff")

    pd.set_option("display.width", 220)
    print(json.dumps(coc, indent=1))
    for n in SCENARIOS:
        print(n, {k: round(v, 3) for k, v in results[n].items()})
        print(details[n][["year", "revenue", "non_gaap_margin", "ebit", "fcff", "pv_fcff"]].round(0).to_string())
    print("Probability-weighted:", round(prob_value, 2))
    print(grid_wg.round(1)); print(grid_mg.round(1)); print(tornado.round(1))
    print(json.dumps(reverse, indent=1)); print(comps.round(2).to_string()); print(ma.round(2)); print(ff.round(1))


if __name__ == "__main__":
    main()
