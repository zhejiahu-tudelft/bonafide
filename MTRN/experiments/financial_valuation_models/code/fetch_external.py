"""Network-only optional business/market data retrieval; archives never overwritten."""
import datetime,hashlib,json,time
import requests
from settings import *
from common.code.fetch_company_data import yahoo_chart

def main():
    initialize(); rows=[]
    for ticker in ['^VIX','HG=F','GC=F','SI=F','CL=F','NG=F','EURUSD=X','DX-Y.NYB']:
        path=price_path(ticker)
        url=f'https://query2.finance.yahoo.com/v8/finance/chart/{requests.utils.quote(ticker)}'
        try:
            if not path.exists():
                data,events=yahoo_chart(ticker,'2013-01-01',CUTOFF)
                data.to_csv(path,index=False)
                path.with_suffix('.events.json').write_text(json.dumps(events,indent=2))
            status='archived';error=''
        except Exception as e:status='unavailable';error=str(e)
        rows.append(dict(series=ticker,url=url,status=status,error=error,path=str(path.relative_to(ROOT)) if path.exists() and path.is_relative_to(ROOT) else str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else '',retrieved=datetime.datetime.now(datetime.timezone.utc).isoformat()))
        print(ticker,status,flush=True)
    for series in ['BAMLH0A0HYM2','DFII10']:
        url=f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}&cosd=2013-01-01&coed={CUTOFF}'
        path=RAW/f'{series}.csv'
        try:
            if not path.exists():
                response=requests.get(url,timeout=15);response.raise_for_status()
                if not response.text.startswith(('DATE','observation_date')):raise ValueError('Not a CSV series')
                path.write_bytes(response.content)
            status='archived';error=''
        except Exception as e:status='unavailable';error=str(e)
        rows.append(dict(series=series,url=url,status=status,error=error,path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else '',retrieved=datetime.datetime.now(datetime.timezone.utc).isoformat()))
        print(series,status,flush=True)
    (ROOT/'sources/manifest.json').write_text(json.dumps(rows,indent=2)+'\n')

if __name__=='__main__':main()
