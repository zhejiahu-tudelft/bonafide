"""Unlevered DCF and separate 12-month fiscal-2027 earnings scenarios (USD m)."""
from pathlib import Path
import sys,json
import numpy as np,pandas as pd
from scipy.optimize import brentq
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from common.code.financial_tools import fcff,dcf
from config import CUTOFF, PRICE, price_history
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'data/processed_data'
# Keep debt convention explicit: principal, estimated total finance leases,
# unfunded retirement liability, less cash. Operating leases remain operating.
CLAIMS={'debt_principal':442.332,'finance_leases':13.3,'retirement':23.155,'cash':19.987}
SHARES=21.15
SCENARIOS={
 'Downside':{'growth':[.00,.03,.04,.04,.04],'ebitda_margin':[.205,.21,.215,.22,.22],
  'da_ratio':.067,'capex_ratio':.085,'nwc_ratio':.35,'tax':[.18,.19,.20,.21,.21],'wacc':.12,'g':.02},
 'Base':{'growth':[.075,.12,.10,.08,.06],'ebitda_margin':[.235,.24,.245,.25,.25],
  'da_ratio':.062,'capex_ratio':.078,'nwc_ratio':.30,'tax':[.17,.18,.19,.20,.20],'wacc':.105,'g':.03},
 'Upside':{'growth':[.15,.20,.18,.15,.12],'ebitda_margin':[.25,.265,.275,.28,.28],
  'da_ratio':.060,'capex_ratio':.08,'nwc_ratio':.28,'tax':[.16,.17,.18,.18,.18],'wacc':.095,'g':.035}}

def forecast(cfg,initial):
 rows=[];last=initial
 for i in range(5):
  va=last*(1+cfg['growth'][i]); margin=cfg['ebitda_margin'][i]
  da=va*cfg['da_ratio']; capex=va*cfg['capex_ratio']; wc=(va-last)*cfg['nwc_ratio']
  eb=va*margin; ebit=eb-da;tax=cfg['tax'][i]
  # Pass-through ratio is a presentation assumption, excluded from value creation.
  revenue=va/.55
  rows.append(dict(year=i+1,period_end=f'{2026+i+1}-09-18',va_sales=va,revenue=revenue,
    growth=cfg['growth'][i],ebitda_margin=margin,ebitda=eb,da=da,ebit=ebit,
    capex=capex,change_nwc=wc,tax_rate=tax,fcff=fcff(ebit,tax,da,capex,wc)))
  last=va
 return pd.DataFrame(rows)

def terminal_fcff(f,cfg,g=None):
 g=cfg['g'] if g is None else g
 last=f.iloc[-1];va=last.va_sales*(1+g)
 return fcff(va*(last.ebitda_margin-cfg['da_ratio']),last.tax_rate,va*cfg['da_ratio'],va*cfg['capex_ratio'],last.va_sales*g*cfg['nwc_ratio'])

def build():
 assert abs(price_history('MTRN').close.iloc[-1]-PRICE)<.005, 'Valuation price does not match cutoff session'
 hist=pd.read_csv(OUT/'financial_history.csv',index_col='period');t=hist.loc['TTM']; last=hist.loc['2025']
 actual_shares=t.actual_shares; cap=actual_shares*PRICE
 netclaims=CLAIMS['debt_principal']+CLAIMS['finance_leases']+CLAIMS['retirement']-CLAIMS['cash']
 ev_standard=cap+CLAIMS['debt_principal']+CLAIMS['finance_leases']-CLAIMS['cash']
 multiple={'date':'2026-09-18','price':PRICE,'basic_shares':actual_shares,'dcf_diluted_shares':SHARES,
  'market_cap':cap,'ev_standard':ev_standard,'ev_including_retirement':ev_standard+CLAIMS['retirement'],
  'net_claims_dcf':netclaims,'pe_ttm_gaap':PRICE/t.eps,'pe_2026_guidance_mid':PRICE/7.0,
  'ps':cap/t.revenue,'pb':cap/t.equity,'ev_revenue':ev_standard/t.revenue,
  'ev_va_sales':ev_standard/t.va_sales,'ev_ebitda':ev_standard/t.ebitda,
  'ev_operating_ebitda':ev_standard/t.operating_ebitda,'ev_adjusted_ebitda':ev_standard/t.adjusted_ebitda,
  'fcf_yield':t.fcf/cap,'dividend_yield':.58/PRICE,'claims':CLAIMS}
 initial=last.va_sales*1.15
 summary=[]; forecasts={}
 for name,cfg in SCENARIOS.items():
  f=forecast(cfg,initial);forecasts[name]=f
  terminal=terminal_fcff(f,cfg)
  result=dcf(f.fcff.tolist(),cfg['wacc'],cfg['g'],netclaims,SHARES,terminal_cashflow=terminal)
  result['terminal_fcff']=terminal
  result.update(scenario=name,wacc=cfg['wacc'],g=cfg['g'],return_vs_price=result['per_share']/PRICE-1,initial_va=initial)
  summary.append(result); f.to_csv(OUT/f'dcf_{name.lower()}.csv',index=False)
 sensitivity=[]
 for w in [.085,.095,.105,.115,.125]:
  sensitivity.append({'wacc':w,**{str(g):dcf(forecasts['Base'].fcff.tolist(),w,g,netclaims,SHARES,terminal_cashflow=terminal_fcff(forecasts['Base'],SCENARIOS['Base'],g))['per_share'] for g in [.02,.025,.03,.035,.04]}})
 pd.DataFrame(sensitivity).to_csv(OUT/'dcf_sensitivity.csv',index=False)
 pd.DataFrame(summary).to_csv(OUT/'dcf_summary.csv',index=False)
 def reverse(growth):
  cfg={**SCENARIOS['Base'],'growth':[growth]*5}
  f=forecast(cfg,initial)
  return dcf(f.fcff.tolist(),cfg['wacc'],cfg['g'],netclaims,SHARES,terminal_cashflow=terminal_fcff(f,cfg))['per_share']-PRICE
 multiple['reverse_dcf_constant_va_growth']=brentq(reverse,0,.75)
 # Fundamental earnings scenarios at a 12-month horizon, fiscal-2027 estimates.
 cases=[('Downside',0,.31,.20,80,100,.30,.18,30,20),
        ('Base',.10,.36,.24,82,110,.30,.17,28,24),
        ('Upside',.22,.40,.27,88,150,.28,.16,26,28)]
 scenarios=[]
 for name,g,gm,em,da,capex,wcr,tax,interest,pe in cases:
  va=initial*(1+g); ebitda=va*em;ebit=ebitda-da; gross_profit=va*gm
  ni=(ebit+10-interest)*(1-tax);eps=ni/SHARES;target=eps*pe
  cash=fcff(ebit,tax,da,capex,(va-initial)*wcr)
  scenarios.append(dict(scenario=name,fy2026_va_anchor=initial,fy2027_va=va,growth=g,gross_margin_va=gm,
    gross_profit=gross_profit,revenue=va/.55,gross_margin_gaap=gm*.55,ebitda_margin_va=em,
    ebitda=ebitda,da=da,ebit=ebit,operating_margin_gaap=ebit/(va/.55),tax=tax,
    interest=interest,acquisition_amortization_addback=10,adjusted_net_income=ni,eps=eps,
    capex=capex,nwc_ratio=wcr,change_nwc=(va-initial)*wcr,fcff=cash,normalized_equity_fcf=cash-interest*(1-tax),
    assumed_pe=pe,price=target,price_return=target/PRICE-1))
 pd.DataFrame(scenarios).to_csv(OUT/'fundamental_scenarios.csv',index=False)
 (OUT/'valuation_summary.json').write_text(json.dumps(multiple,indent=2))
 (ROOT/'data/financial_data/valuation_assumptions.json').write_text(json.dumps(dict(valuation_date='2026-09-18',units='USD millions',shares=SHARES,claims=CLAIMS,dcf=SCENARIOS,earnings_cases=cases),indent=2))
 print(json.dumps(multiple,indent=2));print(pd.DataFrame(summary).round(3).to_string(index=False));print(pd.DataFrame(scenarios)[['scenario','fy2027_va','ebitda','eps','fcff','price','price_return']].round(3).to_string(index=False))
if __name__=='__main__':build()
