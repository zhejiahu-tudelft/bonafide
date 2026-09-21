"""Workbook table formatting with explicit missing data and formula caches."""
import math
def formats(wb):
 return { 'head':wb.add_format({'bold':True,'bg_color':'#142b45','font_color':'white','text_wrap':True}),
  'num':wb.add_format({'num_format':'#,##0.0;[Red](#,##0.0)'}),
  'input':wb.add_format({'num_format':'#,##0.0','font_color':'#1769aa','bg_color':'#eff7fb'}),
  'input_pct':wb.add_format({'num_format':'0.0%','font_color':'#1769aa','bg_color':'#eff7fb'}),
  'input_shares':wb.add_format({'num_format':'0.000','font_color':'#1769aa','bg_color':'#eff7fb'}),
  'pct':wb.add_format({'num_format':'0.0%'}),
  'money':wb.add_format({'num_format':'$0.00'}),
  'note':wb.add_format({'text_wrap':True,'valign':'top','font_color':'#555555'}),
  'title':wb.add_format({'bold':True,'font_size':18,'font_color':'#142b45'})}
def write_frame(wb,name,frame,fmt):
 ws=wb.add_worksheet(name);ws.freeze_panes(1,1);ws.autofilter(0,0,len(frame),len(frame.columns)-1)
 for j,c in enumerate(frame.columns):ws.write(0,j,str(c),fmt['head'])
 for i,row in enumerate(frame.itertuples(index=False,name=None),1):
  for j,v in enumerate(row):
   if v is None or (isinstance(v,float) and not math.isfinite(v)):ws.write(i,j,'Data unavailable')
   elif isinstance(v,(int,float)):
    col=str(frame.columns[j]); percentage=('margin' in col or col.endswith('_yield') or col.startswith('return_') or col.startswith('excess_') or col in ['growth','wacc','g','price_return','tax','tax_rate','sbc_revenue','fcf_conversion','spread_pct','iv','atm_iv','nwc_ratio','terminal_share','return_vs_price','1M','3M','YTD','1Y','3Y','5Y','5Y_vol','5Y_max_drawdown'])
    ws.write_number(i,j,v,fmt['pct'] if percentage else fmt['num'])
   else:ws.write(i,j,str(v))
 ws.set_column(0,0,24);ws.set_column(1,len(frame.columns)-1,17);ws.set_row(0,32)
 return ws
