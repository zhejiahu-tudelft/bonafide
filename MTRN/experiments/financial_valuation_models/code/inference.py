"""Paired forecast-loss inference: one procedure whose intervals and p-values agree.

Estimand: the population mean of d_t = loss(reduced)_t - loss(expanded)_t over the
evaluation months, conditional on the saved forecasts. Positive favours the expanded
(richer or alternative) model. H0: E[d] = 0; H1: E[d] != 0 (two-sided).

Resampling: circular block bootstrap of calendar months. Blocks wrap around the end
of the sample, so every month is equally likely to be drawn and the bootstrap mean
is centred exactly on the sample mean. A joint cross-company result averages the
companies' differentials within each calendar month first, so complete months (all
companies together) are resampled, never individual company-month rows.

Interval: percentile, read from order statistics k = (B+1)a/2 and (B+1)(1-a/2).
p-value: the smallest a at which that interval excludes zero,
p = 2 (min(#{d*<=0}, #{d*>=0}) + 1) / (B + 1). Hence p <= a exactly when zero lies
outside the (1-a) interval. The resolution of p is 2/(B+1).

What this does not capture: estimation and hyperparameter-selection uncertainty
(forecasts are held fixed) and the specification search that preceded the test.
"""
import numpy as np
from scipy import stats

REPS = 1999
ALPHA = .05
SEED = 20260918

def circular_block_indices(n, length, reps, rng):
    if n < 2 or not 1 <= length <= n:
        raise ValueError('Invalid block/sample size')
    starts = rng.integers(0, n, size=(reps, int(np.ceil(n / length))))
    return ((starts[:, :, None] + np.arange(length)) % n).reshape(reps, -1)[:, :n]

def order_ranks(reps=REPS, alpha=ALPHA):
    lo = (reps + 1) * alpha / 2
    if abs(lo - round(lo)) > 1e-9:
        raise ValueError('Choose B so that (B+1)*alpha/2 is an integer')
    return int(round(lo)), int(round((reps + 1) * (1 - alpha / 2)))

def paired_inference(delta, block, reps=REPS, seed=SEED, alpha=ALPHA):
    """Delta is (n,) for one company or (n, k) for k companies on common months."""
    d = np.asarray(delta, float)
    series = d.mean(axis=1) if d.ndim == 2 else d
    n = len(series)
    idx = circular_block_indices(n, min(block, n), reps, np.random.default_rng(seed))
    draws = np.sort(series[idx].mean(axis=1))
    k_lo, k_hi = order_ranks(reps, alpha)
    below, above = int(np.sum(draws <= 0)), int(np.sum(draws >= 0))
    return dict(n=n, mean_loss_reduction=float(series.mean()), lo=float(draws[k_lo - 1]), hi=float(draws[k_hi - 1]),
                pvalue=min(1., 2 * (min(below, above) + 1) / (reps + 1)), bootstrap_se=float(draws.std(ddof=1)),
                block=int(block), replications=reps, confidence=1 - alpha, monte_carlo_resolution=2 / (reps + 1))

def reverse(result):
    """The same comparison read the other way: negate the mean and swap the endpoints."""
    r = dict(result)
    r['mean_loss_reduction'] = -result['mean_loss_reduction']
    r['lo'], r['hi'] = -result['hi'], -result['lo']
    return r

def holm(pvalues):
    """Holm step-down adjustment over one declared family of comparisons."""
    pvalues = np.asarray(pvalues, float)
    order = np.argsort(pvalues); m = len(pvalues); adjusted = np.empty(m); running = 0.
    for rank, idx in enumerate(order):
        running = max(running, min(1., (m - rank) * pvalues[idx])); adjusted[idx] = running
    return adjusted

def newey_west_se(x, lags):
    u = np.asarray(x, float) - np.mean(x); n = len(u); s = u @ u / n
    for lag in range(1, lags + 1):
        s += 2 * (1 - lag / (lags + 1)) * (u[lag:] @ u[:-lag]) / n
    return float(np.sqrt(max(s, 0) / n))

def clark_west(actual, small, big, lags=None):
    """Clark-West (2007) adjusted MSPE test for nested linear forecasts, one-sided.

    Adds back the extra-parameter noise the larger model pays under H0, so the test
    asks whether the extra predictors have population predictive content. It is not
    a test that the larger model's forecasts are more accurate in this sample.
    """
    y, a, b = (np.asarray(v, float) for v in (actual, small, big))
    f = (y - a) ** 2 - ((y - b) ** 2 - (a - b) ** 2)
    n = len(f); lags = int(np.floor(4 * (n / 100) ** (2 / 9))) if lags is None else lags
    se = newey_west_se(f, lags)
    t = float(f.mean() / se) if se > 0 else np.nan
    return dict(n=n, adjusted_mean=float(f.mean()), t_stat=t, pvalue_one_sided=float(1 - stats.norm.cdf(t)) if np.isfinite(t) else np.nan,
                newey_west_lags=lags, mspe_small=float(np.mean((y - a) ** 2)), mspe_big=float(np.mean((y - b) ** 2)))

def detectable_effect(se, alpha=ALPHA, power=.8):
    """Smallest mean loss reduction a two-sided test detects with the given power,
    under a normal approximation that takes the bootstrap standard error as known."""
    return float((stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power)) * se)

def leave_one_out(delta, labels, block, reps=REPS, seed=SEED, alpha=ALPHA):
    """Loss-only influence: drop every month carrying one label, forecasts held fixed.

    This is not a refit robustness test: training samples and fitted models are
    unchanged; only the evaluation set loses the labelled months.
    """
    d = np.asarray(delta, float); labels = np.asarray(labels)
    full = paired_inference(d, block, reps, seed, alpha); rows = []
    for label in sorted(set(labels.tolist())):
        keep = labels != label
        r = paired_inference(d[keep], block, reps, seed, alpha)
        rows.append(dict(excluded=label, months_excluded=int((~keep).sum()), **r,
                         change_in_mean=r['mean_loss_reduction'] - full['mean_loss_reduction'],
                         sign_flip=bool(np.sign(r['mean_loss_reduction']) != np.sign(full['mean_loss_reduction'])),
                         decision_flip=bool((r['pvalue'] <= alpha) != (full['pvalue'] <= alpha))))
    return full, rows

def stationary_indices(n, mean_block, rng):
    idx = np.empty(n, int); i = 0
    while i < n:
        start = rng.integers(0, n); length = rng.geometric(1 / mean_block)
        for j in range(length):
            if i >= n:
                break
            idx[i] = (start + j) % n; i += 1
    return idx

def null_calibration(delta, block, sims=500, reps=REPS, seed=SEED, alpha=ALPHA):
    """Empirical size of the paired test at level alpha under a data-mimicking null.

    Synthetic samples resample the demeaned observed differentials with a stationary
    bootstrap (random block lengths, mean `block`), keeping their heavy tails and
    serial dependence while imposing E[d] = 0. Rejection frequency near alpha means
    the test is calibrated for series like this one; far above alpha means it is not.
    """
    base = np.asarray(delta, float) - np.mean(delta); rng = np.random.default_rng(seed)
    rejections = 0
    for s in range(sims):
        synthetic = base[stationary_indices(len(base), block, rng)]
        rejections += paired_inference(synthetic, block, reps, int(rng.integers(1, 2**31)), alpha)['pvalue'] <= alpha
    size = rejections / sims
    return dict(empirical_size=size, monte_carlo_se=float(np.sqrt(size * (1 - size) / sims)), simulations=sims, nominal=alpha)
