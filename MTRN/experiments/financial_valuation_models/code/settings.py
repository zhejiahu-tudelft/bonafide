"""Frozen scope for the financial/valuation return and variance experiment."""
from pathlib import Path
import hashlib, json, os, sys

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
OLD = ROOT.parent / 'historical_attribution'
sys.path.insert(0, str(REPO))
RAW = ROOT/'data/raw'
OUT = ROOT/'data/processed'
FIG = ROOT/'figures'
CUTOFF = '2026-09-18'
LAST_MONTH = '2026-08-31'
CORE = ['MTRN','ENTG','CRS','ATI']
TICKERS = CORE + ['ELMT']
SEED = 20260918
os.environ.setdefault('MPLCONFIGDIR','/tmp/mtrn-models-matplotlib')
CONFIG = dict(version=3, cutoff=CUTOFF, last_complete_month=LAST_MONTH,
    first_target='2016-01-31', initial_training_months=84,
    first_primary_target='2023-01-31', inner_validation_months=24,
    refit='each origin', retune='annually; fixed candidates between retunes',
    bootstrap_reps=2000, bootstrap_block_months=6, seed=SEED,
    feature_training_min_coverage=.70, feature_clip_quantiles=[.01,.99],
    regularization_grid=[.01,.1,1.,10.,100.], elastic_mixing=[.2,.5,.8],
    arima_orders=[[0,0],[1,0],[2,0],[0,1],[1,1]],
    dynamic_core=['revenue_growth','operating_margin','earnings_yield','market_return','industry_relative','driver_return'],
    rolling_months=84, garch_training_days=1260, ewma_lambda=.94,
    primary_horizon_months=1, secondary_horizon_months=3,
    no_deep_learning=True)

def initialize():
    for p in [RAW,OUT,FIG,ROOT/'sources',ROOT/'final']:p.mkdir(parents=True,exist_ok=True)
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
