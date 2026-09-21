"""Fetch Materion evidence. Run separately from the offline analytical build."""
from pathlib import Path
import sys, json, datetime as dt, argparse
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.code.fetch_company_data import Project, SEC_HEADERS, BROWSER, cached_json, download, yahoo_chart

ROOT = Path(__file__).resolve().parents[1]
END = '2026-09-18'
CIKS = {'MTRN':'0001104657', 'ENTG':'0001101302', 'CRS':'0000017843', 'ATI':'0001018963'}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--section',default='all'); a=ap.parse_args()
    p=Project(ROOT,False)
    if a.section in ('all','options'):
        from common.code.options_tools import retrieve_cboe,normalize_cboe,validate_chain
        from common.code.options_summary_tools import summarize
        folder=ROOT/'data/options_data'
        try:
            # A live endpoint cannot reconstruct a historical chain. Preserve
            # the archived snapshot on later rebuilds instead of overwriting it.
            if (folder/'cboe_raw.json').exists():
                raw=json.loads((folder/'cboe_raw.json').read_text())
                url='https://cdn.cboe.com/api/global/delayed_quotes/options/MTRN.json'
            else:
                raw,url=retrieve_cboe('MTRN',folder/'cboe_raw.json')
            chain=validate_chain(normalize_cboe(raw),END)
            chain.to_csv(folder/'cboe_normalized.csv',index=False)
            summarize(chain).to_csv(ROOT/'data/processed_data/options_summary.csv',index=False)
            p.log_source('options_data','Cboe delayed MTRN option chain','Cboe',url,folder/'cboe_raw.json',str(raw.get('timestamp')))
            print('Cboe',raw.get('timestamp'),'rows',len(chain),'usable',int(chain.usable.sum()) if len(chain) else 0,flush=True)
        except Exception as e:
            (folder/'retrieval_error.txt').write_text(repr(e))
            print('Options unavailable',repr(e),flush=True)
    if a.section in ('all','sec'):
        for t,c in CIKS.items():
            u=f'https://data.sec.gov/api/xbrl/companyfacts/CIK{c}.json'
            f=p.fin/f'companyfacts_{t}.json'; cached_json(u,f,SEC_HEADERS,False)
            p.log_source('financial_data',f'{t} SEC company facts','SEC EDGAR',u,f)
        u=f'https://data.sec.gov/submissions/CIK{CIKS["MTRN"]}.json'
        s=cached_json(u,p.fin/'submissions_MTRN.json',SEC_HEADERS,False)
        pages=[s['filings']['recent']]
        for extra in s['filings'].get('files',[]):
            if extra.get('filingTo','') >= '2021-01-01':
                pages.append(cached_json('https://data.sec.gov/submissions/'+extra['name'],p.fin/extra['name'],SEC_HEADERS,False))
        rows=[]
        for page in pages:
            for i,form in enumerate(page['form']):
                fd=page['filingDate'][i]; rd=page['reportDate'][i]; doc=page['primaryDocument'][i]; acc=page['accessionNumber'][i]
                if fd>END: continue
                take=(form=='10-K' and '2021-01-01'<=rd<='2025-12-31') or (form=='10-Q' and fd>='2025-01-01') or (form in ('8-K','DEF 14A','S-8','S-3ASR') and fd>='2026-01-01')
                if not take: continue
                url=f'https://www.sec.gov/Archives/edgar/data/1104657/{acc.replace("-","")}/{doc}'
                f=p.filings/f'{form.replace(" ","")}_{fd}_{doc}'
                out=download(url,f,SEC_HEADERS,False,1000)
                if out: p.log_source('company_filings',f'MTRN {form} filed {fd}; period {rd}','SEC EDGAR / Materion',url,f,fd)
                rows.append(dict(form=form,filing_date=fd,report_date=rd,url=url,local=str(f.relative_to(ROOT))))
        (p.fin/'filing_index.json').write_text(json.dumps(rows,indent=2))
        print('SEC documents',len(rows),flush=True)
    if a.section in ('all','prices'):
        for t in ['MTRN','SPY','IWM','XLB','ENTG','CRS','ATI','VNP.TO','CAD=X','^TNX','^IRX']:
            f=p.mkt/f'{t.replace("^","")}_daily.csv'
            if f.exists(): continue
            try:
                df,events=yahoo_chart(t,'1972-01-01',END)
                df.to_csv(f,index=False)
                (p.mkt/f'{t.replace("^","")}_events.json').write_text(json.dumps(events,indent=2))
                p.log_source('market_data',f'{t} daily OHLCV and adjusted close, {df.date.min()} to {df.date.max()}','Yahoo Finance',f'https://finance.yahoo.com/quote/{t}/history',f,END,source_type='secondary market data')
                print(t,len(df),df.iloc[-1]['close'],flush=True)
            except Exception as e: print(t,str(e),flush=True)
    if a.section in ('all','sources'):
        manifest=json.loads((ROOT/'data/source_manifest.json').read_text())
        for d in manifest:
            f=ROOT/'report'/d['category']/d['filename']
            result=download(d['url'],f,SEC_HEADERS if 'sec.gov' in d['url'] else BROWSER,False,100)
            if result:
                p.log_source(d['category'],d['title'],d['publisher'],d['url'],f,d.get('date',''))
                print('saved',f.name,flush=True)
            else: print('FAILED',d['url'],flush=True)

if __name__=='__main__': main()
