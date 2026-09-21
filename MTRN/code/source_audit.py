"""Connect manual selections and archived evidence to their original sources."""
from pathlib import Path
import json, hashlib
import pandas as pd
from config import ROOT, CUTOFF, PREPARED

EXTRA = {
 'CPI': ('August 2026 CPI', 'BLS', '2026-09-11', 'https://www.bls.gov/news.release/archives/cpi_09112026.htm', 'report/macro_research/BLS_Treasury_web_extract.txt'),
 'RATE': ('Daily Treasury yields, September 18, 2026', 'US Treasury', CUTOFF, 'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve&field_tdr_date_value=2026', 'report/macro_research/BLS_Treasury_web_extract.txt'),
 'E22EVENT': ('Q3 2022 results', 'Materion', '2022-11-02', 'https://investor.materion.com/news/news-details/2022/Materion-Corporation-Reports-Record-Third-Quarter-Results-and-Updates-Full-Year-2022-Outlook/default.aspx', 'report/other_evidence/event_and_historical_research_web.txt'),
 'E23EVENT': ('FY2022 earnings 8-K', 'Materion / SEC', '2023-02-16', 'https://www.sec.gov/Archives/edgar/data/1104657/000110465723000015/mtrn-20230216.htm', 'report/other_evidence/event_and_historical_research_web.txt'),
 'EVENT25': ('Q3 2025 earnings event calendar', 'Materion', '2025-10-29', 'https://investor.materion.com/events-and-presentations/event-details/2025/Materion-Corporation-Third-Quarter-2025/default.aspx', 'report/other_evidence/event_and_historical_research_web.txt'),
}
FILES = {
 'E25':'FY2025_release.htm','E26':'Q2_2026_release.htm',
 'DECK26':'Q2_2026_presentation.pdf','HISTDECK':'Investor_2023.htm','DECK23':'Q4_2023_presentation.pdf',
 'USGS':'USGS_mcs2026.pdf','SIA':'SIA_July_2026.html','CFS':'Materion_CFS_agreement.html',
 'FED':'FOMC_20260916.html','ENTG':'ENTG_Q2_2026.htm','CRS':'CRS_FY2026.htm',
 'VNP':'VNP_Q2_2026.html','PRICE':'stockanalysis_history.html','CBOE':'cboe_raw.json',
}

def catalog():
    log = pd.read_csv(ROOT/'report/source_log.csv').fillna('')
    result = {}
    filings=json.loads((ROOT/'data/financial_data/filing_index.json').read_text())
    for x in filings:
        key = 'K'+x['report_date'][2:4] if x['form']=='10-K' else (
            'Q26' if x['report_date']=='2026-07-03' and x['form']=='10-Q' else (
            'PROXY' if x['form']=='DEF 14A' else None))
        if key:
            result[key]=dict(title=f"Materion {x['form']} — {x['report_date']}",publisher='Materion / SEC',
                             date=x['filing_date'],url=x['url'],local=x['local'])
    for key,filename in FILES.items():
        row=log.loc[log.local_path.map(lambda x:Path(x).name)==filename].iloc[-1]
        result[key]=dict(title=row.title,publisher=row.publisher,date=row.pub_date,url=row.url,local=row.local_path)
    for key,(title,pub,date,url,local) in EXTRA.items():
        result[key]=dict(title=title,publisher=pub,date=date,url=url,local=local)
    return result

def build():
    logpath=ROOT/'report/source_log.csv'
    log=pd.read_csv(logpath).fillna('')
    for key,(title,publisher,date,url,local) in EXTRA.items():
        if url in log.url.values: continue
        row=dict(id=f'S{len(log)+1:03d}',category=Path(local).parent.name,source=publisher,title=title,
                 publisher=publisher,pub_date=date,retrieved=PREPARED,url=url,local_path=local,
                 forecast_period='',key_data='Official-source web extract; see archived text',
                 relevance='Macro input or verified event date',source_type='primary web extract')
        log=pd.concat([log,pd.DataFrame([row])],ignore_index=True)
    log.loc[log.publisher.isin(['Stock Analysis','ChartExchange','MarketBeat']),'source_type']='secondary aggregator'
    log.to_csv(logpath,index=False)
    sources=catalog()
    (ROOT/'data/processed_data/citation_catalog.json').write_text(json.dumps(sources,indent=2))
    h=pd.read_csv(ROOT/'data/processed_data/financial_history.csv',index_col='period')
    manual=[]
    def add(metric,period,value,key,locator,kind='reported'):
        manual.append(dict(metric=metric,period=period,value=value,unit='USD millions unless noted',
                           classification=kind,source_key=key,source_url=sources[key]['url'],
                           local_path=sources[key]['local'],locator=locator))
    for y in ['2021','2022','2023','2024','2025','H1 2025','H1 2026','TTM']:
        va_source='K23' if y in ['2021','2022','2023'] else ('K25' if y in ['2024','2025'] else 'Q26')
        if y!='TTM': add('value_added_sales',y,h.loc[y,'va_sales'],va_source,'MD&A, net sales / pass-through reconciliation')
        key='HISTDECK' if y in ['2021','2022'] else ('K23' if y=='2023' else ('E25' if y in ['2024','2025'] else 'E26'))
        if y=='2023':
            # Non-GAAP figure is in the retained Q4 2023 presentation.
            add('adjusted_ebitda',y,h.loc[y,'adjusted_ebitda'],'DECK23','Adjusted EBITDA reconciliation')
        else: add('adjusted_ebitda',y,h.loc[y,'adjusted_ebitda'],'DECK26' if y=='TTM' else key,'EBITDA reconciliation; TTM slide 16; historical 2023 investor deck slide 22')
    for y in ['2021','2022','2023','2024','2025']:
        add('separately_reported_mine_development',y,h.loc[y,'mine_capex'],'K'+y[2:] if int(y)<2023 else 'K25','Consolidated cash-flow statement; zero means no separately reported line')
    for metric,value,key,location,kind in [
        ('debt_principal',442.332,'Q26','Debt note','reported'),
        ('finance_lease_total',13.3,'Q26','12.671 noncurrent plus estimated current amount from FY2025','analyst estimate'),
        ('retirement_liability',23.155,'Q26','Balance sheet','reported'),
        ('actual_common_shares_million',20.834,'Q26','Statement of shareholders equity','reported'),
        ('prospective_diluted_shares_million',21.15,'Q26','Analyst assumption above Q2 weighted average 21.075','analyst assumption'),
        ('FY2026_adjusted_EPS_midpoint_USD',7.0,'E26','Guidance range 6.80 to 7.20','calculated'),
        ('FY2026_total_capex_planning_anchor',100.0,'DECK26','75 equipment + 25 mine development; 10-Q wording discrepancy retained','reported / planning interpretation'),
        ('FY2026_VA_growth_anchor_percent',15.0,'E26','Mid-teens guidance interpreted as 15%','analyst interpretation'),
    ]: add(metric,'latest / forecast',value,key,location,kind)
    pd.DataFrame(manual).to_csv(ROOT/'data/processed_data/manual_input_audit.csv',index=False)
    inventory=[]
    for directory in ['report','data/financial_data','data/market_data','data/options_data']:
        for path in sorted((ROOT/directory).rglob('*')):
            if not path.is_file() or path.name=='source_log.csv': continue
            inventory.append(dict(local_path=str(path.relative_to(ROOT)),bytes=path.stat().st_size,
                                  sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    pd.DataFrame(inventory).to_csv(ROOT/'data/processed_data/evidence_inventory.csv',index=False)
    outcomes=[]
    for item in json.loads((ROOT/'data/source_manifest.json').read_text()):
        p=ROOT/'report'/item['category']/item['filename']
        status='archived' if p.exists() else 'direct download unavailable'
        fallback='BLS_Treasury_web_extract.txt' if item['filename'] in ['CPI_202608.html','CPI_202608.pdf','Treasury_yields_2026.html'] else ('TNX_daily.csv yield proxy used' if item['filename']=='DGS10.csv' else '')
        outcomes.append(dict(filename=item['filename'],url=item['url'],status=status,fallback=fallback))
    pd.DataFrame(outcomes).to_csv(ROOT/'data/processed_data/retrieval_outcomes.csv',index=False)
    print(f'Audited {len(log)} source entries and {len(inventory)} evidence files.')

if __name__=='__main__': build()
