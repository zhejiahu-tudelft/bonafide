"""Formula-driven Excel model with independently calculated cached results."""
from pathlib import Path
import sys,json
import pandas as pd,numpy as np
import xlsxwriter
from xlsxwriter.utility import xl_col_to_name
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from common.code.workbook_tools import formats,write_frame
from valuation import SCENARIOS,SHARES,CLAIMS,terminal_fcff
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'data/processed_data'
def build():
 path=ROOT/'excel/MTRN_Research_Model.xlsx';wb=xlsxwriter.Workbook(path);fm=formats(wb)
 wb.set_properties({'title':'Materion investment research model','subject':'As of 18 September 2026','author':'Fundamental equity research'})
 ws=wb.add_worksheet('Read me');ws.set_column('A:A',28);ws.set_column('B:B',110)
 notes=[('Valuation date','18 September 2026; USD millions except per-share data and explicit percentages.'),
 ('Inputs','Blue cells are analyst assumptions. Financial facts are linked by accession and tag in Financial audit.'),
 ('Historical TTM','FY2025 + H1 2026 - H1 2025. Reported cutoffs create a 371-day trailing period. Interim shares weighted by day count.'),
 ('Value-added sales','2021 and 2022 use the comparable recast figures disclosed in the FY2023 10-K. These differ from originally published VA sales.'),
 ('FCF','Operating cash flow less PPE spending AND separately reported mine-development spending. Excludes acquisitions. Annual mining outflows: zero separately reported in 2021-22, $9.326m in 2023, $12.159m in 2024, $26.288m in 2025.'),
 ('Adjusted EBITDA','Company-reported non-GAAP metric; 2021-22 from 2023 investor deck; 2023 from Q4 deck; 2024-25 from FY2025 release; TTM 237.2 from Q2 2026 slide 16.'),
 ('DCF periods','Five prospective 12-month years ending September 18, 2027-2031; year-end discounting; terminal reinvestment reset to terminal growth.'),
 ('Balance-sheet bridge','Debt principal + estimated finance leases + retirement liability - cash. Operating lease expense remains in operating forecasts.'),
 ('Share count','20.834m latest balance-sheet common shares for market cap; 21.15m prospective diluted shares for DCF and earnings scenarios.'),
 ('Capital spending','Q2 deck: $75m PPE plus $25m mine development. Q2 10-Q prose says $100m PPE. Disclosure discrepancy retained in report; $100m total base anchor and $125m downside cash sensitivity.'),
 ('Model status','Formulas include cached numerical values verified against Python; formulas recalculate when changed in Excel. Scenario and DCF assumptions are analyst estimates.'),
 ('Options','Saved real Cboe quotes; no strategies or calculated Greeks because liquidity screen failed. Vendor Greeks remain identified as vendor values.'),
 ('Peer limits','ENTG, CRS, ATI are adjacent valuation references, not identical operating competitors. Peer market caps use latest available diluted weighted-average shares.'),
 ('Rebuild','Run python MTRN/code/run_analysis.py from repository root after installing MTRN/code/requirements.txt.')]
 for i,(a,b) in enumerate(notes):ws.write(i,0,a,fm['head']);ws.write(i,1,b,fm['note']);ws.set_row(i,42)
 h=pd.read_csv(D/'financial_history.csv').fillna(np.nan);hs=write_frame(wb,'Historical',h,fm)
 ci={c:xl_col_to_name(i) for i,c in enumerate(h.columns)}
 derived={'capex':'{ppe_capex}+{mine_capex}','fcf':'{cfo}-{capex}','debt':'{debt_current}+{debt_noncurrent}',
  'net_debt':'{debt}-{cash}','ebitda':'{net_income}+{tax}+{interest}+{da}','operating_ebitda':'{operating_income}+{da}',
  'gross_margin':'{gross_profit}/{revenue}','gross_margin_va':'{gross_profit}/{va_sales}','operating_margin':'{operating_income}/{revenue}',
  'net_margin':'{net_income}/{revenue}','fcf_margin':'{fcf}/{revenue}','sbc_revenue':'{sbc}/{revenue}',
  'current_ratio':'{current_assets}/{current_liabilities}','debt_equity':'{debt}/{equity}','actual_shares':'{shares_issued}-{treasury_shares}',
  'interest_cover':'{operating_income}/{interest}','fcf_per_share':'{fcf}/{diluted_shares}','fcf_conversion':'{fcf}/{net_income}',
  'adjusted_ebitda_margin_va':'{adjusted_ebitda}/{va_sales}'}
 for i,row in h.iterrows():
  cells={c:f'{letter}{i+2}' for c,letter in ci.items()}
  for name,expr in derived.items():hs.write_formula(i+1,h.columns.get_loc(name),'='+expr.format(**cells),fm['pct'] if 'margin' in name or name in ['sbc_revenue','fcf_conversion'] else fm['num'],float(row[name]))
 v=json.loads((D/'valuation_summary.json').read_text());initial=1046.194*1.15
 summary=pd.read_csv(D/'dcf_summary.csv').set_index('scenario')
 for name,cfg in SCENARIOS.items():
  f=pd.read_csv(D/f'dcf_{name.lower()}.csv');ws=wb.add_worksheet('DCF '+name);ws.set_column('A:A',34);ws.set_column('B:F',17);ws.freeze_panes(4,1)
  ws.write(0,0,'Prospective DCF — '+name,fm['title']);ws.write(1,0,'FY2026 VA anchor');ws.write(1,1,initial,fm['input'])
  labels={3:'Prospective year',4:'VA sales growth',5:'Value-added sales',6:'EBITDA / VA sales',7:'EBITDA',8:'D&A / VA sales',9:'D&A',10:'EBIT',11:'Tax rate',12:'NOPAT',13:'Capex / VA sales',14:'Capex incl. mining',15:'NWC / incremental VA',16:'Change in NWC',17:'FCFF',18:'Present value of FCFF',20:'WACC',21:'Terminal growth',22:'Diluted shares',23:'Net claims',25:'Terminal VA sales',26:'Terminal EBITDA',27:'Terminal D&A',28:'Terminal EBIT',29:'Terminal capex',30:'Terminal change NWC',31:'Terminal FCFF',32:'Terminal value',33:'PV of terminal value',34:'PV explicit cash flows',35:'Enterprise value',36:'Equity value',37:'Per-share value',38:'Terminal share of EV'}
  for i,label in labels.items():ws.write(i,0,label,fm['head'] if i in [3,17,35,37] else None)
  for r,val in [(20,cfg['wacc']),(21,cfg['g']),(22,SHARES),(23,v['net_claims_dcf'])]:ws.write_number(r,1,val,fm['input_pct'] if r in [20,21] else (fm['input_shares'] if r==22 else fm['input']))
  for j,row in f.iterrows():
   c=xl_col_to_name(j+1);prev='$B$2' if j==0 else xl_col_to_name(j)+'6'
   for r,value in [(3,j+1),(4,row.growth),(6,row.ebitda_margin),(8,cfg['da_ratio']),(11,row.tax_rate),(13,cfg['capex_ratio']),(15,cfg['nwc_ratio'])]:ws.write_number(r,j+1,value,fm['input'] if r==3 else fm['input_pct'])
   form={5:(f'{prev}*(1+{c}5)',row.va_sales),7:(f'{c}6*{c}7',row.ebitda),9:(f'{c}6*{c}9',row.da),10:(f'{c}8-{c}10',row.ebit),12:(f'{c}11*(1-{c}12)',row.ebit*(1-row.tax_rate)),14:(f'{c}6*{c}14',row.capex),16:(f'({c}6-{prev})*{c}16',row.change_nwc),17:(f'{c}13+{c}10-{c}15-{c}17',row.fcff),18:(f'{c}18/(1+$B$21)^{c}4',row.fcff/(1+cfg['wacc'])**(j+1))}
   for r,(expr,value) in form.items():ws.write_formula(r,j+1,'='+expr,fm['num'],value)
  last=f.iloc[-1];tv=last.va_sales*(1+cfg['g']);sr=summary.loc[name]
  vals={25:('F6*(1+B22)',tv),26:('B26*F7',tv*last.ebitda_margin),27:('B26*F9',tv*cfg['da_ratio']),28:('B27-B28',tv*(last.ebitda_margin-cfg['da_ratio'])),29:('B26*F14',tv*cfg['capex_ratio']),30:('F6*B22*F16',last.va_sales*cfg['g']*cfg['nwc_ratio']),31:('B29*(1-F12)+B28-B30-B31',sr.terminal_fcff),32:('B32/(B21-B22)',sr.terminal_fcff/(cfg['wacc']-cfg['g'])),33:('B33/(1+B21)^F4',sr.pv_terminal),34:('SUM(B19:F19)',sr.pv_explicit),35:('B34+B35',sr.enterprise),36:('B36-B24',sr.equity),37:('B37/B23',sr.per_share),38:('B34/B36',sr.terminal_share)}
  for r,(expr,value) in vals.items():ws.write_formula(r,1,'='+expr,fm['money'] if r==37 else (fm['pct'] if r==38 else fm['num']),value)
  ws.write(40,0,'Terminal capex and working capital are recalculated at terminal growth; SBC remains an expense.',fm['note'])
 ws=write_frame(wb,'DCF summary',summary.reset_index(),fm)
 for i,name in enumerate(summary.index):
  for label,cell in [('per_share','B38'),('enterprise','B36'),('equity','B37'),('pv_terminal','B34'),('pv_explicit','B35')]:
   col=summary.reset_index().columns.get_loc(label);ws.write_formula(i+1,col,f"='DCF {name}'!{cell}",fm['num'],float(summary.loc[name,label]))
 sen=pd.read_csv(D/'dcf_sensitivity.csv');ws=wb.add_worksheet('Sensitivity');ws.set_column('A:F',17);ws.write(0,0,'WACC / terminal g',fm['head'])
 for j,g in enumerate(sen.columns[1:],1):ws.write_number(0,j,float(g),fm['pct'])
 base=pd.read_csv(D/'dcf_base.csv')
 for i,row in sen.iterrows():
  ws.write_number(i+1,0,row.wacc,fm['pct'])
  for j,col in enumerate(sen.columns[1:],1):
   grow=f'{xl_col_to_name(j)}$1';w=f'$A{i+2}'
   explicit='+'.join(f"'DCF Base'!{xl_col_to_name(k+1)}18/(1+{w})^{k+1}" for k in range(5))
   terminal=f"('DCF Base'!F6*(1+{grow})*(('DCF Base'!F7-'DCF Base'!F9)*(1-'DCF Base'!F12)+'DCF Base'!F9-'DCF Base'!F14)-'DCF Base'!F6*{grow}*'DCF Base'!F16)"
   expr=f"=({explicit}+{terminal}/({w}-{grow})/(1+{w})^5-'DCF Base'!B24)/'DCF Base'!B23"
   ws.write_formula(i+1,j,expr,fm['money'],float(row[col]))
 sc=pd.read_csv(D/'fundamental_scenarios.csv');ss=write_frame(wb,'Earnings scenarios',sc,fm);cols={c:xl_col_to_name(i) for i,c in enumerate(sc.columns)}
 expressions={'fy2027_va':'{fy2026_va_anchor}*(1+{growth})','gross_profit':'{fy2027_va}*{gross_margin_va}','revenue':'{fy2027_va}/0.55','ebitda':'{fy2027_va}*{ebitda_margin_va}','ebit':'{ebitda}-{da}','adjusted_net_income':'({ebit}+{acquisition_amortization_addback}-{interest})*(1-{tax})','eps':'{adjusted_net_income}/21.15','price':'{eps}*{assumed_pe}','price_return':'{price}/251.53-1','fcff':'{ebit}*(1-{tax})+{da}-{capex}-{change_nwc}','normalized_equity_fcf':'{fcff}-{interest}*(1-{tax})'}
 expressions.update({'change_nwc':'({fy2027_va}-{fy2026_va_anchor})*{nwc_ratio}','gross_margin_gaap':'{gross_margin_va}*0.55','operating_margin_gaap':'{ebit}/{revenue}'})
 for i,row in sc.iterrows():
  cells={c:letter+str(i+2) for c,letter in cols.items()}
  for name,expr in expressions.items():ss.write_formula(i+1,sc.columns.get_loc(name),'='+expr.format(**cells),fm['pct'] if 'margin' in name or name=='price_return' else fm['num'],float(row[name]))
 for name,file in [('Peers','peers.csv'),('Stock returns','stock_returns.csv'),('Events','events.csv'),('Options snapshot','options_near_spot.csv'),('Options summary','options_summary.csv'),('Financial audit','financial_audit.csv')]:write_frame(wb,name,pd.read_csv(D/file),fm)
 for name,file in [('Manual input audit','manual_input_audit.csv'),('Peer financial audit','peer_financial_audit.csv')]:write_frame(wb,name,pd.read_csv(D/file),fm)
 write_frame(wb,'Sources',pd.read_csv(ROOT/'report/source_log.csv'),fm)
 wb.close();print(path)
if __name__=='__main__':build()
