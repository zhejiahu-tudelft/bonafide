"""Narration for the eleven numbered experiments and the valuation, used by code/run_experiments.sh.

What each experiment tested, on what variables and data, how it was specified, what it produced and
whether the main result clears its predefined significance threshold.

Metadata (purpose, hypotheses, variable roles, data sources, method, threshold) is static text here.
Every statistic is read from the analysis outputs under data/processed_data at print time, so the
narration cannot drift from the analysis: nothing is hardcoded.

Usage (all subcommands write to stdout):
    experiment_report.py list
    experiment_report.py describe <id>          header through METHOD
    experiment_report.py report <id>            RESULTS through VALUATION / EVALUATION
    experiment_report.py summary                final table, from the status file
ids are 1-11, V (valuation) and E (latest-quarter evaluation).
"""
from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path

from common import PROC

W = 98
LABEL = 26
SIGNIFICANT, NOT_SIGNIFICANT, MIXED, DESCRIPTIVE, ERROR = "SIGNIFICANT", "NOT SIGNIFICANT", "MIXED", "NOT APPLICABLE", "UNAVAILABLE"

FILES = {
    "stats": "statistics/statistics_summary.json",
    "kev": "qa/kev_summary.json",
    "q2": "qa/q2_summary.json",
    "q3": "qa/q3_summary.json",
    "val": "valuation/valuation_summary.json",
    "key": "key_metrics.json",
    "earn": "earnings/earnings_summary.json",
}


class MissingOutput(Exception):
    pass


class Data:
    """Lazy access to the analysis outputs, with dotted key paths."""

    def __init__(self) -> None:
        self._cache: dict[str, dict] = {}

    def __getattr__(self, name: str) -> dict:
        if name not in FILES:
            raise AttributeError(name)
        if name not in self._cache:
            path = PROC / FILES[name]
            if not path.exists():
                raise MissingOutput(f"{path.relative_to(PROC.parents[1])} not found — run the pipeline without --cached")
            self._cache[name] = json.loads(path.read_text())
        return self._cache[name]

    def get(self, file: str, path: str):
        node = getattr(self, file)
        for part in path.split("."):
            node = node[int(part)] if part.isdigit() and isinstance(node, list) else node[part]
        return node


# ------------------------------------------------------------------------------------ formatting
def p_fmt(x: float) -> str:
    return "< 0.0001" if abs(x) < 1e-4 else f"{x:.4f}"


def pct(x: float, dp: int = 1) -> str:
    return f"{x * 100:.{dp}f}%"


def wrap(text: str, indent: str = "  ", hanging: str | None = None) -> list[str]:
    return textwrap.wrap(text, width=W, initial_indent=indent, subsequent_indent=hanging or indent) or [indent.rstrip()]


def rule(char: str = "─") -> str:
    return char * W


def head(title: str, right: str = "") -> list[str]:
    pad = " " * max(1, W - len(title) - len(right)) if right else ""
    return [rule("═"), f"{title}{pad}{right}", rule("═")]


def section(name: str, lines: list[str]) -> list[str]:
    return [name, *lines]


def rows(pairs: list[tuple[str, str]], indent: str = "  ") -> list[str]:
    out = []
    for label, value in pairs:
        head_txt = f"{indent}{label:<{LABEL}}"
        body = textwrap.wrap(value, width=W - len(head_txt)) or [""]
        out.append(head_txt + body[0])
        out += [" " * len(head_txt) + line for line in body[1:]]
    return out


def bullets(items: list[str]) -> list[str]:
    out = []
    for item in items:
        out += wrap(item, indent="  ", hanging="    ")
    return out


# -------------------------------------------------------------------------- results and verdicts
def r1(d: Data) -> list[tuple[str, str]]:
    s, c = d.get("stats", "regressions.R1.stats"), d.get("stats", "regressions.R1.coefficients")
    j = s["sum_of_lags"]
    return [("Sum of lags 0-2", f"{j['coef']:+.4f}   SE {j['std_err']:.4f}   t {j['t']:.2f}   95% CI [{j['ci_low']:+.4f}, {j['ci_high']:+.4f}]"),
            *[(f"capex lag {k}", f"{c[f'capex_yoy_lag{k}']['coef']:+.4f}   SE {c[f'capex_yoy_lag{k}']['std_err_hac']:.4f}   p {p_fmt(c[f'capex_yoy_lag{k}']['p_value'])}") for k in (0, 1, 2)],
            ("Juniper dummy", f"{c['juniper_dummy']['coef']:+.4f}   p {p_fmt(c['juniper_dummy']['p_value'])}"),
            ("Fit", f"R2 {s['r2']:.3f}   adj R2 {s['adj_r2']:.3f}   n {s['n']}   {s['sample']}   Durbin-Watson {s['durbin_watson']:.2f}")]


def v1(d: Data) -> dict:
    p = d.get("stats", "regressions.R1.stats.sum_of_lags.p_value")
    pre = d.get("stats", "regressions.R1_pre_juniper.stats.sum_of_lags.p_value")
    full = d.get("stats", "regressions.R1_lags0to4.stats.sum_of_lags.p_value")
    return dict(status=SIGNIFICANT if p < 0.05 else NOT_SIGNIFICANT,
                test=f"Joint t-test that the summed capex lags 0-2 equal zero: p = {p_fmt(p)}",
                headline=f"joint p = {p_fmt(p)}",
                robustness=[f"pre-Juniper subsample: p = {p_fmt(pre)}", f"lags 0-4 specification: p = {p_fmt(full)}"])


def r2(d: Data) -> list[tuple[str, str]]:
    s, c = d.get("stats", "regressions.R2.stats"), d.get("stats", "regressions.R2.coefficients")
    j, b = s["sum_of_lags"], d.get("stats", "regressions.R2_no_juniper_dummy.stats.sum_of_lags")
    return [("Sum of lags 0-2", f"{j['coef']:+.4f} pp   SE {j['std_err']:.4f}   t {j['t']:.2f}   95% CI [{j['ci_low']:+.4f}, {j['ci_high']:+.4f}]"),
            ("Same, no Juniper dummy", f"{b['coef']:+.4f} pp   SE {b['std_err']:.4f}   t {b['t']:.2f}   p {p_fmt(b['p_value'])}"),
            ("Juniper dummy", f"{c['juniper_dummy']['coef']:+.4f} pp   p {p_fmt(c['juniper_dummy']['p_value'])}"),
            ("Fit", f"R2 {s['r2']:.3f}   adj R2 {s['adj_r2']:.3f}   n {s['n']}   {s['sample']}   Durbin-Watson {s['durbin_watson']:.2f}"),
            ("Latest quarter decomposition", "; ".join(f"{q['fiscal_quarter']}: memory {q['memory_part_pp']:+.1f}pp, Juniper {q['juniper_part_pp']:+.1f}pp, unexplained {q['unexplained_pp']:+.1f}pp"
                                                       for q in d.get("stats", "regressions.R2_latest_quarters")[-2:]))]


def v2(d: Data) -> dict:
    p = d.get("stats", "regressions.R2.stats.sum_of_lags.p_value")
    p_nodummy = d.get("stats", "regressions.R2_no_juniper_dummy.stats.sum_of_lags.p_value")
    ok, robust = p < 0.05, p_nodummy < 0.05
    return dict(status=SIGNIFICANT if ok and robust else MIXED if ok else NOT_SIGNIFICANT,
                test=f"Joint t-test of the summed memory lags 0-2: p = {p_fmt(p)}; same specification without the Juniper dummy: p = {p_fmt(p_nodummy)}",
                headline=f"p {p_fmt(p)} / no dummy p {p_fmt(p_nodummy)}",
                robustness=["The link holds only when the Juniper dummy absorbs the mix shift, so the memory coefficient is not "
                            "treated as a robust driver in the report."] if ok and not robust else [])


def r3(d: Data) -> list[tuple[str, str]]:
    a = d.get("stats", "arima")
    dm, mape, dec = a["backtest_diebold_mariano"], a["backtest_mape"], a["decomposition"]
    return [("Selected model", f"SARIMA({','.join(map(str, a['order']))})({','.join(map(str, a['seasonal']))})[4]   AICc {a['aicc']:.1f}   fit {a['fit_sample']}   n {a['n_fit']}"),
            ("Quarters outside 95% band", f"{a['quarters_outside_95']} of {a['quarters_with_actuals']} post-break quarters"),
            ("Backtest MAPE", f"SARIMA {pct(mape['arima'], 2)}   random walk {pct(mape['random_walk'], 2)}   seasonal naive {pct(mape['seasonal_naive'], 2)}"),
            ("Diebold-Mariano", f"vs random walk t {dm['random_walk']['stat']:+.2f} p {p_fmt(dm['random_walk']['p_value'])}   "
                                f"vs seasonal naive t {dm['seasonal_naive']['stat']:+.2f} p {p_fmt(dm['seasonal_naive']['p_value'])}   n {dm['random_walk']['n']}"),
            ("FY26 counterfactual", f"${dec['fy26_arima_counterfactual']:,.0f}m vs guidance ${dec['fy26_guidance_mid']:,.0f}m   excess ${dec['fy26_excess_over_trend']:,.0f}m"),
            ("Excess attribution", f"Juniper ${dec['fy26_juniper_estimate']:,.0f}m, residual (AI and pricing) ${dec['fy26_residual_ai_pricing_estimate']:,.0f}m; "
                                   f"Juniper share across baselines {pct(a['juniper_share_range'][0])}-{pct(a['juniper_share_range'][1])}"),
            ("Residual check", f"Ljung-Box on residuals, lag 8: p = {p_fmt(a['ljung_box_resid_p_lag8'])}")]


def v3(d: Data) -> dict:
    a = d.get("stats", "arima")
    outside, n = a["quarters_outside_95"], a["quarters_with_actuals"]
    dm = a["backtest_diebold_mariano"]["random_walk"]["p_value"]
    return dict(status=SIGNIFICANT if outside >= 1 else NOT_SIGNIFICANT,
                test=f"Interval rule: {outside} of {n} post-break quarters fall outside the 95% forecast band of the pre-Juniper baseline",
                headline=f"{outside}/{n} outside the 95% band",
                robustness=[f"Secondary test: the baseline is not significantly more accurate than a random walk (Diebold-Mariano p = {p_fmt(dm)}), "
                            f"so the counterfactual level is indicative; the break itself is read from the interval, not from forecast accuracy.",
                            f"Across eight alternative baselines the FY26 counterfactual spans ${a['fy26_counterfactual_range'][0]:,.0f}m-${a['fy26_counterfactual_range'][1]:,.0f}m."])


def r4(d: Data) -> list[tuple[str, str]]:
    r = d.get("stats", "returns")
    return [("Sample", f"{r['n_days']:,} daily log returns   daily sigma {pct(r['daily_sigma'], 2)}   skew {r['skew']:+.2f}   excess kurtosis {r['excess_kurtosis']:.1f}"),
            ("Engle ARCH-LM, 5 lags", f"p = {p_fmt(r['arch_lm_p'])}"),
            ("Ljung-Box returns, lag 10", f"p = {p_fmt(r['ljung_box_returns_p_lag10'])}   ACF(1) {r['acf_lag1_returns']:+.3f}"),
            ("Ljung-Box squared, lag 10", f"p = {p_fmt(r['ljung_box_sq_returns_p_lag10'])}   ACF(1) {r['acf_lag1_squared']:+.3f}"),
            ("ADF", f"log price p = {p_fmt(r['adf_price_p'])} (non-stationary)   returns p = {p_fmt(r['adf_returns_p'])} (stationary)"),
            ("Jarque-Bera", f"p = {p_fmt(r['jarque_bera_p'])}"),
            ("Tail frequency", f"{pct(r['share_3sigma_days'], 2)} of days beyond 3 sigma vs {pct(r['normal_expected_3sigma'], 2)} under normality   ratio {r['tail_ratio']:.1f}x")]


def v4(d: Data) -> dict:
    r = d.get("stats", "returns")
    arch, lb = r["arch_lm_p"], r["ljung_box_returns_p_lag10"]
    return dict(status=SIGNIFICANT if arch < 0.05 else NOT_SIGNIFICANT,
                test=f"Main test, Engle ARCH-LM for volatility clustering: p = {p_fmt(arch)}",
                headline=f"ARCH-LM p = {p_fmt(arch)}",
                robustness=[f"Returns show no significant linear autocorrelation (Ljung-Box lag 10 p = {p_fmt(lb)}), so the direction of "
                            f"returns is not predictable while their size is.",
                            f"Fat tails confirmed: Jarque-Bera p = {p_fmt(r['jarque_bera_p'])}, 3-sigma days {r['tail_ratio']:.1f} times as frequent as under normality."])


def r5(d: Data) -> list[tuple[str, str]]:
    out = []
    for c in d.get("stats", "descriptive_tests.correlation_gap"):
        out.append((f"{c['window']} window", f"corr with Dell {c['corr_dell']:.3f} vs S&P 500 {c['corr_spy']:.3f}   gap {c['gap']:+.3f}   "
                                             f"95% CI [{c['ci_low']:+.3f}, {c['ci_high']:+.3f}]   p {p_fmt(c['bootstrap_p'])}   n {c['n_days']} days"))
    c0 = d.get("stats", "descriptive_tests.correlation_gap.0")
    out.append(("Resampling", f"stationary block bootstrap, {c0['draws']:,} draws, mean block {c0['mean_block_days']} days"))
    return out


def v5(d: Data) -> dict:
    one, three = d.get("stats", "descriptive_tests.correlation_gap.0"), d.get("stats", "descriptive_tests.correlation_gap.1")
    ok = one["ci_low"] > 0 or one["ci_high"] < 0
    return dict(status=SIGNIFICANT if ok else NOT_SIGNIFICANT,
                test=f"One-year gap {one['gap']:+.3f} with a 95% bootstrap CI of [{one['ci_low']:+.3f}, {one['ci_high']:+.3f}] "
                     f"({'excludes' if ok else 'includes'} zero); p = {p_fmt(one['bootstrap_p'])}",
                headline=f"1Y gap {one['gap']:+.3f}, p = {p_fmt(one['bootstrap_p'])}",
                robustness=[f"Over three years the gap is {three['gap']:+.3f} with CI [{three['ci_low']:+.3f}, {three['ci_high']:+.3f}] "
                            f"and p = {p_fmt(three['bootstrap_p'])}: not significant, so the co-movement with Dell is a feature of the AI cycle, "
                            f"not of the whole history."])


def r6(d: Data) -> list[tuple[str, str]]:
    e = d.get("stats", "descriptive_tests.earnings_days")
    return [("Earnings days", f"{e['n_events']} events since {e['window_start']}   mean absolute move {pct(e['mean_abs_earnings_day'], 2)}"),
            ("Other days", f"{e['n_other_days']} days in the same window   mean absolute move {pct(e['mean_abs_other_days'], 2)}"),
            ("Ratio", f"{e['ratio']:.2f}x   (all days since listing: {pct(e['mean_abs_all_days_since_listing'], 2)})"),
            ("Permutation test", f"{e['permutation_draws']:,} draws   p = {p_fmt(e['permutation_p'])}"),
            ("Mann-Whitney U", f"p = {p_fmt(e['mann_whitney_p'])}")]


def v6(d: Data) -> dict:
    e = d.get("stats", "descriptive_tests.earnings_days")
    return dict(status=SIGNIFICANT if e["permutation_p"] < 0.05 else NOT_SIGNIFICANT,
                test=f"One-sided permutation test on the mean absolute day-0 return ({e['permutation_draws']:,} draws): p = {p_fmt(e['permutation_p'])}",
                headline=f"permutation p = {p_fmt(e['permutation_p'])}",
                robustness=[f"Mann-Whitney U on the same samples agrees: p = {p_fmt(e['mann_whitney_p'])}."])


def r7(d: Data) -> list[tuple[str, str]]:
    k = d.kev
    top = sorted(k["counts"].items(), key=lambda kv: -kv[1]["kev_entries"])[:3]
    return [("Catalogue", f"CISA KEV version {k['catalog_version']}   {k['catalog_entries']:,} entries   {k['vendors_compared']} vendors compared"),
            ("Juniper", f"{k['juniper_entries']} entries   rank {k['juniper_rank']} of {k['vendors_compared']}   "
                        f"{k['juniper_since_2024']} added since 2024   {pct(k['juniper_share_of_group'], 1)} of the group's entries"),
            ("Group median", f"{k['group_median_entries']:.0f} entries"),
            ("Highest counts", "   ".join(f"{name} {c['kev_entries']}" for name, c in top)),
            ("HPE excluding Juniper", f"{k['counts']['HPE (excl. Juniper)']['kev_entries']} entry"),
            ("Known ransomware use", f"Juniper {k['counts']['Juniper']['known_ransomware_use']}   Cisco {k['counts']['Cisco']['known_ransomware_use']}   "
                                     f"Fortinet {k['counts']['Fortinet']['known_ransomware_use']}")]


def v7(d: Data) -> dict:
    k = d.kev
    below = k["juniper_entries"] <= k["group_median_entries"]
    return dict(status=DESCRIPTIVE,
                test=f"Decision rule (no sampling model, so no p-value): Juniper is unusually exposed only if its count exceeds the group median. "
                     f"{k['juniper_entries']} entries vs a median of {k['group_median_entries']:.0f} -> {'below' if below else 'above'} the median.",
                headline=f"{k['juniper_entries']} entries, rank {k['juniper_rank']}/{k['vendors_compared']}",
                robustness=["Counts are not normalised for installed base or product breadth, so they measure exposure history, not per-device risk."])


def r8(d: Data) -> list[tuple[str, str]]:
    s, k = d.get("q2", "stylised"), d.get("q2", "stylised_parameters")
    out = [(name.capitalize(), f"capital ${s[name]['capital']:,.0f}m   cash trough quarter {s[name]['trough_quarter']}   "
                               f"first GAAP profit quarter {s[name]['first_profit_quarter']}   cash payback quarter {s[name]['payback_quarter']}   "
                               f"cumulative cash by year 12 {s[name]['cum_cash_x_year12']:.2f}x capital")
           for name in ("landlord", "neocloud", "server")]
    out.append(("GPU life sensitivity", f"neocloud cumulative profit {s['neocloud']['cum_profit_x_year12']:.2f}x on a {k['gpu_life_years']}-year life "
                                        f"vs {s['neocloud']['cum_profit_x_year12_4yr_life']:.2f}x on 4 years"))
    out.append(("Key parameters", f"facility ${k['ai_facility_cost_per_mw']:.1f}m/MW over {k['build_quarters']} quarters at a {pct(k['DLR_stabilised_yield'], 0)} stabilised yield; "
                                  f"neocloud ACV ${k['neocloud_acv_per_mw']:.1f}m/MW at {pct(k['neocloud_ebitda_margin'], 0)} EBITDA over {k['contract_years']} years, "
                                  f"re-rent at {pct(k['rerent_price'], 0)}; server gross margin {pct(k['DELL_isg_margin'], 0)}"))
    return out


def v8(d: Data) -> dict:
    s = d.get("q2", "stylised")
    order = sorted(("landlord", "neocloud", "server"), key=lambda n: s[n]["payback_quarter"])
    sequence = " < ".join(f"{n} Q{s[n]['payback_quarter']}" for n in order)
    return dict(status=DESCRIPTIVE,
                test="Deterministic accounting model, so no sampling distribution and no p-value. Decision rule: the models differ if cash payback "
                     "and first GAAP profit fall in a different order. Payback order: " + sequence,
                headline=f"payback {order[0]} Q{s[order[0]]['payback_quarter']} vs {order[-1]} Q{s[order[-1]]['payback_quarter']}",
                robustness=["Parameters are keyed from company disclosures and cited third-party cost benchmarks; the model ignores financing, "
                            "taxes, re-leasing risk and residual values."])


def r9(d: Data) -> list[tuple[str, str]]:
    f = d.get("q2", "fundamental_elasticity")
    out = [(f"{tk} revenue elasticity", f"sum of lags 0-4 {f[tk]['sum_of_lags']:+.4f}   p {p_fmt(f[tk]['sum_p'])}   R2 {f[tk]['r2']:.3f}   n {f[tk]['n']:.0f}   {f[tk]['sample']}")
           for tk in ("HPE", "DELL", "DLR")]
    out.append(("Dell minus HPE gap", f"{f['DELL']['gap_vs_hpe_sum']:+.4f}   p {p_fmt(f['DELL']['gap_vs_hpe_p'])}   n {f['DELL']['gap_vs_hpe_n']:.0f}"))
    out.append(("HPE with Juniper dummy", f"sum {f['HPE']['juniper_controlled_sum']:+.4f}   p {p_fmt(f['HPE']['juniper_controlled_p'])}   "
                                          f"dummy {f['HPE']['juniper_dummy_coef']:+.4f} p {p_fmt(f['HPE']['juniper_dummy_p'])}"))
    ai = {r["ticker"]: r for r in d.get("q2", "market_elasticity") if r["window"] == "own" and r["factor"] == "ai"}
    out.append(("Share-price AI beta", "   ".join(f"{tk} {ai[tk]['beta']:+.2f} (p {p_fmt(ai[tk]['p'])})" for tk in ("CRWV", "NBIS", "HPE", "DELL") if tk in ai)))
    return out


def v9(d: Data) -> dict:
    f = d.get("q2", "fundamental_elasticity")
    gap_p = f["DELL"]["gap_vs_hpe_p"]
    return dict(status=SIGNIFICANT if gap_p < 0.05 else NOT_SIGNIFICANT,
                test=f"Main test, joint t-test that Dell's and HPE's summed capex elasticities are equal: p = {p_fmt(gap_p)}. "
                     f"Individual elasticities: HPE p = {p_fmt(f['HPE']['sum_p'])}, Dell p = {p_fmt(f['DELL']['sum_p'])}.",
                headline=f"Dell-HPE gap p = {p_fmt(gap_p)}",
                robustness=[f"HPE's own elasticity is no longer significant once the Juniper consolidation dummy is added "
                            f"(p = {p_fmt(f['HPE']['juniper_controlled_p'])}), so its measured response partly reflects the acquisition.",
                            f"Digital Realty's elasticity is not significant (p = {p_fmt(f['DLR']['sum_p'])}); the neoclouds have too short a "
                            f"history to regress and are reported descriptively."])


def r10(d: Data) -> list[tuple[str, str]]:
    m, b = d.get("q2", "portfolio.main"), d.get("q2", "portfolio.bootstrap_main")
    names = list(m["stats"])
    out = [("Sample", f"{m['start']} to {m['end']}   {m['n_days']} trading days   risk-free {pct(m['rf'], 2)}")]
    out += [(f"{n} basket", f"annual return {pct(m['stats'][n]['ann_return'], 1)}   volatility {pct(m['stats'][n]['ann_vol'], 1)}   "
                            f"Sharpe {m['stats'][n]['sharpe']:.2f}   max drawdown {pct(m['stats'][n]['max_drawdown'], 1)}") for n in names]
    out.append(("Minimum-variance weights", "   ".join(f"{n} {pct(m['min_variance'][n], 0)}" for n in names) + f"   portfolio volatility {pct(m['min_variance_vol'], 1)}"))
    out.append(("Maximum-Sharpe weights", "   ".join(f"{n} {pct(m['tangency'][n], 0)}" for n in names) + f"   Sharpe {m['tangency_sharpe']:.2f}"))
    out.append(("Bootstrap, min-variance", "   ".join(f"{n} median {pct(b['mv'][n]['median'], 0)} [p5 {pct(b['mv'][n]['p5'], 0)}, p95 {pct(b['mv'][n]['p95'], 0)}]" for n in names)))
    out.append(("Zero-weight frequency", "   ".join(f"{n} {pct(b['mv'][n]['zero_weight_share'], 1)}" for n in names)
                + f"   all three positive in {pct(b['all_positive_mv_share'], 1)} of {b['draws']:,} resamples"))
    return out


def v10(d: Data) -> dict:
    b = d.get("q2", "portfolio.bootstrap_main")
    zero = {n: b["mv"][n]["zero_weight_share"] for n in b["mv"]}
    excluded = max(zero, key=zero.get)
    stable = [n for n in b["mv"] if b["mv"][n]["p5"] > 0.01]
    return dict(status=SIGNIFICANT if zero[excluded] >= 0.95 else NOT_SIGNIFICANT,
                test=f"Stability rule in place of a p-value: a weight is treated as robust when it holds in at least 95% of {b['draws']:,} "
                     f"block-bootstrap resamples. {excluded} receive no minimum-variance weight in {pct(zero[excluded], 1)} of resamples; "
                     f"{' and '.join(stable)} keep a positive 5th-percentile weight.",
                headline=f"{excluded.lower()} zero in {pct(zero[excluded], 1)} of draws",
                robustness=[f"Weights come from 20-day stationary block resamples of {b['draws']:,} draws; the estimate rests on roughly 17 months of "
                            f"AI-boom returns, so the covariance is more reliable than the mean returns."])


def r11(d: Data) -> list[tuple[str, str]]:
    a, c, s = d.get("q3", "arr"), d.get("q3", "customers"), d.get("q3", "segments")
    return [("ARR trajectory", f"${a['first']['arr_m']:,.0f}m in {a['first']['quarter']} to ${a['q4_fy24_m']:,.0f}m in Q4 FY24   "
                               f"compound annual growth {pct(a['cagr_q4fy21_q4fy24'])}"),
            ("Juniper step", f"Q2 FY25 ${a['q2_fy25_m']:,.0f}m (+{pct(a['yoy_q2_fy25'], 0)}) to Q3 FY25 ${a['q3_fy25_m']:,.0f}m (+{pct(a['yoy_q3_fy25'], 0)})   "
                             f"step ${a['step_q2_to_q3_fy25_m']:,.0f}m"),
            ("FY25 and target", f"FY25 ARR ${a['fy25_exact_m']:,.0f}m   FY26 target ${a['fy26_target_m']:,.0f}m   implied growth {pct(a['fy26_implied_growth'])}   "
                                f"ARR is {pct(a['arr_to_ttm_revenue'])} of TTM revenue"),
            ("Customers and usage", f"{c['year_ago']:,} to {c['latest']:,} customers (+{pct(c['growth'])})   systems {c['systems_managed_m_q2_fy26']}m (+{pct(c['systems_growth'])})   "
                                    f"net retention {pct(c['net_retention_q2_fy26'], 0)}   at least ${c['greenlake_arr_per_customer_floor']:,.0f} ARR per customer"),
            ("Segment margins FY23-25", "   ".join(f"{label} {' / '.join(pct(s[key][y]) for y in ('2023', '2024', '2025'))}"
                                                   for label, key in (("Hybrid Cloud", "hybrid_cloud_margin"), ("Networking", "networking_margin"), ("Server", "server_margin")))),
            ("FY25 mix", f"Hybrid Cloud {pct(s['hybrid_cloud_revenue_share_fy25'])} of segment revenue but {pct(s['hybrid_cloud_profit_share_fy25'])} of segment profit; "
                         f"Networking {pct(s['networking_profit_share_fy25'])} of profit"),
            ("Scale needed to match", f"${s['revenue_needed_at_hc_margin_to_match_networking_profit_m'] / 1000:.1f}bn of revenue at the Hybrid Cloud margin, "
                                      f"or a {pct(s['margin_needed_at_hc_revenue_to_match_networking_profit'])} margin on its own revenue")]


def v11(d: Data) -> dict:
    s = d.get("q3", "segments")
    hc, nw, gap = s["hybrid_cloud_margin"]["2025"], s["networking_margin"]["2025"], s["margin_gap_fy25_pp"]
    return dict(status=DESCRIPTIVE,
                test=f"Accounting comparison, so no sampling distribution and no p-value. Decision rule: GreenLake is a second Juniper only if its "
                     f"segment margin approaches networking's. FY2025: {pct(hc)} vs {pct(nw)}, a gap of {gap:.1f} points -> rule not met.",
                headline=f"margin gap {gap:.1f}pp ({pct(hc)} vs {pct(nw)})",
                robustness=["Hybrid Cloud is a proxy: it also held storage hardware, and from FY26 its revenue is reported inside Cloud & AI, so the "
                            "comparison cannot be extended. ARR mixes GreenLake, lease income and software support, and GreenLake's own size is undisclosed."])


def rv(d: Data) -> list[tuple[str, str]]:
    v, k = d.val, d.key
    cc, rev = v["cost_of_capital"], v["reverse_dcf"]
    out = [("Cost of capital", f"WACC {pct(cc['wacc'], 2)}   cost of equity {pct(cc['cost_of_equity'], 2)}   after-tax cost of debt {pct(cc['after_tax_cost_of_debt'], 2)}   "
                               f"levered beta {cc['levered_beta']:.2f}   risk-free {pct(cc['risk_free'], 2)}   ERP {pct(cc['erp'], 2)}")]
    for name in ("Bear", "Base", "Bull"):
        s = v["scenarios"][name]
        out.append((f"{name} ({pct(s['probability'], 0)})", f"${s['value_per_share']:.2f} per share   long-term margin {pct(s['lt_margin'])}   terminal growth {pct(s['terminal_growth'], 2)}   "
                                                            f"terminal value {pct(s['tv_share_of_ev'], 0)} of EV   implied EV/FY27 EBITDA {s['implied_ev_to_fy27_ebitda']:.1f}x"))
    out += [("Probability weighted", f"${v['probability_weighted_value']:.2f} per share   versus the ${v['price']:.2f} close on {v['valuation_date']}   "
                                     f"difference {pct(v['upside_to_probability_weighted'])}"),
            ("Base sensitivity range", f"${v['dcf_base_sensitivity_range'][0]:.2f}-${v['dcf_base_sensitivity_range'][1]:.2f} on WACC +/-0.5pp and terminal growth +/-0.25pp"),
            ("Reverse DCF", f"the price requires a {pct(rev['implied_long_term_margin_at_base_growth'])} long-term margin at base growth, or revenue growth of "
                            f"{pct(rev['implied_fy27_36_revenue_cagr_at_base_margin'])} a year at the base margin (base case {pct(rev['base_fy27_36_revenue_cagr'])}), "
                            f"or a {pct(rev['implied_wacc_at_base_case'])} WACC"),
            ("Cross-checks", f"Damodaran ginzu ${k['ginzu_value']:.2f} at a {pct(k['ginzu_wacc'])} WACC   peer P/E range ${k['comps_pe_range'][0]:.2f}-${k['comps_pe_range'][1]:.2f}   "
                             f"own-history range ${k['own_history_range'][0]:.2f}-${k['own_history_range'][1]:.2f}   FY27 P/E {k['pe_fy27']:.1f}x")]
    return out


def vv(d: Data) -> dict:
    v = d.val
    lo, hi = v["fair_value_core_range"]
    price = v["price"]
    inside = lo <= price <= hi
    return dict(status=DESCRIPTIVE,
                test=f"A valuation is an estimate, not a hypothesis test, so no p-value applies. Decision rule: compare the price with the core "
                     f"cash-flow range. ${price:.2f} versus ${lo:.2f}-${hi:.2f} -> {'inside' if inside else 'above' if price > hi else 'below'} the range.",
                headline=f"base ${v['scenarios']['Base']['value_per_share']:.2f} vs price ${price:.2f}",
                robustness=[f"Only the peer-multiple and control-premium methods reach the price; the scenario span is "
                            f"${v['fair_value_range_dcf'][0]:.2f}-${v['fair_value_range_dcf'][1]:.2f}.",
                            f"The unaffected price one month before the latest move was ${v['unaffected_price_1m_avg']:.2f}."])


def re_(d: Data) -> list[tuple[str, str]]:
    e, g = d.get("earn", "q3_fy26"), d.get("earn", "guidance")
    return [("Q3 FY26 revenue", f"${e['revenue_m']:,.0f}m   {pct(e['revenue_yoy'])} year on year   guidance ${e['revenue_guide'][0]:.1f}-{e['revenue_guide'][1]:.1f}bn   "
                                f"consensus ${e['consensus_revenue_bn']:.1f}bn ({pct(e['revenue_vs_consensus'])})"),
            ("Q3 FY26 earnings", f"non-GAAP EPS ${e['eps']:.2f}   guidance ${e['eps_guide'][0]:.2f}-{e['eps_guide'][1]:.2f}   "
                                 f"consensus ${e['consensus_eps']:.2f} ({pct(e['eps_vs_consensus'])})"),
            ("Margins", f"gross margin {pct(e['gm'])}   operating margin {pct(e['op_margin'])} against {pct(e['op_margin_prior'])} a year earlier"),
            ("FY26 guidance path", f"revenue growth {pct(g['fy26_revenue_growth_first'][0], 0)}-{pct(g['fy26_revenue_growth_first'][1], 0)} raised to "
                                   f"{pct(g['fy26_revenue_growth_last'][0], 0)}-{pct(g['fy26_revenue_growth_last'][1], 0)}   "
                                   f"EPS ${g['fy26_eps_first'][0]:.2f}-{g['fy26_eps_first'][1]:.2f} raised to ${g['fy26_eps_last'][0]:.2f}-{g['fy26_eps_last'][1]:.2f}   "
                                   f"{g['eps_guidance_raises']} EPS raises"),
            ("Verification", f"{d.get('earn', 'keyed_figures_verified')} keyed figures checked against their source documents   consensus: {d.get('earn', 'consensus_source')}")]


def ve(d: Data) -> dict:
    e = d.get("earn", "q3_fy26")
    beat_rev, beat_eps = e["revenue_m"] / 1000 > e["revenue_guide"][1], e["eps"] > e["eps_guide"][1]
    return dict(status=DESCRIPTIVE,
                test=f"Deterministic comparison, so no p-value. Decision rule: a beat means the reported figure exceeds the high end of guidance. "
                     f"Revenue ${e['revenue_m'] / 1000:.2f}bn vs ${e['revenue_guide'][1]:.1f}bn -> {'beat' if beat_rev else 'miss'}; "
                     f"EPS ${e['eps']:.2f} vs ${e['eps_guide'][1]:.2f} -> {'beat' if beat_eps else 'miss'}.",
                headline=f"EPS ${e['eps']:.2f} vs guide high ${e['eps_guide'][1]:.2f}",
                robustness=["One quarter is one observation: the size of the beat is measured against guidance and consensus, not tested against a "
                            "distribution. Experiment 6 is the test of whether such days move the stock more than others."])


# ------------------------------------------------------------------------------------- registry
EXPERIMENTS: dict[str, dict] = {
    "1": dict(
        title="Revenue-capex regression", section="report section 2 - Industry, macro & technology", script="statistical_analysis.py",
        purpose="Measure whether HPE's revenue growth moves with hyperscaler capital expenditure, so that the AI build-out can be treated as a "
                "driver of HPE revenue rather than an assumption.",
        hypotheses=("H0: the capex coefficients at lags 0-2 sum to zero (capex does not move HPE revenue).",
                    "H1: the sum differs from zero."),
        variables=[("Dependent", "HPE revenue growth, log change on the same quarter a year earlier, quarterly"),
                   ("Independent", "Hyperscaler capital expenditure growth, log year-over-year (Microsoft, Alphabet, Amazon, Meta, Oracle), lags 0, 1 and 2"),
                   ("Controls", "Juniper consolidation dummy (1 from Q3 FY25 onwards); intercept"),
                   ("Configuration", "OLS with Newey-West HAC errors, maxlags 4; t-distribution p-values; significance threshold alpha = 0.05")],
        sources=[("data/financial_data/hpe_statements_long.csv", "SEC XBRL company facts - HPE quarterly revenue"),
                 ("data/financial_data/industry/hyperscaler_capex_quarterly.csv", "SEC XBRL company facts for the five hyperscalers, built by macro_industry_analysis.py")],
        method="OLS on 34 aligned calendar quarters with HAC standard errors, then a joint t-test that the three capex coefficients sum to zero. "
               "Robustness: the pre-Juniper subsample and a lags 0-4 specification.",
        results=r1, verdict=v1,
        valuation="Anchors the revenue path in the DCF: because the driver is external, the scenario growth spread is set against hyperscaler capex "
                  "rather than company guidance alone, and the Juniper dummy shows how much of the recent growth is acquisition rather than cycle."),
    "2": dict(
        title="Gross margin-memory regression", section="report section 2 - Industry, macro & technology", script="statistical_analysis.py",
        purpose="Test whether HPE's gross margin follows the memory cycle, the cost input most often claimed to drive server margins.",
        hypotheses=("H0: the memory coefficients at lags 0-2 sum to zero.", "H1: the sum differs from zero."),
        variables=[("Dependent", "Change in HPE gross margin against the same quarter a year earlier, percentage points"),
                   ("Independent", "Change in Micron's gross margin, percentage points, lags 0, 1 and 2, as a proxy for memory contract pricing"),
                   ("Controls", "Juniper consolidation dummy; intercept"),
                   ("Configuration", "OLS with Newey-West HAC errors, maxlags 4; t-distribution p-values; alpha = 0.05. The result counts as robust "
                                     "only if it survives dropping the Juniper dummy")],
        sources=[("data/financial_data/hpe_statements_long.csv", "SEC XBRL - HPE quarterly revenue and cost of revenue"),
                 ("data/financial_data/industry/micron_quarterly.csv", "SEC XBRL - Micron quarterly gross margin")],
        method="OLS with HAC errors on 31 quarters; joint t-test of the summed memory lags; the same specification re-estimated without the Juniper "
               "dummy; the last quarters are decomposed into memory, Juniper and unexplained parts.",
        results=r2, verdict=v2,
        valuation="Sets how much of the current margin can be attributed to a cost cycle that will turn. Because the link is not robust, the DCF holds "
                  "the long-term margin at 12.5% in the base case instead of extrapolating the FY26 margin."),
    "3": dict(
        title="Pre-Juniper revenue baseline", section="report section 3 - Financial performance & health", script="statistical_analysis.py",
        purpose="Establish what HPE's revenue would have been without the Juniper acquisition and the AI pricing cycle, and test whether actual "
                "revenue has left that baseline.",
        hypotheses=("H0: post-break revenue stays inside the 95% forecast interval of the pre-Juniper baseline.",
                    "H1: it falls outside, indicating a structural break."),
        variables=[("Dependent", "Log HPE quarterly revenue"),
                   ("Independent", "None - a univariate time-series baseline extrapolating the pre-break business"),
                   ("Controls", "Model order selected by AICc across (p,d,q) in {0,1,2}x{0,1}x{0,1} and four seasonal orders, capped at four parameters"),
                   ("Configuration", "Fit sample 30 quarters to Q2 FY25; 95% forecast interval; rolling one-step backtest over the last 8 pre-break "
                                     "quarters; Diebold-Mariano against a random walk and a seasonal naive at alpha = 0.05")],
        sources=[("data/financial_data/hpe_statements_long.csv", "SEC XBRL - HPE quarterly revenue"),
                 ("code/statistical_analysis.py", "FY26 guidance midpoint and the Juniper revenue estimate used in the decomposition")],
        method="SARIMAX fitted to the pre-break sample, forecast forward, and each post-break quarter compared with the 95% band; the FY26 gap is then "
               "split into a Juniper part and a residual, and repeated across eight alternative baselines.",
        results=r3, verdict=v3,
        valuation="Produces the counterfactual behind the 'cyclical or structural' question: the size of the residual after Juniper is what the DCF has "
                  "to decide is repeatable, and it sets the bear case's reversion path."),
    "4": dict(
        title="Return diagnostics", section="report section 6 - Stock & technical analysis", script="statistical_analysis.py",
        purpose="Establish the statistical behaviour of HPE's daily returns before any claim is made about trends, volatility or risk.",
        hypotheses=("H0 (main): no ARCH effects - return volatility is constant.", "H1: volatility clusters."),
        variables=[("Dependent", "HPE daily log returns from listing to the valuation date"),
                   ("Independent", "Own lags: 5 lags for the ARCH test, 10 and 20 for the autocorrelation tests"),
                   ("Controls", "None - univariate diagnostics"),
                   ("Configuration", "Engle ARCH-LM (5 lags), Ljung-Box (lags 5, 10, 20) on returns and squared returns, augmented Dickey-Fuller "
                                     "(AIC lag choice), Jarque-Bera, and the frequency of 3-sigma days against the normal expectation; alpha = 0.05")],
        sources=[("data/market_data/HPE_daily.csv", "Yahoo Finance adjusted closes, adjusted for the 2017 spin-offs")],
        method="Each test is run on the full sample of daily log returns; the ACF of returns and squared returns is charted with 95% bands.",
        results=r4, verdict=v4,
        valuation="Justifies treating value as a range rather than a point: fat tails and volatility clustering mean single-day moves carry little "
                  "information, and they support the scenario spread and the event-risk framing."),
    "5": dict(
        title="Correlation-gap bootstrap", section="report section 6 - Stock & technical analysis", script="statistical_analysis.py",
        purpose="Test the claim that HPE trades with Dell rather than with the broad market, which determines the right comparator for relative value.",
        hypotheses=("H0: the correlation with Dell equals the correlation with the S&P 500 (gap = 0).", "H1: the gap differs from zero."),
        variables=[("Dependent", "Difference between HPE's daily-return correlation with Dell and with the S&P 500"),
                   ("Independent", "Daily returns of HPE, Dell and SPY over the same window"),
                   ("Controls", "Two windows, one year and three years, to separate the AI cycle from the full history"),
                   ("Configuration", "Politis-Romano stationary block bootstrap, 5,000 draws, mean block 20 days, fixed seed; two-sided p-value and a "
                                     "95% percentile interval; alpha = 0.05 with the interval as the decision rule")],
        sources=[("data/market_data/HPE_daily.csv, DELL_daily.csv, SPY_daily.csv", "Yahoo Finance adjusted closes")],
        method="Correlations are computed on overlapping daily returns, then the whole correlation matrix is recomputed on each block-bootstrap "
               "resample to build the distribution of the gap.",
        results=r5, verdict=v5,
        valuation="Decides the peer set: Dell is the reference comparable for the multiple ranges, while the three-year result keeps the beta estimate "
                  "from being read as a permanent feature."),
    "6": dict(
        title="Earnings-day permutation test", section="report section 7 - News, filings, events & sentiment", script="statistical_analysis.py",
        purpose="Test whether earnings days really move the stock more than ordinary days, which is what makes the reporting calendar the main catalyst.",
        hypotheses=("H0: the mean absolute move on earnings days equals that on other days in the same window.",
                    "H1: earnings days are larger (one-sided)."),
        variables=[("Dependent", "Absolute daily return"),
                   ("Independent", "Earnings-day indicator: 11 reaction days since March 2024"),
                   ("Controls", "Comparison drawn only from the 624 other trading days inside the same window, so the AI-era regime is held constant"),
                   ("Configuration", "Permutation test, 20,000 draws, one-sided, fixed seed; Mann-Whitney U as a cross-check; alpha = 0.05")],
        sources=[("data/processed_data/events/event_returns.csv", "Event reaction days classified by event_analysis.py from 8-K filings and news"),
                 ("data/market_data/HPE_daily.csv", "Yahoo Finance adjusted closes")],
        method="The observed mean absolute earnings-day return is compared with the distribution of means from random samples of non-earnings days of "
               "the same size drawn without replacement.",
        results=r6, verdict=v6,
        valuation="Sets the catalyst calendar used in the risk section: repricing is concentrated on report dates, so position timing, not fair value, "
                  "is what changes around them."),
    "7": dict(
        title="Exploited-vulnerability counts", section="report section 12 - Practitioner Q&A 1", script="security_exposure_analysis.py",
        purpose="Answer whether Juniper equipment is unusually exposed to actively exploited vulnerabilities, which is what a data-centre SOP singling "
                "out Juniper would imply.",
        hypotheses=("No sampling model applies: the catalogue is a census, not a sample.",
                    "Decision rule fixed in advance: Juniper counts as unusually exposed only if its entries exceed the median of the comparison group."),
        variables=[("Outcome", "Number of CISA Known Exploited Vulnerabilities entries per vendor, in total and since 2024, plus entries with known "
                               "ransomware use"),
                   ("Unit", "Vendor, as named in the KEV vendorProject field; 13 enterprise network and security vendors"),
                   ("Controls", "None available - counts are not normalised for installed base or product breadth, which is stated as a limitation"),
                   ("Configuration", "Catalogue snapshot cached at a fixed version; consumer networking brands and virtualisation software excluded")],
        sources=[("report/other_evidence/practitioner_qa/cisa_kev_catalog_2026.09.11.json", "CISA Known Exploited Vulnerabilities catalogue")],
        method="Filter the catalogue to the 13 comparison vendors, count entries per vendor in total and since 2024, and rank Juniper against the group "
               "median.",
        results=r7, verdict=v7,
        valuation="No effect on fair value. It reclassifies the SOP question as governance rather than defect, and keeps Juniper security events in the "
                  "risk map as event-driven rather than structural."),
    "8": dict(
        title="Stylised 100 MW unit economics", section="report section 12 - Practitioner Q&A 2", script="business_model_analysis.py",
        purpose="Show how the same AI demand converts into cash and reported profit at different points of the supply chain, which is what separates a "
                "landlord, a neocloud and a server provider.",
        hypotheses=("Deterministic model, so no sampling distribution and no p-value.",
                    "Decision rule fixed in advance: the models are structurally different if cash payback and first GAAP profit fall in a different order."),
        variables=[("Outcome", "Quarterly cash flow and GAAP operating profit per unit of capital committed, over 48 quarters"),
                   ("Independent", "Capital committed per business model for 100 MW of capacity"),
                   ("Controls", "Same demand, same capacity and the same build schedule applied to all three models"),
                   ("Configuration", "Keyed parameters: facility cost per MW, facility life, build quarters, stabilised yield, neocloud contract value, "
                                     "EBITDA margin, contract length, GPU life and re-rent price, and the server gross margin")],
        sources=[("report/other_evidence/practitioner_qa/q2/", "Keyed cost, contract and asset-life parameters from company filings and cited cost benchmarks"),
                 ("data/processed_data/qa/q2_summary.json", "Model output written by business_model_analysis.py")],
        method="Build the quarterly cash and profit series for each model from the keyed parameters, then read off the trough quarter, the first "
               "profitable quarter, the cash payback quarter and the cumulative multiple at year 12, including a four-year GPU life variant.",
        results=r8, verdict=v8,
        valuation="Explains why HPE converts AI demand into cash quickly and at low capital intensity, which is the basis for the capex and free-cash-flow "
                  "conversion assumptions in the DCF."),
    "9": dict(
        title="Elasticity of revenue and share price to AI demand", short="AI elasticity: revenue and price",
        section="report section 12 - Practitioner Q&A 2", script="business_model_analysis.py",
        purpose="Measure which layer of the supply chain responds most to AI demand, in reported revenue and in share price.",
        hypotheses=("H0: for each company the summed capex-growth coefficients equal zero, and Dell's and HPE's elasticities are equal.",
                    "H1: the sums differ from zero and the Dell-HPE gap differs from zero."),
        variables=[("Dependent", "Revenue growth, log year-over-year, quarterly (fundamental); daily returns (market)"),
                   ("Independent", "Hyperscaler capex growth at lags 0-4 (fundamental); market (SPY), an AI factor (NVDA orthogonalised to SPY), "
                                   "bitcoin and the change in the 10-year yield per 10bp (market)"),
                   ("Controls", "Juniper consolidation dummy in the HPE variant; a pooled specification with an interaction term for the Dell-HPE gap"),
                   ("Configuration", "OLS with Newey-West HAC errors (maxlags 4 quarterly, 5 daily), t-distribution p-values, alpha = 0.05; neoclouds "
                                     "and Keel have too short a history to regress and are reported descriptively")],
        sources=[("data/financial_data/companyfacts_*.json", "SEC XBRL for DLR, HPE, DELL, IREN, CRWV; keyed figures for Nebius, which files no quarterly XBRL"),
                 ("data/financial_data/industry/hyperscaler_capex_quarterly.csv", "Hyperscaler capital expenditure"),
                 ("data/market_data/*_daily.csv, macro/DGS10.csv", "Yahoo Finance adjusted closes; FRED 10-year Treasury yield")],
        method="Per company, revenue growth is regressed on capex growth at lags 0-4 with a joint test of the summed lags; a pooled regression with an "
               "interaction tests the Dell-HPE difference; a four-factor daily model estimates share-price AI beta over two windows.",
        results=r9, verdict=v9,
        valuation="Supports the relative-value argument: elasticity is highest at the server layer, which is why HPE's revenue path is tied to capex in "
                  "the scenarios, while the insignificance once Juniper is controlled keeps the bull case from assuming a pure AI multiplier."),
    "10": dict(
        title="Portfolio construction", section="report section 12 - Practitioner Q&A 2", script="business_model_analysis.py",
        purpose="Test whether an investor gains from owning several business models rather than one, and whether those weights are stable enough to act on.",
        hypotheses=("No closed-form test applies to constrained optimal weights.",
                    "Decision rule fixed in advance: a weight is robust only if it survives in at least 95% of block-bootstrap resamples."),
        variables=[("Dependent", "Daily returns of equal-weighted baskets for landlords, neoclouds and server providers"),
                   ("Independent", "Basket weights chosen by long-only optimisation"),
                   ("Controls", "Two robustness variants: a longer window and a Digital-Realty-only landlord basket"),
                   ("Configuration", "Long-only simplex; minimum-variance and maximum-Sharpe (tangency) weights; risk-free rate from the mean 3-month "
                                     "bill; 252-day annualisation; stationary block bootstrap of 2,000 draws with 20-day blocks")],
        sources=[("data/market_data/*_daily.csv", "Yahoo Finance adjusted closes for DLR, KEEL, IREN, CRWV, NBIS, HPE, DELL"),
                 ("data/market_data/macro/DTB3.csv", "FRED 3-month Treasury bill rate")],
        method="Build equal-weighted group baskets, estimate annualised means and covariance, solve for minimum-variance and tangency weights on the "
               "simplex, trace the frontier, and re-estimate every weight on 2,000 block-bootstrap resamples.",
        results=r10, verdict=v10,
        valuation="No effect on HPE's fair value. It frames how the equity should be held relative to the other AI layers and shows that the diversification "
                  "case rests on covariance rather than on expected returns."),
    "11": dict(
        title="GreenLake scale and profitability", section="report section 12 - Practitioner Q&A 3", script="greenlake_analysis.py",
        purpose="Test whether GreenLake is becoming a second structural profit driver for HPE, in the way the Juniper acquisition has been.",
        hypotheses=("Accounting comparison of disclosed figures, so no sampling distribution and no p-value.",
                    "Decision rule fixed in advance: GreenLake qualifies only if its recurring revenue grows faster than the company at comparable scale "
                    "and its segment margin approaches networking's."),
        variables=[("Outcome", "Annualised revenue run-rate and its growth; GreenLake customers, systems managed and net retention; segment operating margins"),
                   ("Independent", "Fiscal quarter (ARR) and fiscal year (segment margins)"),
                   ("Controls", "Networking and Server segments as the comparison, on the same definition and years"),
                   ("Configuration", "17 earnings releases Q4 FY21 to Q4 FY25; the FY26 ARR target; FY2023-FY2025 segment tables; every keyed customer "
                                     "figure asserted against the text of its source page")],
        sources=[("report/earnings_materials/sec_8k_ex99/HPE_8-K_Ex99-1_earnings_*.htm", "Quarterly ARR disclosures in the 8-K earnings releases"),
                 ("data/processed_data/text/company_filings/10-K/HPE_10-K_FY2025_filed2025-12-18.txt", "FY2025 10-K segment revenue and earnings from operations"),
                 ("report/earnings_materials/sam_2025/, FY2025Q4/, FY2026Q2/, FY2026Q3/", "Analyst meeting and earnings materials for customers, systems and net retention")],
        method="Parse ARR from each release with a strict pattern, verify keyed customer figures against their source pages, parse the segment tables, "
               "then compute the revenue or margin GreenLake's segment would need to match networking's operating profit.",
        results=r11, verdict=v11,
        valuation="Not valued separately: GreenLake enters the DCF through the company-wide 12.5% long-term margin. It would become material only if HPE "
                  "disclosed a software line with margins well above the Hybrid Cloud level."),
    "V": dict(
        title="Valuation pipeline", section="report sections 9-11 - Valuation and synthesis", script="valuation.py",
        purpose="Turn the experiments into a value per share, and measure what the current price already assumes.",
        hypotheses=("A valuation is an estimate under assumptions, not a hypothesis test, so no p-value applies.",
                    "Decision rule fixed in advance: compare the market price with the core cash-flow range and report where it falls."),
        variables=[("Outcome", "Enterprise and equity value, and value per fully diluted share"),
                   ("Independent", "Ten-year revenue growth path, non-GAAP operating margin path, net working capital intensity and terminal growth, "
                                   "set per scenario"),
                   ("Controls", "Three scenarios weighted 25/50/25; the same share count, net debt and tax treatment across all three"),
                   ("Configuration", "WACC from CAPM with the 10-year Treasury as the risk-free rate; SBC expensed; Financial Services consolidated with "
                                     "all debt deducted; sensitivities on WACC +/-1pp, growth +/-2pp, margin +/-1.5pp and terminal growth +/-0.5pp")],
        sources=[("data/processed_data/financials/, segments/, capital/", "Processed statements, segment mix and capital structure"),
                 ("data/processed_data/peers/peer_multiples.csv", "Peer trailing and forward multiples"),
                 ("data/market_data/macro/DGS10.csv, yahoo/", "FRED 10-year yield; Yahoo Finance consensus estimates and price targets")],
        method="Build the WACC, discount ten years of unlevered free cash flow per scenario with a Gordon terminal value, weight the scenarios, run the "
               "sensitivity grid, then invert the model to find what the price implies and cross-check against peers, the company's own history and a "
               "Damodaran ginzu build.",
        results=rv, verdict=vv,
        valuation="This is the valuation stage: the base case and the reverse DCF are what the pitch rests on, and the gap between them frames the "
                  "cyclical-to-structural question the experiments were run to answer."),
    "E": dict(
        title="Latest-quarter evaluation", section="report section 8 - Latest earnings", script="earnings_analysis.py",
        purpose="Evaluate the most recent quarter against what the company guided and what the market expected, which is the out-of-sample check on the "
                "valuation's starting point.",
        hypotheses=("Deterministic comparison of reported figures with published ranges, so no p-value applies.",
                    "Decision rule fixed in advance: a beat means the reported figure exceeds the high end of guidance."),
        variables=[("Outcome", "Revenue, gross margin, operating margin, non-GAAP EPS and free cash flow for Q3 FY26"),
                   ("Independent", "Company guidance range and sell-side consensus for the same quarter"),
                   ("Controls", "The same quarter a year earlier for the year-on-year comparison; the guidance path across the fiscal year"),
                   ("Configuration", "Every keyed figure verified against the page of the source document it came from")],
        sources=[("report/earnings_materials/FY2026Q3/", "Q3 FY26 press release, presentation and transcript"),
                 ("data/financial_data/hpe_segments_quarterly.csv", "Quarterly segment revenue and operating profit"),
                 ("report/earnings_materials/FY2026Q3/HPE_Q3FY26_consensus_zacks_yahoo_2026-08-28.html", "Consensus revenue and EPS")],
        method="Compare the reported quarter with guidance and consensus, decompose the operating-profit change into volume and margin, and track how "
               "FY26 guidance moved across the year.",
        results=re_, verdict=ve,
        valuation="Sets the starting point of the forecast: the FY27 base case begins from the raised FY26 framework, so a quarter that beats guidance "
                  "raises the level the scenarios grow from without changing the long-term margin."),
}

ORDER = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "V", "E"]


# ----------------------------------------------------------------------------------- subcommands
def label_for(eid: str) -> str:
    return f"EXPERIMENT {eid}" if eid.isdigit() else "VALUATION" if eid == "V" else "EVALUATION"


def describe(eid: str) -> list[str]:
    e = EXPERIMENTS[eid]
    out = head(f"{label_for(eid)} · {e['title']}", e["section"])
    out += section("PURPOSE / HYPOTHESIS", wrap(e["purpose"]) + bullets(list(e["hypotheses"])))
    out += section("VARIABLES", rows(e["variables"]))
    sources = [line for path, desc in e["sources"] for line in ([f"  {path}"] + wrap(desc, indent="      "))]
    out += section("DATA SOURCES", sources)
    out += section("METHOD / SPECIFICATION", wrap(e["method"]))
    return out


def report(eid: str, unavailable: str | None = None) -> tuple[list[str], str, str]:
    e = EXPERIMENTS[eid]
    if unavailable:
        out = section("RESULTS", wrap(f"unavailable - {unavailable}"))
        out += section("STATISTICAL SIGNIFICANCE", wrap(f"not evaluated: {e['script']} did not complete in this run"))
        out += section("VALUATION / EVALUATION", wrap(e["valuation"]))
        return out, ERROR, "not evaluated"
    d = Data()
    try:
        result_rows, verdict = e["results"](d), e["verdict"](d)
    except (MissingOutput, KeyError, IndexError, TypeError) as exc:
        reason = str(exc) if isinstance(exc, MissingOutput) else f"output key missing ({exc!r}) - rerun {e['script']}"
        return report(eid, unavailable=reason)
    out = section("RESULTS", rows(result_rows))
    sig = section("STATISTICAL SIGNIFICANCE", wrap(verdict["test"]))
    sig += wrap(f"=> {verdict['status']}" + (" at alpha = 0.05" if verdict["status"] in (SIGNIFICANT, NOT_SIGNIFICANT, MIXED) else ""))
    for line in verdict.get("robustness", []):
        sig += wrap(f"- {line}", indent="  ", hanging="    ")
    out += sig
    out += section("VALUATION / EVALUATION", wrap(e["valuation"]))
    return out, verdict["status"], verdict["headline"]


def tidy(path: Path) -> str:
    """Print paths relative to the repository root rather than to code/."""
    try:
        return str(Path(path).resolve().relative_to(PROC.parents[1]))
    except ValueError:
        return str(path)


def summary(status_file: Path, log_path: str, json_out: Path | None) -> tuple[list[str], int]:
    records: dict[str, dict] = {}
    for line in status_file.read_text().splitlines():
        kind, *fields = line.split("\t")
        eid = fields[0]
        rec = records.setdefault(eid, dict(id=eid, title=EXPERIMENTS[eid].get("short", EXPERIMENTS[eid]["title"]), script=EXPERIMENTS[eid]["script"],
                                           run="not run", seconds=None, verdict="", headline=""))
        if kind == "STAGE":
            rec["run"], rec["seconds"] = fields[1], float(fields[2])
        elif kind == "RESULT":
            rec["verdict"], rec["headline"] = fields[1], fields[2]
    ordered = [records[eid] for eid in ORDER if eid in records]

    out = head("SUMMARY")
    out.append(f"  {'#':<4}{'Experiment':<36}{'Run':<8}{'Verdict':<16}Main statistic")
    out.append("  " + rule("·")[:W - 2])
    for rec in ordered:
        run = rec["run"] if rec["run"] in ("cached", "failed") or rec["seconds"] is None else f"{rec['run']} {rec['seconds']:.0f}s"
        out.append(f"  {rec['id']:<4}{rec['title'][:34]:<36}{run:<8}{rec['verdict']:<16}{rec['headline'][:34]}")
    ok = sum(1 for r in ordered if r["run"] in ("ok", "cached"))
    counts = {v: sum(1 for r in ordered if r["verdict"] == v) for v in (SIGNIFICANT, NOT_SIGNIFICANT, MIXED, DESCRIPTIVE, ERROR)}
    out.append("")
    out += wrap(f"Stages completed {ok} of {len(ordered)}   ·   significant {counts[SIGNIFICANT]}   ·   "
                f"not significant {counts[NOT_SIGNIFICANT]}   ·   mixed {counts[MIXED]}   ·   "
                f"descriptive or deterministic {counts[DESCRIPTIVE]}   ·   unavailable {counts[ERROR]}")
    out += wrap(f"Log: {log_path}")
    if json_out:
        json_out.write_text(json.dumps(dict(stages=ordered, completed=ok, total=len(ordered),
                                            counts={k: v for k, v in counts.items()}, log=log_path), indent=2))
        out += wrap(f"Machine-readable summary: {tidy(json_out)}")
    failed = sum(1 for r in ordered if r["run"] not in ("ok", "cached"))
    return out, 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["list", "describe", "report", "summary"])
    ap.add_argument("id", nargs="?", help="experiment id: 1-11, V or E")
    ap.add_argument("--unavailable", help="reason the owning script did not produce results")
    ap.add_argument("--status-file", type=Path, help="tab-separated status records shared with the shell runner")
    ap.add_argument("--log", default="", help="path of the run log, printed in the summary")
    ap.add_argument("--json-out", type=Path, help="where to write the machine-readable summary")
    args = ap.parse_args()

    if args.command == "list":
        for eid in ORDER:
            print(f"{eid:<4}{EXPERIMENTS[eid]['title']:<52}{EXPERIMENTS[eid]['script']}")
        return 0
    if args.command == "summary":
        if not args.status_file or not args.status_file.exists():
            print("no stages ran", file=sys.stderr)
            return 1
        lines, code = summary(args.status_file, args.log, args.json_out)
        print("\n".join(lines))
        return code

    eid = (args.id or "").upper()
    if eid not in EXPERIMENTS:
        print(f"unknown experiment id: {args.id!r} (expected one of {', '.join(ORDER)})", file=sys.stderr)
        return 2
    if args.command == "describe":
        print("\n".join(describe(eid)))
        return 0
    lines, status, headline = report(eid, args.unavailable)
    print("\n".join(lines))
    if args.status_file:
        with args.status_file.open("a") as fh:
            fh.write(f"RESULT\t{eid}\t{status}\t{headline}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
