"""Frozen scope for the financial/valuation return and variance experiment."""
from pathlib import Path
import hashlib, json, os, sys

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
OLD = ROOT.parent / 'historical_attribution'
sys.path.insert(0, str(REPO))
RAW = ROOT/'data/raw'
OUT = ROOT/'data/processed'
# Per-issuer and per-stage ledgers: consolidated by score.py, removed after a full rebuild.
INTERIM = ROOT/'data/interim'
FIG = ROOT/'figures'
CUTOFF = '2026-09-18'
LAST_MONTH = '2026-08-31'
CORE = ['MTRN','ENTG','CRS','ATI']
TICKERS = CORE + ['ELMT']
SEED = 20260918
os.environ.setdefault('MPLCONFIGDIR','/tmp/mtrn-models-matplotlib')
# Version 4 is a post-hoc revision frozen in REVISION_SPEC.md before rescoring.
CONFIG = dict(version=4, cutoff=CUTOFF, last_complete_month=LAST_MONTH,
    first_target='2016-01-31', initial_training_months=84,
    first_primary_target='2023-01-31', first_primary_origin='2022-12-30', last_primary_origin='2026-07-31',
    inner_validation_months=24,
    inner_validation='two 12-month blocks; refit at each of the 24 inner origins on labels matured by that origin',
    refit='each origin', retune='first origin and every December origin (forecasting the January target)',
    bootstrap_reps=1999, bootstrap_scheme='circular block, calendar months', bootstrap_block_months=6,
    bootstrap_block_sensitivity=[3,12], confidence=.95, seed=SEED,
    feature_training_min_coverage=.70, feature_clip_quantiles=[.01,.99],
    lambda_grid=[1e-4,1e-3,1e-2,.1,1.,10.,100.], elastic_mixing=[.2,.5,.8], intercept_only_candidate=True,
    penalty_convention='Ridge minimises (1/n)|y-Xb|^2 + lambda|b|^2, i.e. scikit-learn alpha = lambda*n_train; Lasso/Elastic Net alpha = lambda (already per observation)',
    arima_orders=[[0,0],[1,0],[2,0],[0,1],[1,1]],
    dynamic_core=['revenue_growth','operating_margin','earnings_yield','market_return','industry_relative','driver_return'],
    financial_extension=['fcf_equipment_assets','debt_assets'],
    equity_inputs=['roe','roe_diff','book_yield','debt_equity'],
    variance_persistence=['vol_21','vol_63','vol_252'],
    variance_external=['vol_21','vol_63','vol_252','market_vol','vix','industry_vol','driver_vol','yield_10y_change'],
    families=dict(
      R16=[('valuation_added','ridge_full','without_valuation'),('transformations_vs_levels','core_pe_difference','core_pe_level'),
           ('arma_vs_static','arimax','arma_static'),('lags_vs_static','distributed_all_lag1','core_ridge')],
      V20=[('persistence_vs_naive','variance_ridge_persistence','historical_variance63'),
           ('pooling_persistence','pooled_variance_persistence','variance_ridge_persistence'),
           ('pooling_external','pooled_variance_external','variance_ridge_external'),
           ('external_individual','variance_ridge_external','variance_ridge_persistence'),
           ('external_pooled','pooled_variance_external','pooled_variance_persistence')]),
    clark_west_pairs=[('core_ols','historical_mean'),('ar1','historical_mean'),('arx','core_ols'),('core_ols_financial_ext','core_ols')],
    calibration=dict(simulations=500,return_pair=['boost_full','historical_mean'],variance_pair=['garch11','historical_variance63'],
                     descriptive_only_if_size_above=.10,
                     # Amendment 1 (revision_freeze.json): a dense fixed-OLS return series.
                     supplementary_return_pair=['core_ols','historical_mean']),
    rolling_months=84, garch_training_days=1260, ewma_lambda=.94,
    primary_horizon_months=1, secondary_horizon_months=3,
    no_deep_learning=True)

def initialize():
    for p in [RAW,OUT,INTERIM,FIG,ROOT/'sources',ROOT/'final']:p.mkdir(parents=True,exist_ok=True)
    (ROOT/'config.json').write_text(json.dumps(CONFIG,indent=2)+'\n')
    baseline=ROOT/'preservation_hashes.json'
    if not baseline.exists():
        old=json.loads((OLD/'baseline_hashes.json').read_text())
        for p in OLD.rglob('*'):
            if p.is_file() and '__pycache__' not in str(p):old[str(p.relative_to(REPO))]=hashlib.sha256(p.read_bytes()).hexdigest()
        old[str((ROOT.parent/'prompt_v2_financial_valuation_models.md').relative_to(REPO))]=hashlib.sha256((ROOT.parent/'prompt_v2_financial_valuation_models.md').read_bytes()).hexdigest()
        baseline.write_text(json.dumps(old,indent=2)+'\n')

def price_path(ticker):
    name=ticker.replace('=','_').replace('^','')
    for p in [REPO/f'MTRN/data/market_data/{ticker}_daily.csv',OLD/f'data/raw/{ticker}_daily.csv',RAW/f'{name}_daily.csv']:
        if p.exists():return p
    return RAW/f'{name}_daily.csv'

def prices(ticker):
    import pandas as pd
    return pd.read_csv(price_path(ticker),index_col='date',parse_dates=True).sort_index().loc[:CUTOFF]

def fact_path(ticker):
    return OLD/'data/raw/companyfacts_ELMT.json' if ticker=='ELMT' else REPO/f'MTRN/data/financial_data/companyfacts_{ticker}.json'

def defer(component,reason):
    p=OUT/'deferrals.json'; rows=json.loads(p.read_text()) if p.exists() else []
    v=dict(component=component,reason=reason)
    if v not in rows:rows.append(v)
    p.write_text(json.dumps(rows,indent=2)+'\n')
