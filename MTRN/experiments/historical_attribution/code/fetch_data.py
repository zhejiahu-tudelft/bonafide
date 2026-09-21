"""Network-only retrieval. Existing snapshots and the prior study stay intact."""
import json,time,re,argparse,datetime,hashlib
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from settings import *
from common.code.fetch_company_data import yahoo_chart,SEC_HEADERS,BROWSER

SESSION=requests.Session()
def get(url,path,kind,published='',timeout=25):
    path=Path(path)
    if not path.exists():
        try:
            r=SESSION.get(url,headers=SEC_HEADERS if 'sec.gov' in url else BROWSER,timeout=timeout)
            time.sleep(.15)
            r.raise_for_status()
            if len(r.content)<20: raise ValueError('Empty source')
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(r.content)
        except Exception as e:
            print('UNAVAILABLE',url,str(e)[:140],flush=True)
            log(url,path,kind,published,'unavailable');return None
    log(url,path,kind,published,'cached');return path

def log(url,path,kind,published,status):
    p=ROOT/'sources/manifest.json';rows=json.loads(p.read_text()) if p.exists() else []
    row=dict(url=url,path=str(path.relative_to(ROOT)),kind=kind,published=published,
             retrieved=datetime.datetime.now(datetime.timezone.utc).isoformat(),status=status,
             sha256=hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else '')
    if not any(x['url']==url and x['status']==status for x in rows): rows.append(row)
    p.write_text(json.dumps(rows,indent=2))

def market():
    for tk in ['ELMT','SOXX','ITA']:
        path=RAW/f'{tk}_daily.csv'
        if not path.exists():
            try:
                d,events=yahoo_chart(tk,'2014-01-01',CUTOFF);d.to_csv(path,index=False)
                (RAW/f'{tk}_events.json').write_text(json.dumps(events,indent=2))
            except Exception as e: print('PRICE FAILURE',tk,str(e),flush=True);continue
        log(f'https://finance.yahoo.com/quote/{tk}/history',path,'market data',CUTOFF,'cached')
        print('PRICE',tk,flush=True)
    base='https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/'
    for name in ['F-F_Research_Data_Factors_CSV.zip','F-F_Research_Data_Factors_daily_CSV.zip','F-F_Momentum_Factor_CSV.zip','F-F_Research_Data_5_Factors_2x3_CSV.zip']:
        get(base+name,RAW/name,'factor returns')
    get('https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html',SOURCES/'french_methodology.html','factor methodology')
    for series in ['DFII10','BAMLH0A0HYM2','DGS10']:
        url=f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}&cosd=2014-01-01&coed={CUTOFF}'
        if not get(url,RAW/f'{series}.csv','macro series'):
            # Public text observations are an alternative delivery format.
            get(f'https://fred.stlouisfed.org/data/{series}.txt',RAW/f'{series}.txt','macro series alternative')
    for series in ['DFII10','BAMLH0A0HYM2']:
        get(f'https://fred.stlouisfed.org/series/{series}',SOURCES/f'{series}_methodology.html','macro methodology')

def sec():
    get(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{CIKS["ELMT"]:010d}.json',RAW/'companyfacts_ELMT.json','SEC company facts')
    index=[]
    for tk,cik in CIKS.items():
        p=get(f'https://data.sec.gov/submissions/CIK{cik:010d}.json',RAW/f'submissions_{tk}.json','SEC submissions')
        if not p: continue
        sub=json.loads(p.read_text());pages=[sub['filings']['recent']]
        for extra in sub['filings'].get('files',[]):
            if extra.get('filingTo','')>='2021-01-01':
                q=get('https://data.sec.gov/submissions/'+extra['name'],RAW/extra['name'],'SEC submissions archive')
                if q: pages.append(json.loads(q.read_text()))
        for page in pages:
            for i,form in enumerate(page['form']):
                row={k:v[i] for k,v in page.items() if isinstance(v,list) and len(v)>i}
                row['ticker']=tk
                if row['filingDate']>CUTOFF: continue
                if form in ['10-K','10-Q'] or (form=='8-K' and row['filingDate']>='2021-01-01' and ('2.02' in row.get('items','') or tk=='ELMT')):
                    index.append(row)
                if tk=='ELMT' and form in ['10-Q','10-K','424B4','8-K'] and row['filingDate']>='2026-01-01':
                    url=f'https://www.sec.gov/Archives/edgar/data/{cik}/{row["accessionNumber"].replace("-","")}/{row["primaryDocument"]}'
                    get(url,SOURCES/f'{tk}_{row["filingDate"]}_{form.replace("/","")}.html','ELMT filing',row['filingDate'])
        print('SUBMISSIONS',tk,flush=True)
    (RAW/'filing_index.json').write_text(json.dumps(index,indent=2))

def earnings():
    rows=json.loads((RAW/'filing_index.json').read_text());results=[]
    for row in rows:
        if row['ticker'] not in CORE or row['form']!='8-K' or '2.02' not in row.get('items',''): continue
        tk=row['ticker']; acc=row['accessionNumber'];base=f'https://www.sec.gov/Archives/edgar/data/{CIKS[tk]}/{acc.replace("-","")}/'
        path=get(base+row['primaryDocument'],SOURCES/'earnings'/f'{tk}_{acc}.html','earnings 8-K',row['filingDate'])
        if not path: continue
        soup=BeautifulSoup(path.read_text(),'html.parser');text=soup.get_text(' ',strip=True)
        links=[a for a in soup.find_all('a',href=True) if a['href'].lower().endswith(('.htm','.html')) and a['href']!=row['primaryDocument']]
        candidates=[a for a in links if re.search(r'99[.\-_]?1|press.release|earnings.release',a.get_text(' ',strip=True)+' '+a['href'],re.I)]
        if not candidates: candidates=[a for a in links if re.search(r'ex.*99|release',a['href'],re.I)]
        exhibit=''
        if candidates:
            a=candidates[0];url=urljoin(base,a['href']);ep=SOURCES/'earnings'/f'{tk}_{acc}_release.html'
            if get(url,ep,'earnings release',row['filingDate']): exhibit=str(ep.relative_to(ROOT))
        results.append(dict(ticker=tk,accession=acc,filed=row['filingDate'],report_date=row.get('reportDate',''),
                            acceptance=row.get('acceptanceDateTime',''),filing_path=str(path.relative_to(ROOT)),release_path=exhibit))
        print('EARNINGS',tk,row['filingDate'],'release',bool(exhibit),flush=True)
    (RAW/'earnings_index.json').write_text(json.dumps(results,indent=2))

def documents():
    urls={
      'ELMT_IPO.html':'https://investors.theelmetgroup.com/news-events/press-releases/detail/157/the-elmet-group-co-announces-closing-of-upsized-initial-public-offering-and-full-exercise-of-underwriters-option-to-purchase-additional-shares',
      'ELMT_financing.html':'https://investors.theelmetgroup.com/news-events/press-releases/detail/168/department-of-war-makes-landmark-450-million-committed-investment-in-the-elmet-group-to-secure-americas-tungsten-supply-chain',
      'ELMT_financing_8K.html':'https://investors.theelmetgroup.com/sec-filings/content/0001213900-26-099734/ea0304682-8k_elmet.htm',
      'ELMT_history.html':'https://stockanalysis.com/stocks/elmt/history/',
      'SOXX.html':'https://www.ishares.com/us/products/239705/ishares-phlx-semiconductor-etf',
      'ITA.html':'https://www.ishares.com/us/products/239502/ishares-us-aerospace-defense-etf'}
    for name,url in urls.items():get(url,SOURCES/name,'company/benchmark evidence')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--section',choices=['all','market','sec','earnings','documents'],default='all');args=ap.parse_args();initialize()
    for name,func in [('market',market),('sec',sec),('earnings',earnings),('documents',documents)]:
        if args.section in ['all',name]:func()
