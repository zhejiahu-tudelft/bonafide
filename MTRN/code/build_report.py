"""Assemble one self-contained research artifact from audited, frozen inputs."""
from pathlib import Path
import sys, json, re
from html import escape
import pandas as pd
import markdown
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from common.code.report_tools import table, embedded_chart, number as n, percent as pct
from config import ROOT, CUTOFF, PRICE
from source_audit import catalog
from valuation import SCENARIOS
D=ROOT/'data/processed_data'

def read(name): return pd.read_csv(D/(name+'.csv'))

def interactive(base,v):
    last=base.iloc[-1]
    data=dict(cashflows=base.fcff.tolist(),lastVA=float(last.va_sales),margin=float(last.ebitda_margin),
              tax=float(last.tax_rate),da=.062,capex=.078,nwc=.30,claims=v['net_claims_dcf'],shares=v['dcf_diluted_shares'])
    return '''<div class="interactive"><h3>Explore the base DCF</h3>
<p>Change the discount rate and terminal growth while holding the five-year operating forecast fixed. Terminal working capital adjusts with growth.</p>
<label for="wacc">WACC <output id="wacc-label">10.5%</output></label>
<input id="wacc" type="range" min="8.5" max="12.5" step="0.1" value="10.5">
<label for="growth">Terminal growth <output id="growth-label">3.0%</output></label>
<input id="growth" type="range" min="2" max="4" step="0.1" value="3">
<p class="dcf-result"><output id="dcf-value">$98.17</output> <span>per diluted share</span></p>
<p class="caption">Analyst sensitivity, not a live quote. Static base case remains visible without JavaScript.</p></div>
<script id="dcf-inputs" type="application/json">'''+json.dumps(data)+'''</script>
<script>
(()=>{
 const d=JSON.parse(document.getElementById('dcf-inputs').textContent);
 const w=document.getElementById('wacc'),g=document.getElementById('growth');
 function refresh(){
  const W=Number(w.value)/100,G=Number(g.value)/100;
  const terminal=d.lastVA*(1+G)*((d.margin-d.da)*(1-d.tax)+d.da-d.capex)-d.lastVA*G*d.nwc;
  const explicit=d.cashflows.reduce((total,cf,i)=>total+cf/Math.pow(1+W,i+1),0);
  const result=(explicit+terminal/(W-G)/Math.pow(1+W,d.cashflows.length)-d.claims)/d.shares;
  document.getElementById('wacc-label').textContent=Number(w.value).toFixed(1)+'%';
  document.getElementById('growth-label').textContent=Number(g.value).toFixed(1)+'%';
  document.getElementById('dcf-value').textContent='$'+result.toFixed(2);
 }
 w.addEventListener('input',refresh);g.addEventListener('input',refresh);refresh();
})();
</script>'''

def build():
    h=read('financial_history').set_index('period');t=h.loc['TTM'];v=json.loads((D/'valuation_summary.json').read_text())
    st=json.loads((D/'stock_summary.json').read_text());opts=json.loads((D/'options_conclusion.json').read_text())
    tokens={}
    tokens['SNAPSHOT']=table(['Cutoff snapshot','Value','Basis'],[
        ['Closing price',f'${PRICE:.2f}',CUTOFF],['Common-equity market value',f'${v["market_cap"]:,.0f}m','20.834m actual shares'],
        ['Standard enterprise value',f'${v["ev_standard"]:,.0f}m','Debt and finance leases less cash'],
        ['Trailing revenue / VA sales',f'${t.revenue:,.0f}m / ${t.va_sales:,.0f}m','371-day reported trailing period'],
        ['Trailing adjusted EBITDA / FCF',f'${t.adjusted_ebitda:,.1f}m / ${t.fcf:,.1f}m','FCF includes mine development'],
        ['2026 adjusted EPS guidance','$6.80–$7.20','Management, August 5, 2026'],
        ['Valuation view','Cautious at $251.53','Analyst interpretation'],
        ['Options strategy eligibility',str(opts['usable_contracts'])+' usable contracts','Conservative liquidity and activity screen']])
    tokens['SEGMENTS']=table(['Segment','What customers buy','Q2 VA sales','VA share','Adjusted EBITDA / VA'],[
        ['Performance Materials','Beryllium, alloys, composites, ceramics and precision strip','$190.0m',pct(190.001/308.188),'25.4%'],
        ['Electronic Materials','Deposition targets, high-purity materials, chemicals and packaging','$87.4m',pct(87.446/308.188),'32.0%'],
        ['Precision Optics','Thin-film filters, coatings and optical components','$30.7m',pct(30.741/308.188),'21.4%']],
        'Reported Q2 2026 segment measures. Corporate costs are excluded from segment EBITDA margins.')
    years=['2021','2022','2023','2024','2025','TTM']
    rows=[]
    metrics=[('revenue','GAAP revenue',n),('va_sales','Value-added sales',n),('gross_profit','Gross profit',n),
        ('gross_margin','Gross margin / GAAP revenue',pct),('operating_income','Operating income',n),('operating_margin','Operating margin',pct),
        ('ebitda','Calculated EBITDA',n),('adjusted_ebitda','Company adjusted EBITDA',n),('adjusted_ebitda_margin_va','Adjusted EBITDA / VA',pct),
        ('net_income','Net income',n),('net_margin','Net margin',pct),('eps','Diluted EPS ($)',lambda x:n(x,2)),
        ('cfo','Operating cash flow',n),('ppe_capex','Equipment capex',n),('mine_capex','Separately reported mine development',n),
        ('fcf','FCF after both spending categories',n),('fcf_margin','FCF / revenue',pct),('fcf_conversion','FCF / net income',pct),
        ('da','Depreciation, depletion and amortization',n),('amortization','Intangible amortization (within D&A)',n),('sbc','SBC (expense; included in earnings)',n)]
    for key,label,fmt in metrics: rows.append([label]+[fmt(h.loc[y,key]) for y in years])
    rows.insert(1,['Revenue growth, fiscal year']+['—']+[pct(h.loc[str(y),'revenue']/h.loc[str(y-1),'revenue']-1) for y in range(2022,2026)]+['n/a: unequal trailing period'])
    tokens['HISTORICAL']=table(['USD millions except ratios / EPS']+years,rows)
    quarterly=[('GAAP revenue',431.658,613.906),('Pass-through metal costs',162.688,305.718),('Value-added sales',268.970,308.188),
               ('Gross profit',82.658,104.342),('Operating income',36.819,51.711),('Net income',25.140,38.758),
               ('Adjusted EBITDA',55.8,71.8),('FCF after mine development',35.7,58.7),('Diluted EPS ($)',1.21,1.84),('Adjusted EPS ($)',1.37,1.90)]
    tokens['LATEST']=table(['Q2 comparison','2025','2026','Change'],[[label,n(a,2 if 'EPS' in label else 1),n(b,2 if 'EPS' in label else 1),pct(b/a-1)] for label,a,b in quarterly])
    bm=[('cash','Cash',n),('debt','Debt carrying value',n),('net_debt','Net debt',n),('assets','Total assets',n),('current_assets','Current assets',n),
        ('inventory','Inventory',n),('receivables','Receivables',n),('current_liabilities','Current liabilities',n),('equity','Common equity',n),
        ('goodwill','Goodwill',n),('intangibles','Net intangible assets',n),('current_ratio','Current ratio',lambda x:n(x,2,'×')),
        ('debt_equity','Debt / equity',lambda x:n(x,2,'×')),('interest_cover','EBIT / interest',lambda x:n(x,1,'×'))]
    tokens['BALANCE']=table(['USD millions except ratios','FY2024','FY2025','July 3, 2026'],[[label]+[fmt(h.loc[y,key]) for y in ['2024','2025','TTM']] for key,label,fmt in bm])
    tokens['DILUTION']=table(['Measure']+years,[[label]+[fmt(h.loc[y,key]) for y in years] for key,label,fmt in [
        ('actual_shares','Actual period-end shares (m)',lambda x:n(x,3)),('diluted_shares','Weighted diluted shares (m)',lambda x:n(x,3)),
        ('sbc','SBC ($m)',n),('sbc_revenue','SBC / GAAP revenue',pct),('fcf_per_share','FCF / diluted share ($)',lambda x:n(x,2)),
        ('dividends','Cash dividends paid ($m)',n),('repurchases','Repurchases ($m)',n)]])
    p=read('peers').set_index('ticker')
    peers=['MTRN']+list(p.index)
    pm=[('period','Fiscal basis',None),('revenue','Revenue ($m)',n),('gross_margin','Gross margin',pct),('operating_margin','Operating margin',pct),
        ('fcf','FCF ($m)',n),('net_debt','Net debt ($m)',n),('pe','Trailing GAAP P/E',lambda x:n(x,1,'×')),('ps','Price / sales',lambda x:n(x,1,'×')),
        ('pb','Price / book',lambda x:n(x,1,'×')),('ev_revenue','EV / revenue',lambda x:n(x,1,'×')),('ev_ebitda_operating','EV / operating EBITDA',lambda x:n(x,1,'×')),
        ('ev_adjusted_ebitda','EV / adjusted EBITDA',lambda x:n(x,1,'×')),('fcf_yield','FCF yield',pct)]
    own=dict(revenue=t.revenue,gross_margin=t.gross_margin,operating_margin=t.operating_margin,fcf=t.fcf,net_debt=t.net_debt,
             pe=v['pe_ttm_gaap'],ps=v['ps'],pb=v['pb'],ev_revenue=v['ev_revenue'],ev_ebitda_operating=v['ev_operating_ebitda'],
             ev_adjusted_ebitda=v['ev_adjusted_ebitda'],fcf_yield=v['fcf_yield'])
    pr=[['Fiscal basis','TTM July 3, 2026','TTM June 27, 2026','FY June 30, 2026','TTM June 28, 2026']]
    pr += [[label,fmt(own[key])]+[fmt(p.loc[tk,key]) for tk in p.index] for key,label,fmt in pm[1:]]
    tokens['PEERS']=table(['Metric']+peers,pr,'Gross-revenue margins are affected by differing metal pass-through. Peer EV uses disclosed debt less cash; MTRN also includes finance leases. A dash means no comparable adjusted figure was used.')
    multiples=[('pe_ttm_gaap','Trailing GAAP P/E'),('pe_2026_guidance_mid','2026 guidance midpoint adjusted P/E'),('ps','Price / trailing revenue'),
               ('pb','Price / book'),('ev_revenue','EV / revenue'),('ev_va_sales','EV / value-added sales'),('ev_ebitda','EV / calculated EBITDA'),
               ('ev_adjusted_ebitda','EV / adjusted EBITDA')]
    tokens['MULTIPLES']=table(['Current valuation','Calculated multiple'],[[label,n(v[key],1,'×')] for key,label in multiples]+[['Trailing FCF yield',pct(v['fcf_yield'],2)],['Annualized dividend yield',pct(v['dividend_yield'],2)]])
    base=read('dcf_base')
    tokens['DCF_FORECAST']=table(['Base prospective year end','VA sales','Growth','EBITDA / VA','EBIT','Total capex','Δ working capital','FCFF'],[
        [r.period_end,n(r.va_sales),pct(r.growth),pct(r.ebitda_margin),n(r.ebit),n(r.capex),n(r.change_nwc),n(r.fcff)] for _,r in base.iterrows()])
    ds=read('dcf_summary')
    tokens['DCF_RESULTS']=table(['DCF scenario','WACC','Terminal growth','Enterprise value','Net claims','Equity value','Diluted shares','Value / share','vs. cutoff price'],[
        [r.scenario,pct(r.wacc),pct(r.g),n(r.enterprise),n(v['net_claims_dcf']),n(r.equity),n(v['dcf_diluted_shares'],2),'$'+n(r.per_share,2),pct(r.return_vs_price)] for _,r in ds.iterrows()])
    tokens['DCF_RESULTS']+=table(['DCF operating assumptions','Downside','Base','Upside'],[
        ['Five annual VA growth rates']+[' / '.join(pct(x,1) for x in c['growth']) for c in SCENARIOS.values()],
        ['EBITDA / VA, first → final year']+[pct(c['ebitda_margin'][0])+' → '+pct(c['ebitda_margin'][-1]) for c in SCENARIOS.values()],
        ['D&A / VA']+[pct(c['da_ratio']) for c in SCENARIOS.values()],['Capex / VA']+[pct(c['capex_ratio']) for c in SCENARIOS.values()],
        ['NWC / incremental VA']+[pct(c['nwc_ratio']) for c in SCENARIOS.values()],
        ['Tax rate, first → final year']+[pct(c['tax'][0])+' → '+pct(c['tax'][-1]) for c in SCENARIOS.values()]])
    sc=read('fundamental_scenarios').set_index('scenario')
    sm=[('fy2027_va','FY2027 VA sales ($m)',n),('revenue','Illustrative GAAP revenue ($m)',n),('growth','VA / revenue growth',pct),
        ('gross_margin_va','Gross profit / VA',pct),('gross_margin_gaap','GAAP gross margin',pct),('ebitda_margin_va','EBITDA / VA',pct),
        ('operating_margin_gaap','GAAP operating margin',pct),('capex','Total capex ($m)',n),('change_nwc','Incremental NWC ($m)',n),
        ('fcff','Unlevered FCFF ($m)',n),('normalized_equity_fcf','Normalized equity FCF ($m)',n),('eps','Adjusted EPS ($)',lambda x:n(x,2)),
        ('assumed_pe','Assumed P/E',lambda x:n(x,0,'×')),('price','12-month price scenario ($)',lambda x:n(x,2)),('price_return','Price return from cutoff',pct)]
    tokens['SCENARIOS']=table(['Analyst estimate']+list(sc.index),[[label]+[fmt(sc.loc[s,key]) for s in sc.index] for key,label,fmt in sm],
                            'Dividends excluded from price returns. Adjusted EPS adds back $10m acquisition amortization before tax; equity FCF deducts after-tax interest from FCFF.')
    ret=read('stock_returns');ret=ret[ret.ticker!='VNP.TO']
    windows=['1M','3M','YTD','1Y','3Y','5Y']
    tokens['RETURNS']=table(['USD return proxy']+windows,[[r.ticker]+[pct(r[x]) for x in windows] for _,r in ret.iterrows()])
    technical=[('sma20','20-day average',lambda x:'$'+n(x,2)),('sma50','50-day average',lambda x:'$'+n(x,2)),('sma200','200-day average',lambda x:'$'+n(x,2)),
        ('ema12','12-day EMA',lambda x:'$'+n(x,2)),('ema26','26-day EMA',lambda x:'$'+n(x,2)),('rsi14','14-day RSI',n),
        ('bb_lower','Lower 20-day Bollinger band',lambda x:'$'+n(x,2)),('bb_upper','Upper 20-day Bollinger band',lambda x:'$'+n(x,2)),
        ('vol21','21-session annualized volatility',pct),('vol63','63-session annualized volatility',pct),('vol252','252-session annualized volatility',pct),
        ('volume','Latest volume',lambda x:n(x,0)),('volume_ratio','Volume / previous 50-session average',lambda x:n(x,2,'×'))]
    tokens['TECHNICALS']=table(['September 18 indicator','Calculated value'],[[label,fmt(st[key])] for key,label,fmt in technical])
    ev=read('events')
    tokens['EVENTS']=table(['Date','Reviewed context','Event day','Next day','3 sessions','5 sessions','5-session excess vs. SPY'],[
        [r['date'],r['event']]+[pct(r[x]) for x in ['return_1d','next_day','return_3d','return_5d','excess_spy_5d']] for _,r in ev.iterrows()])
    os=read('options_summary');os=os[os.days>0]
    tokens['OPTIONS_SUMMARY']=table(['Expiry','Days','Listed contracts','Call / put volume','Call / put OI','Put/call OI','Indicative ATM IV','Legs passing screen'],[
        [r.expiration,int(r.days),int(r.contracts),f'{r.call_volume:.0f} / {r.put_volume:.0f}',f'{r.call_oi:.0f} / {r.put_oi:.0f}',n(r.put_call_oi,2),pct(r.atm_iv),int(r.usable)] for _,r in os.iterrows()],
        'Near-ATM IV is the median of vendor put/call indications at the closest strike; observations are not validated executable prices.')
    oq=read('options_near_spot');oq=oq[(oq.expiration=='2026-10-16') & (oq.strike.isin([240,250,260]))]
    tokens['OPTIONS_QUOTES']=table(['October 16 contract','Bid','Ask','Spread / mid','Volume','OI','Vendor IV','Last trade'],[
        [f'${r.strike:.0f} {r.type}',n(r.bid,2),n(r.ask,2),pct(r.spread_pct),int(r.volume),int(r.open_interest),pct(r.iv),str(r.last_trade_timestamp) if pd.notna(r.last_trade_timestamp) else 'Unavailable'] for _,r in oq.iterrows()],
        'Premiums in USD per share; standard contract multiplier 100. These are observed quotes only; no strategy is recommended from them.')
    tokens['INTERACTIVE']=interactive(base,v)
    chart_descriptions={
        'segment_mix':'Q2 2026 value-added sales and segment adjusted EBITDA margins.',
        'financial_trends':'Five full fiscal years and a 371-day trailing calculation. FCF includes equipment and mine development.',
        'relative_returns':'Five-year dividend-adjusted price comparison from the saved daily histories.',
        'price_action':'Daily close, moving averages, Bollinger range, and RSI through September 18, 2026.',
        'valuation_scenarios':'DCF and earnings-multiple scenarios are separate analytical approaches.',
        'dcf_sensitivity':'Per-share value as discount rate and terminal growth change; base operations fixed.'}
    for name,desc in chart_descriptions.items(): tokens['CHART_'+name]=embedded_chart(D/'charts'/f'{name}.png',desc)
    sources=catalog();source_rows=[]
    for i,(key,s) in enumerate(sources.items(),1):
        tokens[key]=f'<a class="citation" href="{escape(s["url"],quote=True)}" title="{escape(s["title"],quote=True)}">[{i}]</a>'
        source_rows.append(f'<tr><td>{i}</td><td><a href="{escape(s["url"],quote=True)}">{escape(s["title"])}</a></td><td>{escape(s["publisher"])}</td><td>{escape(str(s["date"]))}</td><td><a href="../{escape(s["local"],quote=True)}">Archived evidence</a></td></tr>')
    tokens['SOURCES']='<h3>Principal sources and local evidence</h3><p>Accessed September 19, 2026. Economic disclosures used were available by September 18. The Cboe file carries the later vendor timestamp described in Section 14; its underlying session matches the cutoff. Live web pages may subsequently change; use the archived evidence for this report.</p><div class="table-wrap"><table><thead><tr><th>Ref.</th><th>Original source</th><th>Publisher</th><th>Publication / snapshot</th><th>Archive</th></tr></thead><tbody>'+''.join(source_rows)+'</tbody></table></div><p>Full inventory: <a href="../report/source_log.csv">source log</a>, <a href="../data/processed_data/manual_input_audit.csv">manual financial selections</a>, <a href="../data/processed_data/evidence_inventory.csv">file hashes</a>, and <a href="../data/processed_data/retrieval_outcomes.csv">retrieval outcomes</a>. The image-based 2023 investor deck also has preserved web-extracted text in <a href="../report/other_evidence/event_and_historical_research_web.txt">historical/event evidence</a>.</p>'
    template=(ROOT/'code/research_template.md').read_text()
    used=set(re.findall(r'\{\{([A-Z_a-z0-9]+)\}\}',template));missing=used-set(tokens)
    if missing: raise ValueError(f'Unfilled report fields: {missing}')
    rendered=re.sub(r'\{\{([A-Z_a-z0-9]+)\}\}',lambda m:tokens[m[1]],template)
    md=markdown.Markdown(extensions=['tables','toc','fenced_code'],extension_configs={'toc':{'toc_depth':'2'}})
    body=md.convert(rendered)
    css=(ROOT/'code/report.css').read_text()
    html='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Materion (MTRN) — Investment Research — September 18, 2026</title><style>'+css+'</style></head><body><aside class="sidebar"><div class="brand">MTRN <span>Research</span></div><p class="nav-date">As of September 18, 2026</p><nav aria-label="Report sections">'+md.toc+'</nav><p class="nav-footer">USD · NYSE<br>Frozen research snapshot</p></aside><main>'+body+'</main></body></html>'
    destination=ROOT/'final/MTRN_Investment_Research.html';destination.parent.mkdir(exist_ok=True)
    destination.write_text(html)
    print(f'{destination} ({destination.stat().st_size:,} bytes; {len(used)} populated fields)')

if __name__=='__main__': build()
