"""Stock price, volume and technical analysis for HPE — descriptive, not a trading strategy.

Explains how the stock has behaved from regular-way listing (2015-11-02) to the valuation date:
returns by window vs benchmarks and peers, trend/momentum indicators (SMA, EMA, RSI, Bollinger,
MACD, OBV via the `ta` library), volatility, drawdowns, gaps, statistically large moves,
volume participation, correlations and simple beta.

Price basis: Yahoo close (adjusted for the 2017 DXC and Micro Focus spin-offs) for technicals;
dividend-adjusted close for returns.

Outputs: data/processed_data/stock/*.csv, stock_summary.json; charts in data/processed_data/charts/
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import ta

import viz
from common import BENCHMARKS, LISTING_DATE, MKT_DATA, PEER_NAMES, PEERS, PROC, VALUATION_DATE

OUT = PROC / "stock"
OUT.mkdir(exist_ok=True)
END = pd.Timestamp(VALUATION_DATE)
TICKERS = ["HPE", *BENCHMARKS, *PEERS]
KEY_EVENTS = {  # for chart annotation only; returns around events are in event_analysis.py
    "2024-01-09": "Juniper deal announced",
    "2025-03-07": "FY25 guide cut",
    "2025-07-02": "Juniper closes",
    "2026-09-03": "Q3 FY26 beat",
}


def load(tk: str) -> pd.DataFrame:
    df = pd.read_csv(MKT_DATA / f"{tk}_daily.csv", parse_dates=["date"]).set_index("date")
    return df[df.index <= END]


def technicals(df: pd.DataFrame) -> pd.DataFrame:
    t = df.copy()
    c = t["close"]
    t["ret"] = t["adj_close"].pct_change()
    for n in (20, 50, 200):
        t[f"sma{n}"] = ta.trend.sma_indicator(c, n)
    for n in (12, 26, 50):
        t[f"ema{n}"] = ta.trend.ema_indicator(c, n)
    t["rsi14"] = ta.momentum.rsi(c, 14)
    bb = ta.volatility.BollingerBands(c, 20, 2)
    t["bb_high"], t["bb_low"], t["bb_mid"] = bb.bollinger_hband(), bb.bollinger_lband(), bb.bollinger_mavg()
    t["bb_width"], t["bb_pctb"] = bb.bollinger_wband(), bb.bollinger_pband()
    t["macd"], t["macd_signal"] = ta.trend.macd(c), ta.trend.macd_signal(c)
    t["obv"] = ta.volume.on_balance_volume(c, t["volume"])
    t["vol21"] = t["ret"].rolling(21).std() * np.sqrt(252)
    t["vol63"] = t["ret"].rolling(63).std() * np.sqrt(252)
    t["volume_avg50"] = t["volume"].rolling(50).mean()
    t["volume_ratio"] = t["volume"] / t["volume_avg50"].shift(1)
    t["gap"] = t["open"] / t["close"].shift(1) - 1
    t["sigma252"] = t["ret"].rolling(252, min_periods=60).std().shift(1)
    t["zscore"] = t["ret"] / t["sigma252"]
    t["drawdown"] = t["adj_close"] / t["adj_close"].cummax() - 1
    t["high52"] = c.rolling(252, min_periods=20).max()
    t["low52"] = c.rolling(252, min_periods=20).min()
    return t


def base_value(s: pd.Series, start: pd.Timestamp) -> float:
    prior = s[s.index <= start].dropna()
    return prior.iloc[-1] if not prior.empty else np.nan


def window_returns(px: pd.DataFrame) -> pd.DataFrame:
    starts = {
        "1M": END - pd.DateOffset(months=1), "3M": END - pd.DateOffset(months=3),
        "6M": END - pd.DateOffset(months=6), "YTD": pd.Timestamp("2025-12-31"),
        "1Y": END - pd.DateOffset(years=1), "3Y": END - pd.DateOffset(years=3),
        "5Y": END - pd.DateOffset(years=5), "Since listing": pd.Timestamp(LISTING_DATE),
    }
    rows = {}
    for tk in px.columns:
        s = px[tk].dropna()
        row = {}
        for name, st in starts.items():
            if s.index[0] > st + pd.Timedelta(days=5):
                row[name] = np.nan  # not trading for the full window
            else:
                row[name] = s.iloc[-1] / base_value(s, st) - 1
        rows[tk] = row
    return pd.DataFrame(rows).T


def risk_stats(px: pd.DataFrame, years: int | None) -> pd.DataFrame:
    out = {}
    for tk in px.columns:
        s = px[tk].dropna()
        if years:
            s = s[s.index > END - pd.DateOffset(years=years)]
        r = s.pct_change().dropna()
        n_years = (s.index[-1] - s.index[0]).days / 365.25
        out[tk] = {"cagr": (s.iloc[-1] / s.iloc[0]) ** (1 / n_years) - 1,
                   "ann_vol": r.std() * np.sqrt(252),
                   "max_drawdown": (s / s.cummax() - 1).min()}
    return pd.DataFrame(out).T


def beta(y: pd.Series, x: pd.Series) -> float:
    d = pd.concat([y, x], axis=1).dropna()
    return float(np.polyfit(d.iloc[:, 1], d.iloc[:, 0], 1)[0])


def drawdown_episodes(price: pd.Series, threshold: float = -0.20) -> pd.DataFrame:
    dd = price / price.cummax() - 1
    episodes, in_ep, peak_date = [], False, price.index[0]
    for date, v in dd.items():
        if v == 0:
            if in_ep:
                seg = dd[peak_date:date]
                episodes.append((peak_date, seg.idxmin(), date, seg.min()))
                in_ep = False
            peak_date = date
        elif v <= threshold:
            in_ep = True
    if in_ep:
        seg = dd[peak_date:]
        episodes.append((peak_date, seg.idxmin(), pd.NaT, seg.min()))
    ep = pd.DataFrame(episodes, columns=["peak", "trough", "recovered", "depth"])
    ep["days_to_trough"] = (ep["trough"] - ep["peak"]).dt.days
    ep["days_to_recover"] = (ep["recovered"] - ep["trough"]).dt.days
    return ep.sort_values("depth")


def swing_points(t: pd.DataFrame, years: int = 3, half_window: int = 4) -> pd.DataFrame:
    w = t[t.index > END - pd.DateOffset(years=years)].resample("W-FRI").agg(
        {"high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    win = 2 * half_window + 1
    hi = w["high"] == w["high"].rolling(win, center=True, min_periods=half_window + 1).max()
    lo = w["low"] == w["low"].rolling(win, center=True, min_periods=half_window + 1).min()
    rows = [(d, "swing high", w.at[d, "high"]) for d in w.index[hi]] + \
           [(d, "swing low", w.at[d, "low"]) for d in w.index[lo]]
    return pd.DataFrame(rows, columns=["week", "type", "price"]).sort_values("week")


def add_events(ax, ymax) -> None:
    for d, label in KEY_EVENTS.items():
        d = pd.Timestamp(d)
        if ax.get_xlim()[0] <= ax.convert_xunits(d) <= ax.get_xlim()[1]:
            ax.axvline(d, color=viz.AXIS, lw=0.8, zorder=0)
            ax.text(d, ymax, f" {label}", fontsize=7, color=viz.INK2, rotation=90, va="top", ha="right")


def charts(t: pd.DataFrame, px: pd.DataFrame) -> None:
    # 1. Long-term weekly trend
    wk = t["close"].resample("W-FRI").last()
    fig, ax = viz.figure(8, 3.6)
    ax.plot(wk.index, wk, color=viz.GREEN, label="HPE weekly close")
    ax.plot(wk.index, wk.rolling(40).mean(), color=viz.GOLD, lw=1.6, label="40-week moving average")
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(viz.mtick.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.set_yticks([5, 10, 20, 40, 60])
    ax.set_xlim(wk.index[0], wk.index[-1] + pd.Timedelta(days=20))
    add_events(ax, wk.max() * 1.05)
    viz.titles(ax, "HPE since listing: a decade-long range, broken decisively in 2026",
               "Weekly close (log scale), spin-off adjusted, with 40-week moving average")
    ax.legend(loc="upper left", bbox_to_anchor=(0, 0.93))
    viz.source(fig, "Yahoo Finance; Bona Fide analysis. Prices to 11-Sep-2026.")
    viz.save(fig, "stock_long_term_weekly")

    # 2. Two-year daily technical panel (price / volume / RSI stacked; one y-scale per panel)
    d = t[t.index > END - pd.DateOffset(years=2)]
    fig, (a1, a2, a3) = viz.figure(8, 5.6, nrows=3, height_ratios=[3, 1, 1])
    a1.fill_between(d.index, d["bb_low"], d["bb_high"], color=viz.GREEN, alpha=0.10, lw=0, label="Bollinger band (20d, 2σ)")
    a1.plot(d.index, d["close"], color=viz.GREEN, lw=1.6, label="Close")
    a1.plot(d.index, d["sma50"], color=viz.GOLD, lw=1.4, label="50-day SMA")
    a1.plot(d.index, d["sma200"], color=viz.BLUE, lw=1.4, label="200-day SMA")
    a1.yaxis.set_major_formatter(viz.mtick.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    a1.legend(loc="upper left", ncol=4)
    viz.titles(a1, "Trend, volume and momentum over the last two years",
               "Daily close with moving averages and Bollinger band; volume vs 50-day average; RSI(14)")
    big = d["volume_ratio"] >= 2
    a2.bar(d.index[~big], d["volume"][~big] / 1e6, color=viz.CONTEXT, width=1.0)
    a2.bar(d.index[big], d["volume"][big] / 1e6, color=viz.GREEN, width=1.0, label="≥2× 50-day avg volume")
    a2.plot(d.index, d["volume_avg50"] / 1e6, color=viz.INK2, lw=1, zorder=4, label="50-day average")
    a2.set_ylabel("Vol (m)")
    a2.legend(loc="upper left")
    a3.plot(d.index, d["rsi14"], color=viz.GREEN, lw=1.4)
    for lvl in (30, 70):
        a3.axhline(lvl, color=viz.AXIS, lw=0.8, zorder=1)
    a3.set_ylim(0, 100)
    a3.set_yticks([30, 50, 70])
    a3.set_ylabel("RSI(14)")
    viz.source(fig, "Yahoo Finance; `ta` library indicators; Bona Fide analysis.")
    viz.save(fig, "stock_2y_technicals")

    # 3. Six-month daily zoom (short-term action)
    s6 = t[t.index > END - pd.DateOffset(months=6)]
    fig, ax = viz.figure(8, 3.2)
    ax.plot(s6.index, s6["close"], color=viz.GREEN, lw=1.8, label="Close")
    ax.plot(s6.index, s6["ema12"], color=viz.GOLD, lw=1.3, label="12-day EMA")
    ax.plot(s6.index, s6["ema26"], color=viz.BLUE, lw=1.3, label="26-day EMA")
    ax.yaxis.set_major_formatter(viz.mtick.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    add_events(ax, s6["close"].max() * 1.02)
    ax.legend(loc="upper left")
    viz.titles(ax, "Short-term: momentum accelerated after the Q3 FY26 print", "Daily close, last six months, with 12/26-day EMAs")
    viz.source(fig, "Yahoo Finance; Bona Fide analysis.")
    viz.save(fig, "stock_6m_daily")

    # 4. Drawdown from prior peak (total return basis)
    fig, ax = viz.figure(8, 2.8)
    ax.fill_between(t.index, t["drawdown"], 0, color=viz.GREEN, alpha=0.12, lw=0)
    ax.plot(t.index, t["drawdown"], color=viz.GREEN, lw=1.2)
    viz.pct_axis(ax)
    viz.titles(ax, "Drawdowns of 40–50% have been recurrent", "Total-return drawdown from prior peak since listing")
    viz.source(fig, "Yahoo Finance (dividend-adjusted); Bona Fide analysis.")
    viz.save(fig, "stock_drawdown")

    # 5. Relative performance vs benchmarks (3 years, indexed)
    r3 = px[px.index > END - pd.DateOffset(years=3)]
    idx = r3 / r3.iloc[0] * 100
    fig, ax = viz.figure(8, 3.4)
    for tk in ["SPY", "XLK", "HPE"]:
        ax.plot(idx.index, idx[tk], color=viz.ENTITY[tk], lw=2 if tk == "HPE" else 1.6, label=PEER_NAMES[tk])
        viz.end_label(ax, idx.index[-1], idx[tk].iloc[-1], f"{PEER_NAMES[tk].split(' (')[0]} {idx[tk].iloc[-1]:.0f}")
    ax.axhline(100, color=viz.AXIS, lw=0.8, zorder=1)
    ax.legend(loc="upper left")
    viz.titles(ax, "HPE lagged the market for two years, then caught up in 2026",
               "Total return indexed to 100, three years to 11-Sep-2026")
    viz.source(fig, "Yahoo Finance (dividend-adjusted); Bona Fide analysis.")
    viz.save(fig, "stock_relative_benchmarks_3y")

    # 6. HPE vs peers (emphasis: HPE green, peers context grey with direct labels)
    fig, ax = viz.figure(8, 3.8)
    for tk in PEERS:
        ax.plot(idx.index, idx[tk], color=viz.CONTEXT, lw=1.2)
        viz.end_label(ax, idx.index[-1], idx[tk].iloc[-1], f"{PEER_NAMES[tk].split(' (')[0]} {idx[tk].iloc[-1]:.0f}")
    ax.plot(idx.index, idx["HPE"], color=viz.GREEN, lw=2.2)
    viz.end_label(ax, idx.index[-1], idx["HPE"].iloc[-1], f"HPE {idx['HPE'].iloc[-1]:.0f}")
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(viz.mtick.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.axhline(100, color=viz.AXIS, lw=0.8, zorder=1)
    viz.titles(ax, "Against hardware and networking peers, HPE sits mid-pack",
               "Total return indexed to 100 (log scale), three years; HPE highlighted")
    viz.source(fig, "Yahoo Finance (dividend-adjusted); Bona Fide analysis.")
    viz.save(fig, "stock_vs_peers_3y")

    # 7. Rolling 126-day correlation of daily returns
    rets = px.pct_change()
    fig, ax = viz.figure(8, 3.0)
    for tk in ["SPY", "DELL", "CSCO"]:
        rc = rets["HPE"].rolling(126).corr(rets[tk])
        rc = rc[rc.index > END - pd.DateOffset(years=5)]
        ax.plot(rc.index, rc, color=viz.ENTITY[tk], lw=1.5, label=PEER_NAMES[tk])
    ax.set_ylim(-0.1, 1)
    ax.legend(loc="lower left", ncol=3)
    viz.titles(ax, "HPE trades increasingly with AI-hardware names", "Rolling 126-day correlation of daily returns, five years")
    viz.source(fig, "Yahoo Finance; Bona Fide analysis.")
    viz.save(fig, "stock_rolling_correlation")

    # 8. Rolling volatility
    v = t[t.index > END - pd.DateOffset(years=5)]
    fig, ax = viz.figure(8, 2.8)
    ax.plot(v.index, v["vol63"], color=viz.GREEN, lw=1.5)
    med = v["vol63"].median()
    ax.axhline(med, color=viz.AXIS, lw=0.8, zorder=1)
    ax.text(v.index[0], med, f" 5-year median {med:.0%}", va="bottom", fontsize=7.5, color=viz.INK2)
    viz.pct_axis(ax)
    viz.titles(ax, "Volatility regimes cluster around earnings and deal news", "Rolling 63-day annualised volatility, five years")
    viz.source(fig, "Yahoo Finance; Bona Fide analysis.")
    viz.save(fig, "stock_rolling_volatility")


def main() -> None:
    raw = {tk: load(tk) for tk in TICKERS}
    hpe = raw["HPE"][raw["HPE"].index >= LISTING_DATE]
    t = technicals(hpe)
    px = pd.DataFrame({tk: raw[tk]["adj_close"] for tk in TICKERS})
    px = px[px.index >= LISTING_DATE]
    price_only = pd.DataFrame({tk: raw[tk]["close"] for tk in TICKERS})
    price_only = price_only[price_only.index >= LISTING_DATE]

    t.to_csv(OUT / "HPE_technicals.csv")
    for rule, name in (("W-FRI", "weekly"), ("ME", "monthly")):
        hpe.resample(rule).agg({"open": "first", "high": "max", "low": "min", "close": "last",
                                "adj_close": "last", "volume": "sum"}).dropna().to_csv(OUT / f"HPE_{name}.csv")

    tr = window_returns(px)
    pr = window_returns(price_only)
    tr.to_csv(OUT / "returns_by_window_total.csv")
    pr.to_csv(OUT / "returns_by_window_price.csv")
    risk = pd.concat({"3Y": risk_stats(px, 3), "Full period": risk_stats(px, None)}, axis=1)
    risk.to_csv(OUT / "risk_stats.csv")

    rets = px.pct_change()
    corr = {}
    for label, start in (("1Y", END - pd.DateOffset(years=1)), ("3Y", END - pd.DateOffset(years=3)),
                         ("Since 2019", pd.Timestamp("2019-01-01"))):
        corr[label] = rets[rets.index > start].corr()["HPE"].drop("HPE")
    corr = pd.DataFrame(corr)
    corr.to_csv(OUT / "correlation_with_hpe.csv")

    wk = px.resample("W-FRI").last().pct_change()
    mo = px.resample("ME").last().pct_change()
    betas = {"2Y weekly vs SPY": beta(wk["HPE"][wk.index > END - pd.DateOffset(years=2)], wk["SPY"]),
             "5Y monthly vs SPY": beta(mo["HPE"][mo.index > END - pd.DateOffset(years=5)], mo["SPY"]),
             "5Y monthly vs XLK": beta(mo["HPE"][mo.index > END - pd.DateOffset(years=5)], mo["XLK"])}

    big = t[(t["ret"].abs() >= 0.07) | (t["zscore"].abs() >= 3)][
        ["close", "ret", "zscore", "gap", "volume", "volume_ratio"]].copy()
    big["spy_ret"] = rets["SPY"].reindex(big.index)
    big["excess_vs_spy"] = big["ret"] - big["spy_ret"]
    big.to_csv(OUT / "big_moves.csv")
    gaps = t[t["gap"].abs() >= 0.05][["open", "close", "gap", "ret", "volume_ratio"]]
    gaps.to_csv(OUT / "gaps_5pct.csv")
    episodes = drawdown_episodes(t["adj_close"])
    episodes.to_csv(OUT / "drawdown_episodes.csv", index=False)
    swings = swing_points(t)
    swings.to_csv(OUT / "swing_points_weekly_3y.csv", index=False)

    last = t.iloc[-1]
    recent = t[t.index > END - pd.DateOffset(months=3)]
    prior = t[(t.index <= END - pd.DateOffset(months=3)) & (t.index > END - pd.DateOffset(months=6))]
    up_vol = lambda df: df.loc[df["ret"] > 0, "volume"].sum() / df["volume"].sum()
    summary = {
        "valuation_date": str(t.index[-1].date()), "close": round(last["close"], 2),
        "sma50": round(last["sma50"], 2), "sma200": round(last["sma200"], 2),
        "pct_above_sma200": round(last["close"] / last["sma200"] - 1, 4),
        "rsi14": round(last["rsi14"], 1), "bb_pctb": round(last["bb_pctb"], 2),
        "vol21": round(last["vol21"], 3), "vol63": round(last["vol63"], 3),
        "vol63_1y_median": round(t["vol63"][t.index > END - pd.DateOffset(years=1)].median(), 3),
        "high52": round(last["high52"], 2), "low52": round(last["low52"], 2),
        "high52_date": str(t["close"][t.index > END - pd.DateOffset(years=1)].idxmax().date()),
        "low52_date": str(t["close"][t.index > END - pd.DateOffset(years=1)].idxmin().date()),
        "pct_from_high52": round(last["close"] / last["high52"] - 1, 4),
        "current_drawdown_total_return": round(last["drawdown"], 4),
        "volume_20d_vs_1y_avg": round(t["volume"].iloc[-20:].mean() / t["volume"].iloc[-252:].mean(), 2),
        "up_volume_share_last3m": round(up_vol(recent), 3), "up_volume_share_prior3m": round(up_vol(prior), 3),
        "obv_change_3m": float(recent["obv"].iloc[-1] - recent["obv"].iloc[0]),
        "price_change_3m": round(recent["close"].iloc[-1] / recent["close"].iloc[0] - 1, 4),
        "macd_above_signal": bool(last["macd"] > last["macd_signal"]),
        "betas": {k: round(v, 2) for k, v in betas.items()},
        "n_big_moves": int(len(big)), "n_gaps_5pct": int(len(gaps)),
        "golden_cross_date": None,
    }
    cross = (t["sma50"] > t["sma200"]).astype(int).diff()
    ups = cross[cross == 1]
    if not ups.empty:
        summary["golden_cross_date"] = str(ups.index[-1].date())
    downs = cross[cross == -1]
    summary["death_cross_date"] = str(downs.index[-1].date()) if not downs.empty else None
    # data-quality cross-check: Yahoo closes vs Nasdaq closes (same spin-off factors, no dividend adjustment)
    nas_path = MKT_DATA / "HPE_nasdaq_daily.csv"
    if nas_path.exists():
        nas = pd.read_csv(nas_path, parse_dates=["date"]).set_index("date")["close"]
        both = pd.concat([hpe["close"], nas], axis=1, keys=["yahoo", "nasdaq"]).dropna()
        diff = (both["yahoo"] / both["nasdaq"] - 1).abs()
        summary["price_cross_check"] = {"overlapping_days": int(len(both)), "median_abs_diff": round(float(diff.median()), 6),
                                        "max_abs_diff": round(float(diff.max()), 4), "days_above_0.5pct": int((diff > 0.005).sum())}
    (OUT / "stock_summary.json").write_text(json.dumps(summary, indent=2))

    charts(t, px)
    pd.set_option("display.width", 200)
    print("Returns (total):\n", (tr * 100).round(1))
    print("Risk:\n", risk.round(3))
    print("Correlation with HPE:\n", corr.round(2))
    print("Summary:", json.dumps(summary, indent=1))
    print("Drawdown episodes:\n", episodes.head(6))
    print("Largest moves (top 15 by |ret|):\n",
          big.reindex(big["ret"].abs().sort_values(ascending=False).index).head(15).round(3))


if __name__ == "__main__":
    main()
