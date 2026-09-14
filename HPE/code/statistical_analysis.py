"""Statistical analysis for HPE: macro driver regressions, an ARIMA revenue baseline and return diagnostics.

Each model answers an investment question in the report; none of them is the forecast.

A. Macro driver regressions (OLS with Newey-West HAC standard errors, because year-over-year observations overlap)
   R1  HPE revenue growth (YoY, log) on cloud-capex growth (MSFT, GOOGL, AMZN, META, ORCL; YoY, log), lags 0–2,
       with a dummy for quarters that include Juniper (from Q3 FY25). Robustness: pre-Juniper sample only.
   R2  Change in HPE GAAP gross margin (YoY, pp) on the change in Micron gross margin (YoY, pp), lags 0–2, with the
       Juniper dummy. Micron's margin proxies memory contract pricing, a large server input cost.
   Fiscal quarters are aligned to the calendar quarter they mostly cover (HPE Nov–Jan → prior-year Q4, etc.).
B. ARIMA revenue baseline
   SARIMA on log quarterly revenue FY2018 Q1–FY2025 Q2 (post spin-offs, pre-Juniper); order chosen by AICc from a small
   grid (≤4 parameters); one-step rolling backtest over the last 8 quarters vs random-walk and seasonal-naive
   benchmarks; forecast from Q3 FY25 used as a no-structural-change counterfactual for FY26–FY27.
C. Return diagnostics (daily, since regular-way listing)
   ADF unit-root tests, Ljung-Box on returns and squared returns, Engle ARCH-LM, skewness/kurtosis/Jarque-Bera,
   frequency of 3-sigma days vs a normal distribution.

Inputs: data/financial_data (XBRL facts, parsed statements, industry series), data/market_data (prices).
Outputs: data/processed_data/statistics/*.csv, *.txt model summaries, statistics_summary.json; charts.
"""
from __future__ import annotations

import itertools
import json
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import acf, adfuller

import viz
from common import FIN_DATA, LISTING_DATE, MKT_DATA, PROC, VALUATION_DATE
from macro_industry_analysis import discrete_quarters

warnings.filterwarnings("ignore")
OUT = PROC / "statistics"
OUT.mkdir(exist_ok=True)
JUNIPER_FIRST_QUARTER = pd.Timestamp("2025-07-31")      # Q3 FY25: first quarter including Juniper (closed 2-Jul-2025)
FY26_GUIDANCE_MID = 46_500                               # FY26 revenue guidance midpoint, $m (+34–37% on FY25)
FY26_NORMALISED_GROWTH_MID = 0.22                        # company-normalised FY26 growth, midpoint of 21–23%
FY26_REPORTED_GROWTH_MID = 0.355                         # reported FY26 growth guidance, midpoint of 34–37%
FY25_REVENUE = 34_296


# ------------------------------------------------------------------------------------------ data
def fiscal_calendar_quarter(end: pd.Timestamp) -> pd.Period:
    """Calendar quarter with the most overlap for a quarter ending on `end` (three-month period)."""
    return (end - pd.Timedelta(days=45)).to_period("Q")


def hpe_quarterly_revenue() -> pd.Series:
    """Quarterly revenue from XBRL, starting FY2017 Q1.

    FY2016 quarterly facts mix values reported before and after the 2017 DXC / Micro Focus spin-off restatements
    (e.g. $12.7bn then $4.3bn in consecutive quarters), so they are excluded; FY2017 onward is on the restated basis.
    """
    f = json.loads((FIN_DATA / "companyfacts_HPE.json").read_text())["facts"]["us-gaap"]
    q = discrete_quarters(f["Revenues"]["units"]["USD"]) / 1e6
    return q[(q.index >= "2016-11-01") & (q.index <= VALUATION_DATE)].rename("revenue")


def hpe_quarterly_gross_margin() -> pd.DataFrame:
    """GAAP gross margin per fiscal quarter from the parsed 10-Q (3 months) and 10-K (FY less nine months) statements."""
    df = pd.read_csv(FIN_DATA / "hpe_statements_long.csv")
    is_ = df[df.statement == "IS"]
    rev_pat = r"^(Total net revenue|Net revenue)$"
    cost_pat = r"^(Cost of (products|services|sales)|Financing (cost|interest))"

    def rev_cost(rows: pd.DataFrame) -> tuple[float, float]:
        rev = rows[rows.label.str.match(rev_pat)].value
        cost = rows[rows.label.str.match(cost_pat)].groupby("label").value.first().sum()
        return (float(rev.iloc[0]) if len(rev) else np.nan), float(cost)

    out = {}
    for filing in is_[is_.form == "10-Q"].filing.unique():
        end = pd.Timestamp(filing[-10:])
        rows = is_[(is_.filing == filing) & (is_.period == f"3M_{end.year}")]
        if rows.empty:
            continue
        rev, cost = rev_cost(rows)
        out[end] = dict(revenue=rev, cost=cost, basis="10-Q three months")
        if filing.split("_")[2].endswith("Q3"):
            nine = is_[(is_.filing == filing) & (is_.period == f"9M_{end.year}")]
            r9, c9 = rev_cost(nine)
            fy = int(filing.split("_")[2][2:6])
            annual = is_[(is_.form == "10-K") & (is_.period == f"FY{fy}")]
            for k in sorted(annual.filing.unique(), reverse=True):   # latest 10-K presenting the year
                ra, ca = rev_cost(annual[annual.filing == k])
                if not np.isnan(ra) and ca > 0:
                    out[pd.Timestamp(f"{fy}-10-31")] = dict(revenue=ra - r9, cost=ca - c9, basis=f"{k} less 9M")
                    break
    gm = pd.DataFrame(out).T.sort_index()
    gm["gross_margin"] = 1 - gm["cost"].astype(float) / gm["revenue"].astype(float)
    return gm[gm.index >= "2017-11-01"]   # FY2018 onward: after the 2017 spin-offs


def capex_growth() -> pd.Series:
    cap = pd.read_csv(FIN_DATA / "industry" / "hyperscaler_capex_quarterly.csv", index_col=0)
    cap.index = pd.PeriodIndex(cap.index, freq="Q")
    return np.log(cap["total"]).diff(4).rename("capex_yoy")


def micron_margin() -> pd.Series:
    mu = pd.read_csv(FIN_DATA / "industry" / "micron_quarterly.csv", parse_dates=["end"]).set_index("end")["gross_margin"]
    mu.index = [fiscal_calendar_quarter(d) for d in mu.index]
    return mu[~mu.index.duplicated(keep="last")]


# ------------------------------------------------------------------------------------------ A. regressions
def hac_ols(y: pd.Series, X: pd.DataFrame, name: str) -> tuple[dict, pd.DataFrame]:
    data = pd.concat([y, X], axis=1).dropna()
    model = sm.OLS(data.iloc[:, 0], sm.add_constant(data.iloc[:, 1:])).fit(cov_type="HAC", cov_kwds={"maxlags": 4})
    (OUT / f"{name}_summary.txt").write_text(model.summary().as_text())
    ci = model.conf_int()
    table = pd.DataFrame({"coef": model.params, "std_err_hac": model.bse, "t": model.tvalues, "p_value": model.pvalues,
                          "ci_low": ci[0], "ci_high": ci[1]})
    table.to_csv(OUT / f"{name}_coefficients.csv")
    stats_ = dict(n=int(model.nobs), r2=float(model.rsquared), adj_r2=float(model.rsquared_adj),
                  durbin_watson=float(sm.stats.durbin_watson(model.resid)), sample=f"{data.index[0]} to {data.index[-1]}")
    return stats_, table


def regressions() -> dict:
    rev = hpe_quarterly_revenue()
    growth = np.log(rev).diff(4)
    growth.index = [fiscal_calendar_quarter(d) for d in growth.index]
    growth = growth[~growth.index.duplicated(keep="last")].rename("hpe_revenue_yoy")
    cg = capex_growth()
    juniper = pd.Series([1.0 if p >= fiscal_calendar_quarter(JUNIPER_FIRST_QUARTER) else 0.0 for p in growth.index],
                        index=growth.index, name="juniper_dummy")
    X1 = pd.concat({"capex_yoy_lag0": cg, "capex_yoy_lag1": cg.shift(1), "capex_yoy_lag2": cg.shift(2)}, axis=1)
    X1 = X1.reindex(growth.index).join(juniper)
    r1_stats, r1 = hac_ols(growth, X1, "R1_revenue_on_capex")
    pre = juniper == 0
    r1b_stats, r1b = hac_ols(growth[pre], X1.loc[pre, ["capex_yoy_lag0", "capex_yoy_lag1", "capex_yoy_lag2"]], "R1b_revenue_on_capex_pre_juniper")

    gm = hpe_quarterly_gross_margin()
    gm_s = gm["gross_margin"].astype(float)
    gm_s.index = [fiscal_calendar_quarter(d) for d in gm_s.index]
    gm_s = gm_s[~gm_s.index.duplicated(keep="last")]
    d_gm = (gm_s - gm_s.shift(4)).rename("hpe_gm_yoy_change_pp") * 100
    mu = micron_margin()
    d_mu = (mu - mu.shift(4)) * 100
    X2 = pd.concat({"micron_gm_change_lag0": d_mu, "micron_gm_change_lag1": d_mu.shift(1), "micron_gm_change_lag2": d_mu.shift(2)}, axis=1)
    j2 = pd.Series([1.0 if p >= fiscal_calendar_quarter(JUNIPER_FIRST_QUARTER) else 0.0 for p in d_gm.index], index=d_gm.index, name="juniper_dummy")
    X2 = X2.reindex(d_gm.index).join(j2)
    r2_stats, r2 = hac_ols(d_gm, X2, "R2_gross_margin_on_memory")

    pd.DataFrame({"hpe_revenue_yoy": growth, "capex_yoy": cg.reindex(growth.index), "juniper": juniper}).to_csv(OUT / "R1_data.csv")
    pd.DataFrame({"hpe_gross_margin": gm_s, "hpe_gm_yoy_change_pp": d_gm, "micron_gm_change_pp": d_mu.reindex(d_gm.index)}).to_csv(OUT / "R2_data.csv")
    gm.to_csv(OUT / "hpe_quarterly_gross_margin.csv")

    # charts: scatter with fitted bivariate line (the multivariate results are in the tables)
    d1 = pd.concat([growth, cg.reindex(growth.index), juniper], axis=1).dropna()
    fig, ax = viz.figure(8, 3.4)
    for flag, col, lab in ((0, viz.GREEN, "Pre-Juniper quarters"), (1, viz.GOLD, "Quarters including Juniper")):
        s = d1[d1["juniper_dummy"] == flag]
        ax.scatter(s["capex_yoy"], s["hpe_revenue_yoy"], s=48, color=col, edgecolor=viz.SURFACE, linewidth=1.5, zorder=3, label=lab)
    pre1 = d1[d1["juniper_dummy"] == 0]
    b = np.polyfit(pre1["capex_yoy"], pre1["hpe_revenue_yoy"], 1)
    xs = np.linspace(d1["capex_yoy"].min(), d1["capex_yoy"].max(), 50)
    ax.plot(xs, np.polyval(b, xs), color=viz.INK2, lw=1.2, zorder=2, label="Fit, pre-Juniper quarters")
    ax.axhline(0, color=viz.AXIS, lw=0.8, zorder=1)
    ax.xaxis.set_major_formatter(viz.mtick.PercentFormatter(1.0))
    viz.pct_axis(ax)
    ax.grid(axis="x", color=viz.GRID, lw=0.6)
    ax.set_xlabel("Cloud capex growth, YoY (log)")
    ax.set_ylabel("HPE revenue growth, YoY (log)")
    ax.legend(loc="upper left")
    lag0 = r1.loc["capex_yoy_lag0"]
    sig = r1.drop(["const", "juniper_dummy"])
    r1_title = ("HPE revenue growth moves with cloud capex growth" if ((sig.coef > 0) & (sig.p_value < 0.05)).any()
                else "Cloud capex growth explains little of HPE's revenue growth; Juniper and pricing do")
    viz.titles(ax, r1_title,
               f"Quarterly YoY growth FY2018–Q3 FY26; R1 capex coefficients sum {sig.coef.sum():.2f} (lags 0–2, best HAC p={sig.p_value.min():.2f}), n={r1_stats['n']}")
    viz.source(fig, "SEC XBRL (HPE, MSFT, GOOGL, AMZN, META, ORCL); Bona Fide regression (statsmodels, Newey-West errors).")
    viz.save(fig, "stat_capex_revenue")

    best = r2.drop(["const", "juniper_dummy"]).t.abs().idxmax()
    lag = int(best[-1])
    d2 = pd.concat([d_gm, d_mu.shift(lag).reindex(d_gm.index).rename("mu"), j2], axis=1).dropna()
    fig, ax = viz.figure(8, 3.4)
    for flag, col, lab in ((0, viz.GREEN, "Pre-Juniper quarters"), (1, viz.GOLD, "Quarters including Juniper")):
        s = d2[d2["juniper_dummy"] == flag]
        ax.scatter(s["mu"], s["hpe_gm_yoy_change_pp"], s=48, color=col, edgecolor=viz.SURFACE, linewidth=1.5, zorder=3, label=lab)
    b2 = np.polyfit(d2["mu"], d2["hpe_gm_yoy_change_pp"], 1)
    xs = np.linspace(d2["mu"].min(), d2["mu"].max(), 50)
    ax.plot(xs, np.polyval(b2, xs), color=viz.INK2, lw=1.2, zorder=2, label="Fit, all quarters")
    ax.axhline(0, color=viz.AXIS, lw=0.8, zorder=1)
    ax.axvline(0, color=viz.AXIS, lw=0.8, zorder=1)
    ax.grid(axis="x", color=viz.GRID, lw=0.6)
    ax.set_xlabel(f"Change in Micron gross margin, YoY (pp), lag {lag}")
    ax.set_ylabel("Change in HPE gross margin, YoY (pp)")
    ax.legend(loc="upper left")
    row = r2.loc[best]
    r2_title = ("Memory-price spikes dent HPE's gross margin only modestly; the Juniper mix shift dominates"
                if row["coef"] < 0 and row["p_value"] < 0.05 else "Memory price swings show no reliable link to HPE's gross margin")
    viz.titles(ax, r2_title,
               f"R2 coefficient on Micron margin change (lag {lag}) {row['coef']:.2f} (HAC p={row['p_value']:.2f}), n={r2_stats['n']}")
    viz.source(fig, "HPE 10-Q/10-K statements; Micron XBRL; Bona Fide regression (statsmodels, Newey-West errors).")
    viz.save(fig, "stat_memory_margin")

    return dict(R1=dict(stats=r1_stats, coefficients=r1.round(4).to_dict("index")),
                R1_pre_juniper=dict(stats=r1b_stats, coefficients=r1b.round(4).to_dict("index")),
                R2=dict(stats=r2_stats, coefficients=r2.round(4).to_dict("index"), chart_lag=lag))


# ------------------------------------------------------------------------------------------ B. ARIMA baseline
def aicc(res, n: int) -> float:
    k = len(res.params)
    return res.aic + 2 * k * (k + 1) / max(n - k - 1, 1)


def fit_sarima(y: pd.Series, order, seasonal):
    trend = "c" if order[1] + seasonal[1] == 0 else "n"
    return SARIMAX(y, order=order, seasonal_order=(*seasonal, 4), trend=trend).fit(disp=False)


def arima_baseline() -> dict:
    rev = hpe_quarterly_revenue()
    y_all = np.log(rev[rev.index >= "2017-11-01"])
    y_all.index = pd.PeriodIndex([fiscal_calendar_quarter(d) for d in y_all.index], freq="Q")
    pre = y_all[y_all.index <= fiscal_calendar_quarter(pd.Timestamp("2025-04-30"))]
    n = len(pre)

    grid = []
    for p, d, q in itertools.product((0, 1, 2), (0, 1), (0, 1)):
        for seasonal in ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 1, 1)):
            k = p + q + seasonal[0] + seasonal[2] + (1 if d + seasonal[1] == 0 else 0)
            if k > 4:
                continue
            try:
                res = fit_sarima(pre, (p, d, q), seasonal)
                grid.append(dict(order=(p, d, q), seasonal=seasonal, aicc=aicc(res, n), aic=res.aic, converged=res.mle_retvals.get("converged", True)))
            except Exception:
                continue
    sel = pd.DataFrame(grid).query("converged").sort_values("aicc")
    sel.to_csv(OUT / "arima_model_selection.csv", index=False)
    order, seasonal = tuple(sel.iloc[0]["order"]), tuple(sel.iloc[0]["seasonal"])

    # rolling one-step backtest over the last 8 pre-break quarters
    bt = []
    for i in range(n - 8, n):
        train = pre.iloc[:i]
        fc = fit_sarima(train, order, seasonal).get_forecast(1).predicted_mean.iloc[0]
        actual = pre.iloc[i]
        bt.append(dict(quarter=str(pre.index[i]), actual=np.exp(actual), arima=np.exp(fc), random_walk=np.exp(pre.iloc[i - 1]),
                       seasonal_naive=np.exp(pre.iloc[i - 4])))
    bt = pd.DataFrame(bt)
    mape = {m: float((bt[m] / bt["actual"] - 1).abs().mean()) for m in ("arima", "random_walk", "seasonal_naive")}
    bt.to_csv(OUT / "arima_backtest.csv", index=False)

    res = fit_sarima(pre, order, seasonal)
    (OUT / "arima_summary.txt").write_text(res.summary().as_text())
    steps = 10
    fc = res.get_forecast(steps)
    idx = pd.period_range(pre.index[-1] + 1, periods=steps, freq="Q")
    ci80, ci95 = fc.conf_int(alpha=0.20), fc.conf_int(alpha=0.05)
    cf = pd.DataFrame({"forecast": np.exp(fc.predicted_mean.values), "lo80": np.exp(ci80.iloc[:, 0].values), "hi80": np.exp(ci80.iloc[:, 1].values),
                       "lo95": np.exp(ci95.iloc[:, 0].values), "hi95": np.exp(ci95.iloc[:, 1].values)}, index=idx)
    actual_post = np.exp(y_all[y_all.index > pre.index[-1]])
    cf["actual"] = actual_post.reindex(idx)
    cf["actual_vs_forecast"] = cf["actual"] / cf["forecast"] - 1
    cf["outside_95"] = (cf["actual"] > cf["hi95"]) | (cf["actual"] < cf["lo95"])
    labels = ["Q3 FY25", "Q4 FY25", "Q1 FY26", "Q2 FY26", "Q3 FY26", "Q4 FY26", "Q1 FY27", "Q2 FY27", "Q3 FY27", "Q4 FY27"]
    cf.insert(0, "fiscal_quarter", labels)
    cf.to_csv(OUT / "arima_counterfactual.csv")

    fy26_cf = float(cf["forecast"].iloc[2:6].sum())
    fy27_cf = float(cf["forecast"].iloc[6:10].sum())
    ttm_actual = float(cf["actual"].iloc[1:5].sum())
    ttm_cf = float(cf["forecast"].iloc[1:5].sum())
    # Company "normalised" growth adds Juniper's 8 pre-close months to the FY25 base:
    #   FY25 × (1 + reported) = (FY25 + J8) × (1 + normalised)  →  J8; a full Juniper year ≈ J8 × 12/8 (analyst estimate)
    juniper_pre_close_8m = FY25_REVENUE * (1 + FY26_REPORTED_GROWTH_MID) / (1 + FY26_NORMALISED_GROWTH_MID) - FY25_REVENUE
    juniper_fy26 = juniper_pre_close_8m * 12 / 8
    excess_fy26 = FY26_GUIDANCE_MID - fy26_cf
    decomposition = dict(fy26_arima_counterfactual=fy26_cf, fy26_guidance_mid=FY26_GUIDANCE_MID, fy26_excess_over_trend=excess_fy26,
                         juniper_pre_close_8m_estimate=juniper_pre_close_8m,
                         fy26_juniper_estimate=juniper_fy26, fy26_residual_ai_pricing_estimate=excess_fy26 - juniper_fy26,
                         fy27_arima_counterfactual=fy27_cf, fy27_base_case=53_475.0,
                         ttm_q3fy26_actual=ttm_actual, ttm_q3fy26_counterfactual=ttm_cf, ttm_excess_pct=ttm_actual / ttm_cf - 1)

    # chart
    hist = np.exp(y_all)
    fig, ax = viz.figure(8, 3.6)
    t_hist = hist.index.to_timestamp(how="end")
    t_fc = cf.index.to_timestamp(how="end")
    ax.fill_between(t_fc, cf["lo95"] / 1000, cf["hi95"] / 1000, color=viz.GOLD, alpha=0.10, lw=0, label="95% interval")
    ax.fill_between(t_fc, cf["lo80"] / 1000, cf["hi80"] / 1000, color=viz.GOLD, alpha=0.18, lw=0, label="80% interval")
    model_label = "SARIMA(" + ",".join(map(str, order)) + ")(" + ",".join(map(str, seasonal)) + ")[4] counterfactual"
    ax.plot(t_fc, cf["forecast"] / 1000, color=viz.GOLD, lw=1.8, label=model_label)
    ax.plot(t_hist, hist / 1000, color=viz.GREEN, lw=2, marker="o", ms=3.5, label="Actual quarterly revenue")
    ax.axvline(pd.Timestamp("2025-07-02"), color=viz.AXIS, lw=0.8, zorder=1)
    ax.text(pd.Timestamp("2025-07-02"), ax.get_ylim()[1] * 0.97, " Juniper closes", fontsize=7.5, color=viz.INK2, va="top")
    ax.set_ylabel("$bn per quarter")
    ax.legend(loc="upper left", fontsize=7.5)
    viz.titles(ax, f"Actual revenue broke far above the pre-Juniper trend: TTM {decomposition['ttm_excess_pct']:+.0%} vs ARIMA baseline",
               "Quarterly revenue FY2018–Q3 FY26 and a SARIMA counterfactual fitted to FY2018–Q2 FY25 only")
    viz.source(fig, "HPE XBRL revenue; Bona Fide SARIMA (statsmodels). Counterfactual, not a forecast.")
    viz.save(fig, "stat_arima_counterfactual")

    return dict(order=list(order), seasonal=list(seasonal), n_fit=n, fit_sample=f"{pre.index[0]}–{pre.index[-1]} (calendar-aligned)",
                aicc=float(sel.iloc[0]["aicc"]), backtest_mape=mape, quarters_outside_95=int(cf["outside_95"].sum()),
                quarters_with_actuals=int(cf["actual"].notna().sum()), decomposition=decomposition,
                ljung_box_resid_p_lag8=float(acorr_ljungbox(res.resid.iloc[max(order[1], 1):], lags=[8]).lb_pvalue.iloc[0]))


# ------------------------------------------------------------------------------------------ C. return diagnostics
def return_diagnostics() -> dict:
    px = pd.read_csv(MKT_DATA / "HPE_daily.csv", parse_dates=["date"]).set_index("date")
    px = px[(px.index >= LISTING_DATE) & (px.index <= VALUATION_DATE)]
    logp = np.log(px["adj_close"])
    r = logp.diff().dropna()
    adf_p = adfuller(logp, autolag="AIC")
    adf_r = adfuller(r, autolag="AIC")
    lb_r = acorr_ljungbox(r, lags=[5, 10, 20])
    lb_r2 = acorr_ljungbox(r ** 2, lags=[5, 10, 20])
    arch_lm, arch_p, _, _ = het_arch(r, nlags=5)
    jb = stats.jarque_bera(r)
    sigma = r.std()
    tail_share = float((r.abs() > 3 * sigma).mean())
    normal_share = float(2 * (1 - stats.norm.cdf(3)))
    table = pd.DataFrame([
        ("ADF, log price", adf_p[0], adf_p[1], "Unit root not rejected → prices are non-stationary" if adf_p[1] > 0.05 else "Stationary"),
        ("ADF, daily log returns", adf_r[0], adf_r[1], "Stationary" if adf_r[1] < 0.05 else "Unit root not rejected"),
        ("Ljung-Box returns, lag 10", lb_r.lb_stat.loc[10], lb_r.lb_pvalue.loc[10], "Autocorrelation in returns" if lb_r.lb_pvalue.loc[10] < 0.05 else "No significant autocorrelation"),
        ("Ljung-Box returns, lag 20", lb_r.lb_stat.loc[20], lb_r.lb_pvalue.loc[20], ""),
        ("Ljung-Box squared returns, lag 10", lb_r2.lb_stat.loc[10], lb_r2.lb_pvalue.loc[10], "Volatility clustering" if lb_r2.lb_pvalue.loc[10] < 0.05 else "No clustering"),
        ("Engle ARCH-LM, 5 lags", arch_lm, arch_p, "ARCH effects" if arch_p < 0.05 else "No ARCH effects"),
        ("Jarque-Bera normality", jb.statistic, jb.pvalue, "Non-normal (fat tails)" if jb.pvalue < 0.05 else "Normal"),
    ], columns=["test", "statistic", "p_value", "reading"])
    table.to_csv(OUT / "return_diagnostics.csv", index=False)

    lags = 20
    a_r, a_r2 = acf(r, nlags=lags, fft=True)[1:], acf(r ** 2, nlags=lags, fft=True)[1:]
    band = 1.96 / np.sqrt(len(r))
    fig, (a1, a2) = viz.figure(8, 3.8, nrows=2, sharex=True)
    for ax, vals, lab in ((a1, a_r, "Returns"), (a2, a_r2, "Squared returns")):
        ax.axhspan(-band, band, color=viz.CONTEXT, alpha=0.25, lw=0, zorder=0)
        ax.bar(np.arange(1, lags + 1), vals, width=0.5, color=viz.GREEN, zorder=3)
        ax.axhline(0, color=viz.AXIS, lw=0.8, zorder=1)
        ax.set_ylabel(f"ACF: {lab}", fontsize=8)
    a2.set_xlabel("Lag (trading days)")
    a2.set_xticks(range(1, lags + 1, 2))
    viz.titles(a1, "Returns are close to unpredictable; volatility is not",
               "Autocorrelation of daily log returns and squared returns since listing; grey band = 95% no-autocorrelation range")
    viz.source(fig, "Yahoo Finance adjusted prices; Bona Fide analysis (statsmodels).")
    viz.save(fig, "stat_return_acf")

    return dict(n_days=int(len(r)), daily_sigma=float(sigma), skew=float(stats.skew(r)), excess_kurtosis=float(stats.kurtosis(r)),
                share_3sigma_days=tail_share, normal_expected_3sigma=normal_share, tail_ratio=tail_share / normal_share,
                adf_price_p=float(adf_p[1]), adf_returns_p=float(adf_r[1]), ljung_box_returns_p_lag10=float(lb_r.lb_pvalue.loc[10]),
                ljung_box_sq_returns_p_lag10=float(lb_r2.lb_pvalue.loc[10]), arch_lm_p=float(arch_p), jarque_bera_p=float(jb.pvalue),
                acf_lag1_returns=float(a_r[0]), acf_lag1_squared=float(a_r2[0]))


def main() -> None:
    summary = dict(regressions=regressions(), arima=arima_baseline(), returns=return_diagnostics())
    (OUT / "statistics_summary.json").write_text(json.dumps(summary, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    print(json.dumps(summary, indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
