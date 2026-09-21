"""Post-protocol diagnostics for interpreting the completed historical study.

Uses cached outputs only. These are descriptive specification/influence checks,
not additional hypothesis tests. The frozen pipeline and report are not changed.
"""
import hashlib
import json

import numpy as np
import pandas as pd

from settings import ROOT, REPO, OUT, CORE, CUTOFF


FEATURES = ["earnings_change_scaled", "operating_margin_change"]
DEST = ROOT / "diagnostics" / "inference_review"


def fit_events(events, features):
    companies = [ticker for ticker in CORE if ticker in set(events.ticker)]
    intercepts = np.column_stack([
        np.asarray(events.ticker == ticker, dtype=float) for ticker in companies
    ])
    x = np.column_stack([intercepts, events[features].to_numpy()])
    y = events.car.to_numpy()
    coefficient = np.linalg.lstsq(x, y, rcond=None)[0]
    null_residual = y - intercepts @ np.linalg.lstsq(intercepts, y, rcond=None)[0]
    residual = y - x @ coefficient
    partial_r2 = 1 - residual @ residual / (null_residual @ null_residual)
    leverage = np.einsum("ij,ji->i", x, np.linalg.pinv(x))
    assert np.linalg.matrix_rank(x) == x.shape[1]
    assert np.isclose(leverage.sum(), x.shape[1])
    return dict(zip(companies + features, coefficient)), partial_r2, leverage


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    used = [OUT / f"{name}.csv" for name in [
        "event_cars", "event_regression", "models", "paired_comparisons",
        "financial_snapshots", "primary_alpha_family",
    ]]
    protected = [ROOT / "final/Historical_Attribution.html", ROOT.parent / "prompt.md"]
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    before = {str(path.relative_to(REPO)): digest(path) for path in used + protected}

    cars = pd.read_csv(OUT / "event_cars.csv")
    events = cars.loc[
        (cars.window == "primary") & (cars.mapping == "conservative")
        & (cars.benchmark == "market")
    ].dropna(subset=["car"] + FEATURES).copy()
    assert len(events) == 92 and not events.duplicated(["ticker", "release_date"]).any()
    assert (pd.to_datetime(events.release_date) <= pd.Timestamp(CUTOFF)).all()
    within = events[FEATURES] - events.groupby("ticker")[FEATURES].transform("mean")
    correlation = float(within.corr().iloc[0, 1])
    sums_of_squares = within.pow(2).groupby(events.ticker).sum()
    shares = sums_of_squares.div(sums_of_squares.sum(), axis=1)
    assert np.allclose(shares.sum(), 1)
    shares.rename(columns={key: key + "_within_ss_share" for key in FEATURES}).to_csv(
        DEST / "event_variation_by_company.csv"
    )

    coefficient, partial_r2, leverage = fit_events(events, FEATURES)
    original = pd.read_csv(OUT / "event_regression.csv").set_index("term").estimate
    assert all(np.isclose(coefficient[key], value) for key, value in original.items())
    events.assign(leverage=leverage)[[
        "ticker", "release_date", "eps", "eps_prior", *FEATURES, "car", "leverage",
        "release_path", "source_url",
    ]].sort_values("leverage", ascending=False).to_csv(DEST / "event_leverage.csv", index=False)

    sensitivities = []
    for omitted in [None] + CORE:
        sample = events if omitted is None else events.loc[events.ticker != omitted]
        for features in [FEATURES, FEATURES[:1], FEATURES[1:]]:
            estimates, fit, _ = fit_events(sample, features)
            sensitivities.append(dict(
                omitted_company=omitted or "none", features=" + ".join(features),
                n=len(sample), partial_r2_over_company_intercepts=fit,
                **{key: estimates.get(key, np.nan) for key in FEATURES},
            ))
    pd.DataFrame(sensitivities).to_csv(DEST / "event_specification_diagnostics.csv", index=False)

    models = pd.read_csv(OUT / "models.csv")
    long = models.loc[models.panel == "long"]
    core_models = long.loc[long.model.isin(["M0", "M1", "M2"])]
    assert core_models.n.nunique() == 1
    fit = core_models.pivot(index="ticker", columns="model", values="r2")
    fit["industry_increment_percentage_points"] = 100 * (fit.M2 - fit.M1)
    fit.to_csv(DEST / "model_fit_comparison.csv")

    paired = pd.read_csv(OUT / "paired_comparisons.csv")
    paired.loc[
        (paired.frequency == "daily") & (paired.basis == "total")
        & paired.panel.isin(["long", "matched"])
    ].to_csv(DEST / "risk_window_comparison.csv", index=False)
    snapshots = pd.read_csv(OUT / "financial_snapshots.csv")
    snapshots.loc[snapshots["asof"] == CUTOFF, [
        "ticker", "asof", "period_end", "market_cap", "fcf", "fcf_yield", "claims_note",
    ]].to_csv(DEST / "cutoff_cash_yields.csv", index=False)

    baseline = json.loads((ROOT / "baseline_hashes.json").read_text())
    assert all(digest(REPO / path) == expected for path, expected in baseline.items())
    assert all(digest(REPO / path) == expected for path, expected in before.items())
    summary = dict(
        status="Post-protocol exploratory diagnostics; no new significance claims",
        cutoff=CUTOFF, n_events=len(events),
        calendar_quarters=int(pd.to_datetime(events.release_date).dt.to_period("Q").nunique()),
        event_within_company_covariate_correlation=correlation,
        two_covariate_vif_after_company_intercepts=1 / (1 - correlation ** 2),
        event_partial_r2_over_company_intercepts=partial_r2,
        ATI_within_earnings_variation_share=float(shares.loc["ATI", FEATURES[0]]),
        ATI_within_margin_variation_share=float(shares.loc["ATI", FEATURES[1]]),
        largest_event_leverage=float(leverage.max()),
        established_monthly_observations=int(core_models.n.iloc[0]),
        factor_sample_end=core_models.end.max(),
        checks="Reproduced original pooled coefficients; shares sum to one; leverage trace "
               "equals parameter count; dates respect cutoff; all baseline and protected hashes preserved",
        baseline_files_preserved=len(baseline), input_and_protected_sha256=before,
    )
    (DEST / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({key: value for key, value in summary.items()
                      if key != "input_and_protected_sha256"}, indent=2))


if __name__ == "__main__":
    main()
