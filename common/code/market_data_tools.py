"""Price indicators and event windows, using daily observations."""
import numpy as np
import pandas as pd

def technicals(d):
    t=d.copy(); c=t.close; t['return']=t.adj_close.pct_change()
    for n in (20,50,200): t[f'sma{n}']=c.rolling(n).mean()
    for n in (12,26): t[f'ema{n}']=c.ewm(span=n,adjust=False).mean()
    delta=c.diff(); up=delta.clip(lower=0).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    down=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    t['rsi14']=100-100/(1+up/down)
    t['bb_upper']=t.sma20+2*c.rolling(20).std(ddof=0)
    t['bb_lower']=t.sma20-2*c.rolling(20).std(ddof=0)
    for n in (21,63,252): t[f'vol{n}']=t['return'].rolling(n).std()*np.sqrt(252)
    t['drawdown']=t.adj_close/t.adj_close.cummax()-1
    t['volume_ratio']=t.volume/t.volume.rolling(50).mean().shift(1)
    t['gap']=t.open/t.close.shift(1)-1
    return t

def event_windows(prices,date,benchmark):
    i=prices.index.get_indexer([pd.Timestamp(date)])[0]
    if i<1: return {}
    out={}
    for n in [1,3,5]:
        if i+n-1>=len(prices): continue
        before=prices.index[i-1]; end=prices.index[i+n-1]
        ret=prices.adj_close.iloc[i+n-1]/prices.adj_close.iloc[i-1]-1
        br=benchmark.adj_close.loc[end]/benchmark.adj_close.loc[before]-1
        out[f'return_{n}d']=ret; out[f'excess_spy_{n}d']=ret-br
    if i+1<len(prices): out['next_day']=prices.adj_close.iloc[i+1]/prices.adj_close.iloc[i]-1
    return out
