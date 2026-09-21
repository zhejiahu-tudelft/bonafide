"""Reproducible price history, indicators, peer returns, and event windows."""
from pathlib import Path
import sys,json
import numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from common.code.market_data_tools import technicals,event_windows
from config import price_history
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'data/processed_data'
TICKERS=['MTRN','SPY','IWM','XLB','ENTG','CRS','ATI','VNP.TO']
EVENTS={
 '2007-02-12':('Large historical move; specific catalyst unverified','unverified'),
 '2020-03-16':('Pandemic market selloff; macro association','context'),
 '2022-11-02':('Q3 2022 earnings','company earnings'),
 '2023-02-16':('FY2022 earnings and 2023 outlook','company earnings'),
 '2024-02-15':('FY2023 earnings and 2024 outlook','company earnings'),
 '2025-07-30':('Q2 2025 earnings; China and tariff uncertainty','company earnings'),
 '2025-10-29':('Q3 2025 earnings date listed on IR calendar','company event'),
 '2026-02-12':('FY2025 earnings; $65m defense customer investment','company earnings'),
 '2026-04-29':('Q1 2026 results; improved outlook','company earnings'),
 '2026-07-28':('Large decline; specific catalyst unverified','unverified'),
 '2026-07-29':('Second consecutive large decline; catalyst unverified','unverified'),
 '2026-07-30':('Rebound; company-specific catalyst unverified','unverified'),
 '2026-08-05':('Record Q2 2026; raised outlook','company earnings'),
 '2026-09-16':('FOMC raises rates 25bp; coincidence does not establish causality','macro event')}

def build():
 prices={t:price_history(t) for t in TICKERS}
 p=prices['MTRN']; t=technicals(p); t.to_csv(OUT/'technicals.csv')
 end=p.index[-1]
 windows={'1M':end-pd.DateOffset(months=1),'3M':end-pd.DateOffset(months=3),'YTD':pd.Timestamp('2025-12-31'),'1Y':end-pd.DateOffset(years=1),'3Y':end-pd.DateOffset(years=3),'5Y':end-pd.DateOffset(years=5)}
 rows=[]
 for tk,d in prices.items():
  row={'ticker':tk,'first_date':str(d.index[0].date()),'close':d.close.iloc[-1]}
  for label,start in windows.items():
   base=d.adj_close[d.index<=start]
   row[label]=d.adj_close.iloc[-1]/base.iloc[-1]-1 if len(base) else np.nan
  x=d.adj_close[d.index>=windows['5Y']]; r=x.pct_change().dropna()
  row['5Y_vol']=r.std()*np.sqrt(252); row['5Y_max_drawdown']=(x/x.cummax()-1).min()
  rows.append(row)
 pd.DataFrame(rows).to_csv(OUT/'stock_returns.csv',index=False)
 rets=pd.concat({tk:d.adj_close.pct_change() for tk,d in prices.items()},axis=1)
 corr=rets.loc[windows['3Y']:].corr();corr.to_csv(OUT/'correlations_3y.csv')
 events=[dict(date=date,event=v[0],evidence=v[1],**event_windows(p,date,prices['SPY'])) for date,v in EVENTS.items()]
 pd.DataFrame(events).to_csv(OUT/'events.csv',index=False)
 t.loc[t['return'].abs().nlargest(30).index,['return','gap','volume_ratio','close']].to_csv(OUT/'largest_moves_full_history.csv')
 t.loc[t.loc['2024':,'return'].abs().nlargest(20).index,['return','gap','volume_ratio','close']].to_csv(OUT/'largest_moves_recent.csv')
 paired=rets[['MTRN','SPY']].loc[windows['3Y']:].dropna()
 summary=t.iloc[-1].to_dict()
 summary.update(first_date=str(p.index[0].date()),last_date=str(end.date()),observations=len(p),
   full_max_drawdown=t.drawdown.min(),full_cagr=(p.adj_close.iloc[-1]/p.adj_close.iloc[0])**(365.25/(end-p.index[0]).days)-1,
   beta_3y=paired.MTRN.cov(paired.SPY)/paired.SPY.var(),high_52w=p.high.tail(252).max(),low_52w=p.low.tail(252).min(),
   avg_volume_50=p.volume.tail(50).mean(),drawdown_recent=p.close.iloc[-1]/p.close.tail(252).max()-1)
 (OUT/'stock_summary.json').write_text(json.dumps(summary,indent=2))
 print(json.dumps(summary,indent=2))
if __name__=='__main__': build()
