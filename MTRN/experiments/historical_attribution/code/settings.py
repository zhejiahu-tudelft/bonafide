"""Frozen experiment scope and paths; no data retrieval on import."""
from pathlib import Path
import json, sys, hashlib
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[2]
sys.path.insert(0,str(REPO))
RAW=ROOT/'data/raw'; OUT=ROOT/'data/processed'; SOURCES=ROOT/'sources'
TICKERS=['MTRN','ENTG','CRS','ATI','ELMT']; CORE=TICKERS[:4]
CIKS=dict(MTRN=1104657,ENTG=1101302,CRS=17843,ATI=1018963,ELMT=2101698)
CUTOFF='2026-09-18'; MONTH_END='2026-08-31'; START='2016-01-01'
SEED=20260918; REPS=2000

def initialize():
    for p in [RAW,OUT,SOURCES,ROOT/'figures',ROOT/'final']: p.mkdir(parents=True,exist_ok=True)
    cfg=dict(cutoff=CUTOFF,start=START,complete_month_end=MONTH_END,tickers=TICKERS,
             event_start='2021-01-01',seed=SEED,bootstrap_replications=REPS,
             bootstrap_blocks={'daily':10,'weekly':5,'monthly':3,'events_quarters':2},
             monthly_hac_lags=3,monthly_minimum='max(60,10*parameters)',
             pooled_event_minimum=60,pooled_event_minimum_quarters=12)
    (ROOT/'config.json').write_text(json.dumps(cfg,indent=2))
    base=ROOT/'baseline_hashes.json'
    if not base.exists():
        files=[p for d in ['MTRN/final','MTRN/excel','MTRN/data','MTRN/report','MTRN/code','HPE/code'] for p in (REPO/d).rglob('*') if p.is_file() and '__pycache__' not in str(p)]
        files.append(REPO/'MTRN/experiments/prompt.md')
        base.write_text(json.dumps({str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2))

def facts_path(ticker):
    return REPO/f'MTRN/data/financial_data/companyfacts_{ticker}.json' if ticker in CORE else RAW/'companyfacts_ELMT.json'

def prices_path(ticker):
    old=REPO/f'MTRN/data/market_data/{ticker}_daily.csv'
    return old if old.exists() else RAW/f'{ticker}_daily.csv'

def deferred(component,reason):
    p=OUT/'deferrals.json'; rows=json.loads(p.read_text()) if p.exists() else []
    row={'component':component,'reason':reason}
    if row not in rows: rows.append(row)
    p.write_text(json.dumps(rows,indent=2))
