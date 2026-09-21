"""Business-adjacent valuation context, explicit fiscal periods and tag choices."""
from pathlib import Path
import sys,json
import pandas as pd
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from common.code.financial_tools import Facts
from config import price_history
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'data/processed_data'
CONFIG={
 'ENTG':{'periods':[('2025-01-01','2025-12-31',1),('2026-01-01','2026-06-27',1),('2025-01-01','2025-06-28',-1)],'date':'2026-06-27','debt':3456.0,'adjusted_ebitda':925.6},
 'CRS':{'periods':[('2025-07-01','2026-06-30',1)],'date':'2026-06-30','debt':690.7},
 'ATI':{'periods':[('2024-12-30','2025-12-28',1),('2025-12-29','2026-06-28',1),('2024-12-30','2025-06-29',-1)],'date':'2026-06-28','debt':2192.0}}
def build():
 rows=[];audit=[]
 for tk,cfg in CONFIG.items():
  f=Facts(json.loads((ROOT/f'data/financial_data/companyfacts_{tk}.json').read_text()),'2026-09-18')
  def flow(tags): return sum(sgn*f.get(tags,en,st)/1e6 for st,en,sgn in cfg['periods'])
  row={'ticker':tk,'period_end':cfg['date'],'revenue':flow('RevenueFromContractWithCustomerExcludingAssessedTax'),
   'net_income':flow('NetIncomeLoss'),'operating_income':flow('OperatingIncomeLoss'),
   'gross_profit':flow('GrossProfit'),'cfo':flow('NetCashProvidedByUsedInOperatingActivities'),
   'capex':flow(['PaymentsToAcquirePropertyPlantAndEquipment','PaymentsToAcquireProductiveAssets']),
   'cash':f.get('CashAndCashEquivalentsAtCarryingValue',cfg['date'])/1e6,'debt':cfg['debt'],
   'equity':f.get(['StockholdersEquity','StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'],cfg['date'])/1e6}
  row['da']=flow('Depreciation')+flow('AmortizationOfIntangibleAssets') if tk=='ENTG' else flow('DepreciationDepletionAndAmortization')
  row['ebitda_operating']=row['operating_income']+row['da']
  row['adjusted_ebitda']=cfg.get('adjusted_ebitda',np.nan)
  # Latest interim/annual diluted denominator; market cap is an approximation
  # and explicitly distinguished from the company's basic market capitalization.
  st,en,_=cfg['periods'][-2] if len(cfg['periods'])>1 else cfg['periods'][0]
  row['shares']=f.get('WeightedAverageNumberOfDilutedSharesOutstanding',en,st,unit='shares')/1e6
  row['price']=price_history(tk).close.iloc[-1]
  row['market_cap_diluted']=row['price']*row['shares']
  row['ev']=row['market_cap_diluted']+row['debt']-row['cash']
  row['fcf']=row['cfo']-row['capex'];row['net_debt']=row['debt']-row['cash']
  for label,num,den in [('pe','market_cap_diluted','net_income'),('ps','market_cap_diluted','revenue'),('pb','market_cap_diluted','equity'),('ev_revenue','ev','revenue'),('ev_ebitda_operating','ev','ebitda_operating'),('ev_adjusted_ebitda','ev','adjusted_ebitda'),('fcf_yield','fcf','market_cap_diluted'),('operating_margin','operating_income','revenue'),('gross_margin','gross_profit','revenue')]:
   row[label]=row[num]/row[den] if row[den] else np.nan
  rows.append(row); audit.extend([dict(ticker=tk,**a) for a in f.audit])
 pd.DataFrame(rows).to_csv(OUT/'peers.csv',index=False);pd.DataFrame(audit).to_csv(OUT/'peer_financial_audit.csv',index=False)
 print(pd.DataFrame(rows).round(2).to_string(index=False))
if __name__=='__main__': build()
