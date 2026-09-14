"""Practitioner Q&A 2: three business models in the AI data-centre supply chain.

  Landlords         Digital Realty (DLR), Keel Infrastructure (KEEL): develop and lease powered data-centre space
  Neoclouds         IREN, CoreWeave (CRWV), Nebius (NBIS): own GPU clusters and rent out compute under contracts
  Server providers  HPE, Dell (DELL): sell the equipment that goes inside the building

A. Financial profile   TTM to the latest filing: asset mix, capex, D&A and interest intensity, margins, contracted
                       backlog; revenue stability over 2017-2026 for the long-history names; GPU useful-life
                       sensitivity for CoreWeave and Nebius
B. Phase shift         stylised 100 MW unit economics (cumulative cash flow and GAAP operating profit per unit of
                       capital committed); DLR development-capex -> revenue cross-correlation
C. AI elasticity       revenue growth on hyperscaler capex growth (HAC, lags 0-4); daily-return factor model on the
                       market (SPY), an AI factor (NVDA orthogonal to SPY), bitcoin and the 10-year yield
D. Portfolio frontier  equal-weight group baskets; long-only minimum-variance and tangency weights; pairwise corner
                       test (rho >= sigma_low / sigma_high); stationary block bootstrap of the weights

Inputs: SEC XBRL company facts (data/financial_data); DLR's Q2 2026 10-Q inline XBRL for the quarter the companyfacts
API had not yet published; Nebius figures keyed from its FY2025 20-F and Q2 2026 6-K (it files no quarterly XBRL);
keyed contract, asset-life and cost parameters from report/other_evidence/practitioner_qa/q2; prices and rates.
Outputs: data/processed_data/qa/q2_*.csv, q2_summary.json; charts qa_q2_profile, qa_q2_phase_shift,
qa_q2_elasticity, qa_q2_frontier.
"""
from __future__ import annotations

import json
import re
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import optimize

import viz
from common import CHARTS, FIN_DATA, MKT_DATA, OTHER, PROC, VALUATION_DATE
from macro_industry_analysis import combined_quarters
from statistical_analysis import capex_growth, fiscal_calendar_quarter

warnings.filterwarnings("ignore")
OUT = PROC / "qa"
OUT.mkdir(exist_ok=True)
EVID = OTHER / "practitioner_qa" / "q2"
ASOF = pd.Timestamp(VALUATION_DATE)

GROUPS = {"Landlords": ["DLR", "KEEL"], "Neoclouds": ["IREN", "CRWV", "NBIS"], "Server providers": ["HPE", "DELL"]}
GROUP_OF = {t: g for g, ts in GROUPS.items() for t in ts}
TICKERS = [t for ts in GROUPS.values() for t in ts]
COLOUR = {"Landlords": viz.BLUE, "Neoclouds": viz.ORANGE, "Server providers": viz.GREEN}
NAME = {"DLR": "Digital Realty", "KEEL": "Keel Infra.", "IREN": "IREN", "CRWV": "CoreWeave", "NBIS": "Nebius",
        "HPE": "HPE", "DELL": "Dell"}
FIRST_CLEAN_DAY = {"NBIS": "2024-10-21", "CRWV": "2025-03-28"}  # Nebius relisted after the Yandex split; CoreWeave IPO
AI_ERA_START, ROBUST_START, COMMON_START = "2023-01-01", "2024-10-21", "2025-03-28"

DURATION = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"],
    "operating_income": ["OperatingIncomeLoss"],
    "d_and_a": ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets",
              "PaymentsToDevelopRealEstateAssets"],
    "cfo": ["NetCashProvidedByUsedInOperatingActivities"],
    "interest": ["InterestExpense", "InterestExpenseNonoperating", "InterestExpenseDebt"],
}
INSTANT = {
    "assets": ["Assets"],
    "current_assets": ["AssetsCurrent"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue"],
    "ppe_net": ["PropertyPlantAndEquipmentNet",
                "PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization",
                "RealEstateInvestmentPropertyNet"],
    "rou": ["OperatingLeaseRightOfUseAsset"],
    "rpo": ["RevenueRemainingPerformanceObligation"],
}
IXBRL_SUPPLEMENT = {"DLR": ("DLR_10Q_2026-07-31_dlr-20260630x10q.htm", "2026-07-31")}

# Digital Realty re-presented operating income from Q2 2026 (gains on real estate transactions moved inside it, prior
# quarters restated). TTM on the new basis excluding those gains, from the Q2 2026 financial supplement ($m):
# quarter end -> (operating income, gain on real estate transactions)
DLR_OPINC_NEW_BASIS = {"2025-09-30": (158.2, 19.8), "2025-12-31": (155.5, 42.9), "2026-03-31": (267.8, 0.2),
                       "2026-06-30": (467.2, 8.0)}
# Nebius files 20-F / 6-K without quarterly XBRL: $m keyed from the FY2025 20-F (NBIS_20F_2026-04-30_*) and the
# Q2 2026 6-K MD&A and interim statements (NBIS_6K_2026-08-12_nbis-20260812xex99d1/d2)
NBIS_KEYED = {
    "FY2025": dict(revenue=529.8, operating_income=-611.7, d_and_a=417.9, interest=61.5, cfo=384.8, capex=4066.0),
    "6M2025": dict(revenue=156.0, operating_income=-231.5, d_and_a=124.3, interest=4.8, cfo=-352.0, capex=1054.5),
    "6M2026": dict(revenue=981.3, operating_income=-303.9, d_and_a=471.7, interest=182.8, cfo=4504.1, capex=8130.3),
    "2026-06-30": dict(assets=27961.5, current_assets=9615.6, ppe_net=13045.2, rou=1855.1, rpo=37490.6),
}
# Keyed disclosures ($m unless stated) — each from a document in report/other_evidence/practitioner_qa/q2
KEYED = {
    "IREN_lease_contracted": 11400.0,   # 10-K FY2026: aggregate contracted value of lease arrangements (ASC 842)
    "DLR_backlog_annual_rent": 1900.0,  # Q2 2026 release: signed-not-commenced leases, annualised GAAP rent, 100% share
    "DLR_walt_years": 4.1,              # Q2 2026 supplement: weighted average remaining lease term
    "DLR_commencement_lag_months": 9,   # Q2 2026 release: lag between signing and commencement
    "DLR_stabilised_yield": 0.10,       # 2026 guidance: average stabilised development yield 10.0%+
    "CRWV_ppe_gross": dict(technology=33823, software=859, data_center=5997, furniture=25),  # 10-Q Q2 2026
    "CRWV_lives": dict(technology=6, software=4.5, data_center=12, furniture=4),              # 10-K FY2025
    "NBIS_ppe_gross": dict(servers=5197.7, other_in_service=14149.5 - 7836.4 - 5197.7),      # 6-K Q2 2026, note 7
    "NBIS_lives": dict(servers=5, other_in_service=20),  # servers 4 -> 5 years from Jan-2026; other: assumption
    "HPE_ai_backlog": 7600.0, "DELL_ai_backlog": 95000.0, "DELL_isg_margin": 0.150,
    # stylised 100 MW parameters
    "ai_facility_cost_per_mw": 17.5,    # $m/MW, AI-optimised facility $15-20m+ (iRecruit, citing JLL 2026)
    "facility_life_years": 25,          # assumption: straight-line life of the building and power infrastructure
    "build_quarters": 6,                # assumption: 18-month construction
    "neocloud_acv_per_mw": 22.5,        # $m/MW/yr, Nebius Q2 2026 deals $20-25m per MW
    "neocloud_payback_years": 2.0,      # IREN FY26: contracts >$20m revenue per MW, ~2-year payback
    "neocloud_ebitda_margin": 0.59,     # CoreWeave Q2 2026 adjusted EBITDA margin
    "contract_years": 5,                # CoreWeave weighted-average contract duration
    "gpu_life_years": 6,                # CoreWeave technology equipment
    "rerent_price": 0.4,                # assumption: price for out-of-contract GPUs until the refresh
}


# ------------------------------------------------------------------------------------------ fundamentals
def ixbrl_facts(path, filed: str) -> dict[str, list[dict]]:
    """Non-dimensional us-gaap facts from an inline-XBRL filing, in companyfacts format."""
    raw = path.read_text(errors="ignore")
    ctx = {}
    for cid, body in re.findall(r'<xbrli:context id="([^"]+)">(.*?)</xbrli:context>', raw, re.S):
        if "<xbrli:segment>" in body:
            continue
        inst = re.search(r"<xbrli:instant>([^<]+)", body)
        if inst:
            ctx[cid] = {"end": inst.group(1)}
        else:
            ctx[cid] = {"start": re.search(r"<xbrli:startDate>([^<]+)", body).group(1),
                        "end": re.search(r"<xbrli:endDate>([^<]+)", body).group(1)}
    out: dict[str, list[dict]] = {}
    for attrs, text in re.findall(r"<ix:nonFraction([^>]*)>(.*?)</ix:nonFraction>", raw, re.S):
        a = dict(re.findall(r'([\w:]+)="([^"]*)"', attrs))
        c, name = ctx.get(a.get("contextRef")), a.get("name", "")
        if c is None or not name.startswith("us-gaap:"):
            continue
        txt = re.sub(r"<[^>]+>", "", text).strip().replace(",", "")
        try:
            val = 0.0 if txt in ("", "-", "—") else float(txt)
        except ValueError:
            continue
        val *= 10 ** int(a.get("scale", "0"))
        out.setdefault(name[len("us-gaap:"):], []).append({**c, "val": -val if a.get("sign") == "-" else val,
                                                            "form": "10-Q", "filed": filed})
    return out


def load_facts(tk: str) -> dict:
    f = json.loads((FIN_DATA / f"companyfacts_{tk}.json").read_text())["facts"].get("us-gaap", {})
    if tk in IXBRL_SUPPLEMENT:  # add only periods newer than companyfacts, never restated comparatives
        doc, filed = IXBRL_SUPPLEMENT[tk]
        for name, vals in ixbrl_facts(EVID / doc, filed).items():
            node = f.setdefault(name, {"units": {"USD": []}})["units"].setdefault("USD", [])
            last = max((v["end"] for v in node), default="")
            node.extend(v for v in vals if v["end"] > last)
    return f


def quarterly(f: dict, key: str) -> pd.Series:
    tags = [t for t in DURATION[key] if t in f and "USD" in f[t]["units"]]
    try:
        return combined_quarters(f, tags).sort_index() / 1e6
    except IndexError:
        return pd.Series(dtype=float)


def ttm(s: pd.Series) -> tuple[float, pd.Timestamp | None]:
    s = s[s.index <= ASOF].dropna()
    last4 = s.iloc[-4:]
    if len(last4) < 4 or (last4.index[-1] - last4.index[0]).days > 300:
        return np.nan, None
    return float(last4.sum()), last4.index[-1]


def ttm_from_ytd(f: dict, key: str) -> tuple[float, pd.Timestamp | None]:
    """TTM = last fiscal year + current year-to-date - prior year-to-date (for gaps in the quarterly chain)."""
    vals = [v for t in DURATION[key] if t in f and "USD" in f[t]["units"] for v in f[t]["units"]["USD"]
            if "start" in v and v.get("form") in ("10-Q", "10-K") and v["end"] <= VALUATION_DATE]
    if not vals:
        return np.nan, None
    d = pd.DataFrame(vals)
    d["start"], d["end"] = pd.to_datetime(d["start"]), pd.to_datetime(d["end"])
    d["days"] = (d["end"] - d["start"]).dt.days
    d = d.sort_values("filed").drop_duplicates(["start", "end"], keep="last")
    annual = d[(d["days"] > 350) & (d["days"] < 380)].sort_values("end")
    if annual.empty:
        return np.nan, None
    fy = annual.iloc[-1]
    ytd = d[(d["start"] == fy["end"] + pd.Timedelta(days=1)) & (d["days"] < 350)].sort_values("end")
    if ytd.empty:
        return float(fy["val"]) / 1e6, fy["end"]
    cur = ytd.iloc[-1]
    prior = d[(d["start"] == fy["start"]) & ((d["end"] - (cur["end"] - pd.DateOffset(years=1))).abs() <= pd.Timedelta(days=7))]
    if prior.empty:
        return np.nan, None
    return float(fy["val"] + cur["val"] - prior.iloc[-1]["val"]) / 1e6, cur["end"]


def instant(f: dict, key: str) -> float:
    best = None
    for tag in INSTANT[key]:
        node = f.get(tag)
        if not node or "USD" not in node["units"]:
            continue
        vals = [v for v in node["units"]["USD"] if "start" not in v and v["end"] <= VALUATION_DATE]
        if vals and (best is None or max(v["end"] for v in vals) > max(v["end"] for v in best)):
            best = vals
    if not best:
        return np.nan
    end = max(v["end"] for v in best)
    return sorted([v for v in best if v["end"] == end], key=lambda v: v.get("filed", ""))[-1]["val"] / 1e6


def nbis_row() -> dict:
    k = NBIS_KEYED
    row = {m: k["FY2025"][m] + k["6M2026"][m] - k["6M2025"][m] for m in DURATION}
    row.update(k["2026-06-30"], cash=np.nan, ttm_end=pd.Timestamp("2026-06-30"))
    return row


def financial_profile() -> tuple[pd.DataFrame, dict]:
    rows, series = [], {}
    for tk in TICKERS:
        if tk == "NBIS":
            row = nbis_row()
        else:
            f = load_facts(tk)
            q = {k: quarterly(f, k) for k in DURATION}
            series[tk] = q
            row = {}
            for k, s in q.items():
                row[k], end = ttm(s)
                if np.isnan(row[k]):
                    row[k], end = ttm_from_ytd(f, k)
                if k == "revenue":
                    row["ttm_end"] = end
            row.update({k: instant(f, k) for k in INSTANT})
            if tk == "DLR":
                row["operating_income"] = sum(op - gain for op, gain in DLR_OPINC_NEW_BASIS.values())
        rows.append({"ticker": tk, "group": GROUP_OF[tk], **row})
    df = pd.DataFrame(rows).set_index("ticker")
    df["interest"] = df["interest"].abs()
    # REIT balance sheets are unclassified: approximate current assets by cash
    df["noncurrent_basis"] = np.where(df["current_assets"].isna(), "assets less cash (unclassified)", "classified")
    df["noncurrent_share"] = 1 - df["current_assets"].fillna(df["cash"]) / df["assets"]
    df["long_lived_share"] = (df["ppe_net"] + df["rou"].fillna(0)) / df["assets"]
    df["asset_turnover"] = df["revenue"] / df["assets"]
    df["capex_to_revenue"] = df["capex"] / df["revenue"]
    df["da_to_revenue"] = df["d_and_a"] / df["revenue"]
    df["interest_to_revenue"] = df["interest"] / df["revenue"]
    df["committed_cost_ratio"] = (df["d_and_a"] + df["interest"]) / df["revenue"]
    df["operating_margin"] = df["operating_income"] / df["revenue"]
    df["ebitda_margin"] = (df["operating_income"] + df["d_and_a"]) / df["revenue"]
    df["fcf_margin"] = (df["cfo"] - df["capex"]) / df["revenue"]
    contracted = df["rpo"].copy()
    contracted["IREN"] = df.loc["IREN", "rpo"] + KEYED["IREN_lease_contracted"]
    # estimate: in-place rent runs for the weighted average remaining lease term; backlog rent for a similar term
    contracted["DLR"] = (df.loc["DLR", "revenue"] + KEYED["DLR_backlog_annual_rent"]) * KEYED["DLR_walt_years"]
    contracted["KEEL"] = 0.0  # no data-centre lease signed at 10-Aug-2026
    df["contracted"] = contracted
    df["contract_basis"] = pd.Series({"DLR": "estimate: (TTM revenue + backlog rent) x 4.1-yr WALT",
                                      "KEEL": "no lease signed", "IREN": "RPO + contracted lease value",
                                      "CRWV": "RPO", "NBIS": "RPO (6-K)", "HPE": "RPO", "DELL": "RPO"})
    df["contract_coverage"] = df["contracted"] / df["revenue"]
    df.to_csv(OUT / "q2_financial_profile.csv", date_format="%Y-%m-%d")
    return df, series


def revenue_stability(series: dict) -> pd.DataFrame:
    """How far and how often TTM revenue fell, 2017-2026 (long-history names only)."""
    rows = []
    for tk in ("DLR", "HPE", "DELL"):
        rev = series[tk]["revenue"]
        t4 = rev[(rev.index >= "2016-11-01") & (rev.index <= ASOF)].rolling(4).sum().dropna()
        yoy = (t4 / t4.shift(4) - 1).dropna()
        rows.append(dict(ticker=tk, first=str(yoy.index[0].date()), last=str(yoy.index[-1].date()), n=len(yoy),
                         growth_sd=float(yoy.std()), worst_yoy=float(yoy.min()), best_yoy=float(yoy.max()),
                         share_quarters_declining=float((yoy < 0).mean())))
    out = pd.DataFrame(rows).set_index("ticker")
    out.to_csv(OUT / "q2_revenue_stability.csv")
    return out


def useful_life_sensitivity(df: pd.DataFrame) -> pd.DataFrame:
    """TTM operating income if GPU/server equipment were depreciated over other lives (straight-line proxy)."""
    rows = []
    for tk, gross, lives, eq, base in (("CRWV", KEYED["CRWV_ppe_gross"], KEYED["CRWV_lives"], "technology", 6),
                                        ("NBIS", KEYED["NBIS_ppe_gross"], KEYED["NBIS_lives"], "servers", 5)):
        dep = {k: gross[k] / lives[k] for k in gross}
        share = dep[eq] / sum(dep.values())
        gpu_da = df.loc[tk, "d_and_a"] * share
        for life in (6, 5, 4, 3):
            op = df.loc[tk, "operating_income"] - gpu_da * (base / life - 1)
            rows.append(dict(ticker=tk, reported_life=base, life=life, gpu_share_of_da=share, operating_income=op,
                             operating_margin=op / df.loc[tk, "revenue"]))
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "q2_useful_life_sensitivity.csv", index=False)
    return out


# ------------------------------------------------------------------------------------------ B. phase shift
def dlr_capex_revenue_lag(series: dict) -> pd.DataFrame:
    s = pd.DataFrame({"capex": series["DLR"]["capex"], "revenue": series["DLR"]["revenue"]}).dropna()
    g = np.log(s.rolling(4).sum().dropna()).diff(4).dropna()
    out = pd.DataFrame([dict(lag_quarters=k, corr=g["capex"].shift(k).corr(g["revenue"]),
                             n=int(g["capex"].shift(k).notna().sum())) for k in range(0, 13)])
    out.to_csv(OUT / "q2_lags.csv", index=False)
    return out


def stylised_models(df: pd.DataFrame, horizon: int = 48) -> tuple[pd.DataFrame, dict]:
    """Quarterly cash flow and GAAP operating profit for 100 MW of AI capacity under each model ($m)."""
    k, q = KEYED, np.arange(horizon)
    mw, build_q = 100, k["build_quarters"]
    live_q = build_q
    # landlord: builds the facility, rent (at a 10% stabilised yield on cost) starts when it goes live
    facility = k["ai_facility_cost_per_mw"] * mw
    l_capex = np.where(q < build_q, facility / build_q, 0.0)
    l_noi = np.where(q >= live_q, facility * k["DLR_stabilised_yield"] / 4, 0.0)
    l_dep = np.where(q >= live_q, facility / (k["facility_life_years"] * 4), 0.0)
    # neocloud: rents the facility (in opex), buys GPUs the quarter before go-live, 5-year contract, refresh at 6 years
    gpu = k["neocloud_payback_years"] * k["neocloud_acv_per_mw"] * k["neocloud_ebitda_margin"] * mw
    life_q, contract_q = k["gpu_life_years"] * 4, k["contract_years"] * 4
    n_capex, n_rev, n_dep, n_dep4 = (np.zeros(horizon) for _ in range(4))
    for start in range(live_q, horizon, life_q):
        n_capex[start - 1] += gpu
        for t in range(start, min(start + life_q, horizon)):
            n_rev[t] = k["neocloud_acv_per_mw"] * mw / 4 * (1.0 if t < start + contract_q else k["rerent_price"])
            n_dep[t] = gpu / life_q
        for t in range(start, min(start + 16, horizon)):
            n_dep4[t] = gpu / 16
    n_ebitda = n_rev * k["neocloud_ebitda_margin"]
    # server provider: ships the GPU systems the quarter they are bought; builds inventory a quarter ahead and
    # collects a quarter after shipment
    margin = k["DELL_isg_margin"]
    s_rev = n_capex.copy()
    s_cash = -np.roll(s_rev, -1) * (1 - margin) + np.roll(s_rev, 1)
    capital = {"landlord": facility, "neocloud": gpu, "server": gpu * (1 - margin)}
    model = pd.DataFrame({
        "quarter": q, "landlord_cash": l_noi - l_capex, "landlord_operating_profit": l_noi - l_dep,
        "neocloud_cash": n_ebitda - n_capex, "neocloud_operating_profit": n_ebitda - n_dep,
        "neocloud_operating_profit_4yr_life": n_ebitda - n_dep4,
        "server_cash": s_cash, "server_operating_profit": s_rev * margin,
    })
    for m in ("landlord", "neocloud", "server"):
        model[f"{m}_cum_cash_x"] = model[f"{m}_cash"].cumsum() / capital[m]
        model[f"{m}_cum_profit_x"] = model[f"{m}_operating_profit"].cumsum() / capital[m]
    model["neocloud_cum_profit_4yr_x"] = model["neocloud_operating_profit_4yr_life"].cumsum() / capital["neocloud"]
    model.to_csv(OUT / "q2_stylised_unit_economics.csv", index=False)
    stats = {}
    for m in ("landlord", "neocloud", "server"):
        cum = model[f"{m}_cash"].cumsum()
        trough = int(cum.idxmin())
        payback = model.loc[(cum >= 0) & (model["quarter"] > trough), "quarter"]
        first_profit = model.loc[model[f"{m}_operating_profit"] > 0, "quarter"]
        stats[m] = dict(capital=float(capital[m]), trough_quarter=trough,
                        payback_quarter=int(payback.iloc[0]) if len(payback) else None,
                        first_profit_quarter=int(first_profit.iloc[0]) if len(first_profit) else None,
                        cum_cash_x_year12=float(model[f"{m}_cum_cash_x"].iloc[-1]),
                        cum_profit_x_year12=float(model[f"{m}_cum_profit_x"].iloc[-1]))
    stats["neocloud"]["cum_profit_x_year12_4yr_life"] = float(model["neocloud_cum_profit_4yr_x"].iloc[-1])
    return model, stats


# ------------------------------------------------------------------------------------------ C. AI elasticity
def calendar(s: pd.Series) -> pd.Series:
    s = s.copy()
    s.index = [fiscal_calendar_quarter(d) for d in s.index]
    return s[~s.index.duplicated(keep="last")]


def fundamental_elasticity(series: dict) -> pd.DataFrame:
    cap = capex_growth()
    rows, coefs = [], []
    for tk in ("DLR", "HPE", "DELL"):
        rev = series[tk]["revenue"]
        g = np.log(calendar(rev[(rev.index >= "2016-11-01") & (rev.index <= ASOF)])).diff(4).rename("growth")
        X = pd.concat({f"capex_lag{k}": cap.shift(k) for k in range(5)}, axis=1)
        d = pd.concat([g, X], axis=1).dropna()
        m = sm.OLS(d["growth"], sm.add_constant(d.drop(columns="growth"))).fit(cov_type="HAC", cov_kwds={"maxlags": 4})
        wald = m.t_test(" + ".join(X.columns) + " = 0")
        single = {c: sm.OLS(d["growth"], sm.add_constant(d[[c]])).fit(cov_type="HAC", cov_kwds={"maxlags": 4})
                  for c in X.columns}
        best = max(single, key=lambda c: single[c].tvalues[c])
        rows.append(dict(ticker=tk, n=int(m.nobs), sample=f"{d.index[0]}–{d.index[-1]}", sum_of_lags=float(wald.effect[0]),
                         sum_p=float(wald.pvalue), r2=float(m.rsquared), best_single_lag=int(best[-1]),
                         best_lag_coef=float(single[best].params[best]), best_lag_p=float(single[best].pvalues[best]),
                         best_lag_r2=float(single[best].rsquared)))
        coefs.append(pd.DataFrame({"ticker": tk, "coef": m.params, "p": m.pvalues}))
    # neoclouds and Keel: too short for regression; TTM revenue growth against hyperscaler TTM capex growth
    capq = pd.read_csv(FIN_DATA / "industry" / "hyperscaler_capex_quarterly.csv", index_col=0)
    capex_ttm_growth = float(capq["ttm_yoy"].dropna().iloc[-1])
    for tk in ("KEEL", "IREN", "CRWV", "NBIS"):
        if tk == "NBIS":  # prior-year TTM not disclosed quarterly: first-half growth instead
            growth, basis = NBIS_KEYED["6M2026"]["revenue"] / NBIS_KEYED["6M2025"]["revenue"] - 1, "H1 YoY"
        else:
            t4 = series[tk]["revenue"].dropna().rolling(4).sum().dropna()
            ok = len(t4) >= 5 and (t4.index[-1] - t4.index[-5]).days < 380
            growth, basis = (float(t4.iloc[-1] / t4.iloc[-5] - 1) if ok else np.nan), "TTM YoY"
        rows.append(dict(ticker=tk, sample="descriptive", revenue_growth=growth, growth_basis=basis,
                         hyperscaler_ttm_capex_growth=capex_ttm_growth))
    out = pd.DataFrame(rows).set_index("ticker")
    out.to_csv(OUT / "q2_elasticity_fundamental.csv")
    pd.concat(coefs).to_csv(OUT / "q2_elasticity_fundamental_coefficients.csv")
    return out


def prices() -> pd.DataFrame:
    px = pd.DataFrame({t: pd.read_csv(MKT_DATA / f"{t}_daily.csv", parse_dates=["date"]).set_index("date")["adj_close"]
                       for t in TICKERS + ["SPY", "NVDA"]})
    px = px[px.index <= ASOF].sort_index()
    for tk, day in FIRST_CLEAN_DAY.items():
        px.loc[px.index < day, tk] = np.nan
    btc = pd.read_csv(MKT_DATA / "BTC-USD_daily.csv", parse_dates=["date"]).set_index("date")["adj_close"].sort_index()
    px["BTC"] = btc.reindex(btc.index.union(px.index)).ffill().reindex(px.index)
    return px


def factor_model(rets: pd.DataFrame) -> pd.DataFrame:
    y10 = pd.read_csv(MKT_DATA / "macro" / "DGS10.csv", parse_dates=["date"]).set_index("date")["value"]
    y10 = pd.to_numeric(y10, errors="coerce").sort_index()
    rates = y10.reindex(y10.index.union(rets.index)).ffill().reindex(rets.index).diff() * 10   # per +10bp
    era = rets.loc[AI_ERA_START:, ["NVDA", "SPY"]].dropna()
    b = sm.OLS(era["NVDA"], sm.add_constant(era["SPY"])).fit()
    factors = pd.DataFrame({"market": rets["SPY"], "ai": rets["NVDA"] - b.params["const"] - b.params["SPY"] * rets["SPY"],
                            "bitcoin": rets["BTC"], "rates_10bp": rates})
    rows = []
    for tk in TICKERS:
        for window, start in (("own", max(AI_ERA_START, FIRST_CLEAN_DAY.get(tk, AI_ERA_START))), ("common", COMMON_START)):
            d = pd.concat([rets[tk].rename("y"), factors], axis=1)
            d = d[d.index > start].dropna()
            m = sm.OLS(d["y"], sm.add_constant(d[factors.columns])).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
            ci = m.conf_int()
            for fac in factors.columns:
                rows.append(dict(ticker=tk, group=GROUP_OF[tk], window=window, start=str(d.index[0].date()), n=int(m.nobs),
                                 factor=fac, beta=m.params[fac], ci_low=ci.loc[fac, 0], ci_high=ci.loc[fac, 1],
                                 p=m.pvalues[fac], r2=m.rsquared))
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "q2_elasticity_market.csv", index=False)
    return out


# ------------------------------------------------------------------------------------------ D. portfolio
def baskets(rets: pd.DataFrame, start: str, groups: dict) -> pd.DataFrame:
    r = rets[rets.index > start]
    return pd.DataFrame({g: r[m].mean(axis=1, skipna=True) for g, m in groups.items()}).dropna()


def _simplex(n: int) -> dict:
    return dict(bounds=[(0, 1)] * n, constraints={"type": "eq", "fun": lambda w: w.sum() - 1}, method="SLSQP")


def min_variance(cov: np.ndarray) -> np.ndarray:
    return optimize.minimize(lambda w: w @ cov @ w, np.ones(len(cov)) / len(cov), **_simplex(len(cov))).x


def tangency(mu: np.ndarray, cov: np.ndarray, rf: float) -> np.ndarray:
    n = len(cov)
    best = None
    for w0 in [np.ones(n) / n] + [np.eye(n)[i] * 0.98 + 0.01 for i in range(n)]:
        res = optimize.minimize(lambda w: -(w @ mu - rf) / np.sqrt(w @ cov @ w), w0, **_simplex(n))
        if best is None or res.fun < best.fun:
            best = res
    return best.x


def frontier(mu: np.ndarray, cov: np.ndarray, names: list) -> pd.DataFrame:
    w_mv = min_variance(cov)
    pts = []
    for target in np.linspace(w_mv @ mu, mu.max(), 40):
        res = optimize.minimize(lambda w: w @ cov @ w, w_mv, bounds=[(0, 1)] * len(mu), method="SLSQP",
                                constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1},
                                             {"type": "eq", "fun": lambda w, t=target: w @ mu - t}])
        if res.success:
            pts.append(dict(ret=target, vol=float(np.sqrt(res.x @ cov @ res.x)), **dict(zip(names, res.x))))
    return pd.DataFrame(pts)


def stationary_bootstrap_index(n: int, mean_block: int, rng: np.random.Generator) -> np.ndarray:
    idx = np.empty(n, dtype=int)
    idx[0] = rng.integers(n)
    jumps, draws = rng.random(n) < 1 / mean_block, rng.integers(n, size=n)
    for t in range(1, n):
        idx[t] = draws[t] if jumps[t] else (idx[t - 1] + 1) % n
    return idx


def bootstrap_weights(b: pd.DataFrame, rf: float, draws: int = 2000, block: int = 20) -> tuple[pd.DataFrame, dict]:
    rng, x, names = np.random.default_rng(20260911), b.values, list(b.columns)
    rows = []
    for _ in range(draws):
        s = x[stationary_bootstrap_index(len(x), block, rng)]
        mu_b, cov_b = s.mean(axis=0) * 252, np.cov(s, rowvar=False) * 252
        rows.append({**{f"mv_{g}": w for g, w in zip(names, min_variance(cov_b))},
                     **{f"tan_{g}": w for g, w in zip(names, tangency(mu_b, cov_b, rf))}})
    boot = pd.DataFrame(rows)
    stats = {kind: {g: dict(zero_weight_share=float((boot[f"{kind}_{g}"] < 0.01).mean()),
                            p5=float(boot[f"{kind}_{g}"].quantile(0.05)), median=float(boot[f"{kind}_{g}"].median()),
                            p95=float(boot[f"{kind}_{g}"].quantile(0.95))) for g in names} for kind in ("mv", "tan")}
    for kind in ("mv", "tan"):
        stats[f"all_positive_{kind}_share"] = float((boot[[f"{kind}_{g}" for g in names]] >= 0.01).all(axis=1).mean())
    stats.update(draws=draws, mean_block_days=block)
    return boot, stats


def portfolio(rets: pd.DataFrame) -> tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dtb3 = pd.to_numeric(pd.read_csv(MKT_DATA / "macro" / "DTB3.csv", parse_dates=["date"]).set_index("date")["value"],
                         errors="coerce")
    variants = (("main", COMMON_START, GROUPS), ("robust", ROBUST_START, GROUPS),
                ("dlr_only", COMMON_START, {**GROUPS, "Landlords": ["DLR"]}))
    summary, rows = {}, []
    for label, start, groups in variants:
        b = baskets(rets, start, groups)
        names = list(b.columns)
        rf = float(dtb3[(dtb3.index > start) & (dtb3.index <= ASOF)].mean() / 100)
        mu, cov = b.mean().values * 252, b.cov().values * 252
        vol, corr, wealth = np.sqrt(np.diag(cov)), b.corr(), (1 + b).cumprod()
        w_mv, w_tan = min_variance(cov), tangency(mu, cov, rf)
        pairs = []
        for i in range(3):
            for j in range(i + 1, 3):
                lo, hi = (i, j) if vol[i] <= vol[j] else (j, i)
                rho = float(corr.iloc[i, j])
                w_lo = (vol[hi] ** 2 - rho * vol[lo] * vol[hi]) / (vol[lo] ** 2 + vol[hi] ** 2 - 2 * rho * vol[lo] * vol[hi])
                pairs.append(dict(low_vol=names[lo], high_vol=names[hi], rho=rho, vol_ratio=float(vol[lo] / vol[hi]),
                                  corner=bool(rho >= vol[lo] / vol[hi]), w_low_analytic=float(np.clip(w_lo, 0, 1)),
                                  w_low_optimiser=float(min_variance(cov[np.ix_([lo, hi], [lo, hi])])[0])))
        summary[label] = dict(members={g: m for g, m in groups.items()}, start=str(b.index[0].date()),
                              end=str(b.index[-1].date()), n_days=len(b), rf=rf,
                              stats={g: dict(ann_return=float(mu[k]), ann_vol=float(vol[k]), sharpe=float((mu[k] - rf) / vol[k]),
                                             max_drawdown=float((wealth[g] / wealth[g].cummax() - 1).min()))
                                     for k, g in enumerate(names)},
                              corr=corr.round(3).to_dict(), min_variance=dict(zip(names, map(float, w_mv))),
                              tangency=dict(zip(names, map(float, w_tan))), pairs=pairs,
                              min_variance_vol=float(np.sqrt(w_mv @ cov @ w_mv)),
                              tangency_sharpe=float((w_tan @ mu - rf) / np.sqrt(w_tan @ cov @ w_tan)))
        rows += [dict(window=label, basket=g, **summary[label]["stats"][g]) for g in names]
        if label in ("main", "dlr_only"):
            boot, bstats = bootstrap_weights(b, rf)
            boot.to_csv(OUT / f"q2_bootstrap_weights_{label}.csv", index=False)
            summary[f"bootstrap_{label}"] = bstats
        if label == "main":
            main_b, main_boot = b, boot
            front = frontier(mu, cov, names)
            front.to_csv(OUT / "q2_frontier.csv", index=False)
            b.rolling(60).corr().dropna().to_csv(OUT / "q2_rolling_corr_60d.csv")
    pd.DataFrame(rows).to_csv(OUT / "q2_portfolio.csv", index=False)
    return summary, main_b, front, main_boot


# ------------------------------------------------------------------------------------------ charts
def header(fig, title: str, subtitle: str, source: str) -> list:
    return [fig.text(0.01, 0.995, title, fontsize=11, fontweight="bold", color=viz.INK, va="top"),
            fig.text(0.01, 0.955, subtitle, fontsize=8.5, color=viz.INK2, va="top"),
            fig.text(0.01, 0.0, f"Source: {source}", fontsize=7, color=viz.MUTED, va="top")]


def save(fig, name: str, texts: list, top: float = 0.90) -> None:
    """PNG/SVG with title, subtitle and source; deck variant without them (the slide carries those)."""
    fig.tight_layout(rect=(0, 0.02, 1, top))
    fig.savefig(CHARTS / f"{name}.svg", bbox_inches="tight")
    fig.savefig(CHARTS / f"{name}.png", dpi=220, bbox_inches="tight")
    for t in texts:
        t.set_visible(False)
    fig.savefig(CHARTS / f"{name}_deck.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def panel_title(ax, text: str) -> None:
    ax.text(0, 1.03, text, transform=ax.transAxes, fontsize=8.5, fontweight="bold", color=viz.INK)


def legend_groups(ax, loc: str = "lower right") -> None:
    ax.legend([plt.Rectangle((0, 0), 1, 1, color=COLOUR[g]) for g in GROUPS], list(GROUPS), loc=loc, fontsize=7.5)


def chart_profile(df: pd.DataFrame) -> None:
    panels = [("noncurrent_share", "Non-current assets / total assets", "pct", (0, 1.0)),
              ("capex_to_revenue", "Capex / revenue", "x", (0, 6.0)),
              ("da_to_revenue", "Depreciation & amortisation / revenue", "pct", (0, 1.0)),
              ("interest_to_revenue", "Interest expense / revenue", "pct", (0, 0.4)),
              ("operating_margin", "GAAP operating margin", "pct", (-2.0, 0.5)),
              ("contract_coverage", "Contracted backlog / revenue", "x", (0, 30.0))]
    fig, axes = plt.subplots(2, 3, figsize=(9.6, 5.6))
    order = TICKERS[::-1]
    for ax, (col, label, kind, (lo, hi)) in zip(axes.flat, panels):
        vals = df.loc[order, col]
        shown = vals.clip(lo, hi).fillna(0)
        ax.barh([NAME[t] for t in order], shown, color=[COLOUR[GROUP_OF[t]] for t in order], height=0.66)
        ax.grid(axis="x"); ax.grid(axis="y", visible=False); ax.tick_params(axis="y", length=0)
        ax.axvline(0, color=viz.AXIS, lw=0.8, zorder=1)
        span = hi - lo
        for y, (t, v) in enumerate(vals.items()):
            if pd.isna(v):
                txt = "n/a"
            elif kind == "pct":
                txt = f"{v:.0%}"
            else:
                txt = f"{v:.2f}x" if abs(v) < 0.1 else f"{v:.1f}x"
            clipped = not pd.isna(v) and (v > hi or v < lo)
            xpos = float(shown[t])
            ax.text(xpos + (0.02 * span if xpos >= 0 else -0.02 * span), y, txt + (" ▸" if clipped else ""),
                    va="center", ha="left" if xpos >= 0 else "right", fontsize=7, color=viz.INK2)
        if kind == "pct":
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
        ax.set_xlim(lo - (0.3 * span if lo < 0 else 0), hi + 0.3 * span)
        panel_title(ax, label)
    legend_groups(axes.flat[1])
    texts = header(fig, "Three business models, three financial profiles",
                   "TTM to the latest filing (Jun/Jul-2026); ▸ = value beyond the axis",
                   "SEC XBRL; company 10-K, 10-Q, 20-F and 6-K filings; Bona Fide analysis. DLR backlog coverage is an estimate; "
                   "DLR operating income excludes real-estate gains.")
    save(fig, "qa_q2_profile", texts)


def chart_phase(model: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(8, 5.4), sharex=True)
    years = model["quarter"] / 4
    for m, g in (("landlord", "Landlords"), ("neocloud", "Neoclouds"), ("server", "Server providers")):
        axes[0].plot(years, model[f"{m}_cum_cash_x"], color=COLOUR[g], label=g)
        axes[1].plot(years, model[f"{m}_cum_profit_x"], color=COLOUR[g], label=g)
    axes[1].plot(years, model["neocloud_cum_profit_4yr_x"], color=COLOUR["Neoclouds"], ls="--", lw=1.2,
                 label="Neoclouds, 4-year GPU life")
    for ax in axes:
        ax.axhline(0, color=viz.AXIS, lw=0.8, zorder=1)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.1f}x"))
        ax.legend(loc="upper left", fontsize=7.5)
    panel_title(axes[0], "Cumulative cash flow ÷ capital committed")
    panel_title(axes[1], "Cumulative GAAP operating profit ÷ capital committed")
    axes[1].set_xlabel("Years from the start of construction", color=viz.INK2)
    texts = header(fig, "The phase shift: who pays first and who books profit first",
                   "Stylised 100 MW AI deployment; capital = facility cost, GPU capex or inventory funded; parameters in the text",
                   "Bona Fide stylised model using DLR, CoreWeave, Nebius, IREN and Dell disclosures and a JLL build-cost benchmark.")
    save(fig, "qa_q2_phase_shift", texts, top=0.89)


def chart_elasticity(mkt: pd.DataFrame) -> None:
    labels = {"ai": "AI factor beta (NVDA, ex-market)", "market": "Market beta (S&P 500)",
              "bitcoin": "Bitcoin beta", "rates_10bp": "Return per +10bp 10-year yield"}
    d = mkt[mkt["window"] == "common"]
    fig, axes = plt.subplots(2, 2, figsize=(8.6, 5.4))
    order = TICKERS[::-1]
    for ax, (fac, label) in zip(axes.flat, labels.items()):
        s = d[d["factor"] == fac].set_index("ticker").loc[order]
        y = np.arange(len(order))
        ax.barh(y, s["beta"], color=[COLOUR[GROUP_OF[t]] for t in order], height=0.62)
        ax.errorbar(s["beta"], y, xerr=[s["beta"] - s["ci_low"], s["ci_high"] - s["beta"]], fmt="none",
                    ecolor=viz.INK2, elinewidth=0.8, capsize=2, zorder=4)
        ax.set_yticks(y, [NAME[t] for t in order])
        ax.axvline(0, color=viz.AXIS, lw=0.8, zorder=1)
        ax.grid(axis="x"); ax.grid(axis="y", visible=False); ax.tick_params(axis="y", length=0)
        if fac == "rates_10bp":
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.1%}"))
        panel_title(ax, label)
    legend_groups(axes.flat[0])
    texts = header(fig, "Share-price elasticity: neoclouds carry the most AI beta",
                   f"Daily returns {d['start'].iloc[0]} to {VALUATION_DATE}; four-factor OLS; Newey-West 95% intervals",
                   "Yahoo Finance prices, FRED 10-year yield; Bona Fide analysis.")
    save(fig, "qa_q2_elasticity", texts, top=0.89)


def chart_frontier(port: dict, b: pd.DataFrame, front: pd.DataFrame, boot: pd.DataFrame, rets: pd.DataFrame) -> None:
    main = port["main"]
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.2), gridspec_kw={"width_ratios": [1.5, 1]})
    ax = axes[0]
    r = rets[rets.index > COMMON_START]
    for tk in TICKERS:
        s = r[tk].dropna()
        x, y = s.std() * np.sqrt(252), s.mean() * 252
        ax.scatter(x, y, s=14, color=COLOUR[GROUP_OF[tk]], alpha=0.45, zorder=3)
        ax.annotate(NAME[tk], (x, y), xytext=(3, 2), textcoords="offset points", fontsize=6.5, color=viz.MUTED)
    ax.plot(front["vol"], front["ret"], color=viz.INK2, lw=1.6, zorder=2, label="Efficient frontier (long-only)")
    for g, st in main["stats"].items():
        ax.scatter(st["ann_vol"], st["ann_return"], s=60, color=COLOUR[g], edgecolor="white", lw=1.2, zorder=4,
                   label=f"{g} basket")
    mu, cov = b.mean().values * 252, b.cov().values * 252
    for key, marker, size, colour, lab in (("min_variance", "D", 40, viz.INK, "Minimum variance"),
                                            ("tangency", "*", 90, viz.GOLD, "Maximum Sharpe")):
        w = np.array([main[key][g] for g in b.columns])
        ax.scatter(np.sqrt(w @ cov @ w), w @ mu, marker=marker, s=size, color=colour, zorder=5, label=lab)
    ax.axhline(0, color=viz.AXIS, lw=0.8, zorder=1)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_xlabel("Annualised volatility", color=viz.INK2)
    ax.set_ylabel("Annualised return", color=viz.INK2)
    ax.legend(fontsize=6.5, loc="lower right")
    panel_title(ax, "Risk and return: baskets, names and the frontier")
    ax2 = axes[1]
    bp = ax2.boxplot([boot[f"mv_{g}"].values for g in GROUPS], vert=False, patch_artist=True, widths=0.55,
                     medianprops={"color": viz.INK}, flierprops={"markersize": 2, "markeredgecolor": viz.MUTED})
    for patch, g in zip(bp["boxes"], GROUPS):
        patch.set_facecolor(COLOUR[g]); patch.set_alpha(0.85); patch.set_edgecolor("white")
    ax2.set_yticks([1, 2, 3], list(GROUPS))
    ax2.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax2.grid(axis="x"); ax2.grid(axis="y", visible=False); ax2.tick_params(axis="y", length=0)
    panel_title(ax2, "Minimum-variance weight, 2,000 bootstraps")
    texts = header(fig, "One, two or all three? Diversification versus estimation risk",
                   f"Daily returns {main['start']} to {main['end']}; equal-weight baskets; stationary bootstrap, 20-day blocks",
                   "Yahoo Finance prices; FRED 3-month bill; Bona Fide analysis. Seventeen months of returns are a weak guide to the future.")
    save(fig, "qa_q2_frontier", texts, top=0.86)


# ------------------------------------------------------------------------------------------ main
def main() -> None:
    df, series = financial_profile()
    stability = revenue_stability(series)
    life = useful_life_sensitivity(df)
    lags = dlr_capex_revenue_lag(series)
    model, jstats = stylised_models(df)
    fund = fundamental_elasticity(series)
    rets = prices().pct_change(fill_method=None)
    mkt = factor_model(rets)
    port, b, front, boot = portfolio(rets)

    chart_profile(df)
    chart_phase(model)
    chart_elasticity(mkt)
    chart_frontier(port, b, front, boot, rets)

    metrics = ["noncurrent_share", "long_lived_share", "asset_turnover", "capex_to_revenue", "da_to_revenue",
               "interest_to_revenue", "committed_cost_ratio", "operating_margin", "ebitda_margin", "fcf_margin",
               "contract_coverage"]
    summary = dict(
        valuation_date=VALUATION_DATE,
        profile=json.loads(df.drop(columns=["ttm_end"]).to_json(orient="index")),
        ttm_end={t: (None if pd.isna(v) else str(pd.Timestamp(v).date())) for t, v in df["ttm_end"].items()},
        group_medians=json.loads(df.groupby("group")[metrics].median().to_json(orient="index")),
        revenue_stability=json.loads(stability.to_json(orient="index")),
        useful_life=json.loads(life.to_json(orient="records")),
        dlr_lag=dict(peak_lag=int(lags.loc[lags["corr"].idxmax(), "lag_quarters"]), peak_corr=float(lags["corr"].max()),
                     most_negative_lag=int(lags.loc[lags["corr"].idxmin(), "lag_quarters"]), min_corr=float(lags["corr"].min())),
        stylised=jstats, stylised_parameters={k: v for k, v in KEYED.items() if not isinstance(v, dict)},
        fundamental_elasticity=json.loads(fund.to_json(orient="index")),
        market_elasticity=json.loads(mkt.to_json(orient="records")),
        portfolio=port,
    )
    (OUT / "q2_summary.json").write_text(json.dumps(summary, indent=2, default=float))

    pd.set_option("display.width", 250)
    print(df[["ttm_end", "revenue", "operating_income", "d_and_a", "capex", "interest"] + metrics].round(3).to_string())
    print(stability.round(3).to_string())
    print(life.round(3).to_string())
    print("DLR lag:", summary["dlr_lag"], "\nStylised:", json.dumps(jstats))
    print(fund.round(3).to_string())
    print(mkt[mkt["window"] == "common"].pivot(index="ticker", columns="factor", values="beta").round(3).to_string())
    for w in ("main", "robust", "dlr_only"):
        p = port[w]
        print(w, p["start"], p["n_days"], {g: {k: round(v, 3) for k, v in s.items()} for g, s in p["stats"].items()})
        print("  corr", p["corr"], "\n  mv", {k: round(v, 3) for k, v in p["min_variance"].items()},
              "tan", {k: round(v, 3) for k, v in p["tangency"].items()})
        print("  pairs", [(x["low_vol"], x["high_vol"], round(x["rho"], 3), round(x["vol_ratio"], 3), x["corner"]) for x in p["pairs"]])
    for k in ("bootstrap_main", "bootstrap_dlr_only"):
        print(k, json.dumps(port[k]))


if __name__ == "__main__":
    main()
