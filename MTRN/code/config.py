"""Frozen research dates; retrieval time is distinct from the information cutoff."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CUTOFF = '2026-09-18'
PREPARED = '2026-09-19'
PRICE = 251.53

def price_history(ticker):
    import pandas as pd
    frame = pd.read_csv(ROOT / f'data/market_data/{ticker}_daily.csv',
                        index_col='date', parse_dates=True)
    frame = frame.loc[:CUTOFF]
    if frame.empty or frame.index[-1].strftime('%Y-%m-%d') != CUTOFF:
        raise ValueError(f'{ticker}: missing cutoff-session price')
    if not frame.index.is_unique or not frame.index.is_monotonic_increasing:
        raise ValueError(f'{ticker}: duplicate or unordered price dates')
    return frame
