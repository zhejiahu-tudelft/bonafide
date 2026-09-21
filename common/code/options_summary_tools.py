"""Transparent expiration summaries; no inference of dealer positioning."""
import pandas as pd

def summarize(chain):
    rows=[]
    if chain.empty: return pd.DataFrame()
    for expiry,d in chain.groupby('expiration'):
        calls=d[d.type=='call']; puts=d[d.type=='put']
        ratio=lambda a,b: a/b if b else float('nan')
        near=d.iloc[(d.strike-d.spot).abs().argsort()[:2]]
        rows.append(dict(expiration=expiry,contracts=len(d),usable=int(d.usable.sum()),
            call_volume=calls.volume.sum(),put_volume=puts.volume.sum(),call_oi=calls.open_interest.sum(),
            put_oi=puts.open_interest.sum(),put_call_volume=ratio(puts.volume.sum(),calls.volume.sum()),
            put_call_oi=ratio(puts.open_interest.sum(),calls.open_interest.sum()),
            median_spread=d.spread_pct.median(),atm_strike=near.strike.median(),
            atm_iv=near.iv.median(),days=int(d.days_to_expiration.iloc[0])))
    return pd.DataFrame(rows)
