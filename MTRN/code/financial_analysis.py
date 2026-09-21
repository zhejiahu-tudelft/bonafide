"""Five annual periods and trailing reported quarters, sourced from SEC facts."""
from pathlib import Path
import sys,json
import pandas as pd
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from common.code.financial_tools import Facts
ROOT=Path(__file__).resolve().parents[1]
CUTOFF='2026-09-18'
FLOW={
 'revenue':['RevenueFromContractWithCustomerExcludingAssessedTax','SalesRevenueNet'],
 'gross_profit':'GrossProfit','operating_income':'OperatingIncomeLoss','net_income':'NetIncomeLoss',
 'tax':'IncomeTaxExpenseBenefit','interest':['InterestExpenseNonoperating','InterestAndDebtExpense','InterestExpense'],
 'cfo':'NetCashProvidedByUsedInOperatingActivities',
 'ppe_capex':['PaymentsToAcquireOtherPropertyPlantAndEquipment','PaymentsToAcquirePropertyPlantAndEquipment'],
 'mine_capex':'PaymentsToAcquireMiningAssets','da':'DepreciationDepletionAndAmortization',
 'amortization':'AmortizationOfIntangibleAssets','sbc':'ShareBasedCompensation',
 'rnd':'ResearchAndDevelopmentExpense','dividends':['PaymentsOfDividendsCommonStock','PaymentsOfDividends'],'repurchases':'PaymentsForRepurchaseOfCommonStock',
 'diluted_shares':'WeightedAverageNumberOfDilutedSharesOutstanding','basic_shares':'WeightedAverageNumberOfSharesOutstandingBasic',
 'eps':'EarningsPerShareDiluted'}
STOCK={
 'cash':'CashAndCashEquivalentsAtCarryingValue','assets':'Assets','current_assets':'AssetsCurrent',
 'liabilities':'Liabilities','current_liabilities':'LiabilitiesCurrent','equity':'StockholdersEquity',
 'debt_current':'LongTermDebtCurrent','debt_noncurrent':'LongTermDebtNoncurrent','debt_face':'LongTermDebt',
 'goodwill':'Goodwill','intangibles':['IntangibleAssetsNetExcludingGoodwill','FiniteLivedIntangibleAssetsNet'],
 'receivables':'AccountsReceivableNetCurrent','inventory':'InventoryNet','payables':'AccountsPayableCurrent',
 'shares_issued':'CommonStockSharesIssued','treasury_shares':['TreasuryStockCommonShares','TreasuryStockShares'],
 'finance_lease_current':'FinanceLeaseLiabilityCurrent','finance_lease_noncurrent':'FinanceLeaseLiabilityNoncurrent'}

def build():
 f=Facts(json.loads((ROOT/'data/financial_data/companyfacts_MTRN.json').read_text()),CUTOFF)
 periods={str(y):(f'{y}-01-01',f'{y}-12-31') for y in range(2021,2026)}
 periods.update({'H1 2025':('2025-01-01','2025-06-27'),'H1 2026':('2026-01-01','2026-07-03')})
 out={}
 for label,(start,end) in periods.items():
  row={'start':start,'end':end}
  for name,tags in FLOW.items():
   unit='shares' if 'shares' in name else ('USD/shares' if name=='eps' else 'USD')
   row[name]=f.get(tags,end,start,unit,label=name)/(1 if name=='eps' else 1e6)
  for name,tags in STOCK.items():
   row[name]=f.get(tags,end,unit='shares' if 'shares' in name else 'USD',label=name)/1e6
  if pd.isna(row['interest']): row['interest']=-f.get('InterestIncomeExpenseNet',end,start,label='interest')/1e6
  row['liabilities']=row['assets']-row['equity']
  out[label]=row
 # Explicit cash-flow statement mining outflows; company-specific tags are
 # not included in the standard SEC company-facts feed for all annual periods.
 for y in ('2021','2022'): out[y]['mine_capex']=0.0
 for y,val in [('2023',9.326),('2024',12.159),('2025',26.288)]:
  out[y]['mine_capex']=val
  f.audit.append(dict(metric='mine_capex',tag='manual: cash flow statement mining development',start=y+'-01-01',end=y+'-12-31',unit='USD',val=val*1e6,filed='2026-02-12',accn='0001104657-26-000011'))
 # FY2021-22 value-added sales are the comparable recast figures in FY2023 10-K.
 va={'2021':829.572,'2022':1114.411,'2023':1127.071,'2024':1097.577,'2025':1046.194,'H1 2025':528.316,'H1 2026':569.978}
 adj={'2021':143.6,'2022':196.0,'2023':217.7,'2024':221.2,'2025':217.0,'H1 2025':104.5,'H1 2026':124.8}
 for key in out: out[key]['va_sales']=va[key]; out[key]['adjusted_ebitda']=adj[key]
 for key,shares in [('H1 2025',20.727),('H1 2026',20.834)]:
  out[key]['treasury_shares']=out[key]['shares_issued']-shares
  f.audit.append(dict(metric='treasury_shares',tag='manual: statement of shareholders equity',end=out[key]['end'],unit='shares',val=out[key]['treasury_shares']*1e6,filed='2026-08-05',accn='0001104657-26-000044'))
 t={k:out['2025'][k]+out['H1 2026'][k]-out['H1 2025'][k] for k in list(FLOW)+['va_sales','adjusted_ebitda']}
 t.update({k:out['H1 2026'][k] for k in STOCK})
 # TTM is 371 days because interim fiscal cutoffs differ, explicitly disclosed.
 t.update(start='2025-06-28',end='2026-07-03')
 for name in ('basic_shares','diluted_shares'):
  t[name]=(out['2025'][name]*365+out['H1 2026'][name]*184-out['H1 2025'][name]*178)/371
 out['TTM']=t
 # Company deck (Q2 2026, p16) provides the TTM total, avoiding accumulated
 # rounding in annual plus half-year figures (237.3 using displayed inputs).
 out['TTM']['adjusted_ebitda']=237.2
 df=pd.DataFrame(out).T
 for name in list(FLOW)+list(STOCK)+['va_sales','adjusted_ebitda']: df[name]=pd.to_numeric(df[name],errors='coerce')
 df['capex']=df.ppe_capex+df.mine_capex
 df['fcf']=df.cfo-df.capex
 df['debt']=df.debt_current+df.debt_noncurrent
 df['net_debt']=df.debt-df.cash
 df['ebitda']=df.net_income+df.tax+df.interest+df.da
 df['operating_ebitda']=df.operating_income+df.da
 df['gross_margin']=df.gross_profit/df.revenue
 df['gross_margin_va']=df.gross_profit/df.va_sales
 df['operating_margin']=df.operating_income/df.revenue
 df['net_margin']=df.net_income/df.revenue
 df['fcf_margin']=df.fcf/df.revenue
 df['sbc_revenue']=df.sbc/df.revenue
 df['current_ratio']=df.current_assets/df.current_liabilities
 df['debt_equity']=df.debt/df.equity
 df['actual_shares']=df.shares_issued-df.treasury_shares
 df['interest_cover']=df.operating_income/df.interest
 df['fcf_per_share']=df.fcf/df.diluted_shares
 df['fcf_conversion']=df.fcf/df.net_income
 df['adjusted_ebitda_margin_va']=df.adjusted_ebitda/df.va_sales
 df.to_csv(ROOT/'data/processed_data/financial_history.csv',index_label='period')
 pd.DataFrame(f.audit).to_csv(ROOT/'data/processed_data/financial_audit.csv',index=False)
 print(df[['revenue','va_sales','net_income','ebitda','cfo','capex','fcf','debt','diluted_shares','actual_shares']].round(3).to_string())
 print('Missing:',df.columns[df.isna().any()].tolist())
 return df

if __name__=='__main__': build()
