"""Announcement-date and financial-update extraction from original SEC exhibits."""
import json,re
import numpy as np,pandas as pd
from bs4 import BeautifulSoup
from settings import *
from market_analysis import load_prices
from common.code.attribution_statistics import session_for_release,event_car,block_indices

MONTHS=r'(?:January|February|March|April|May|June|July|August|September|October|November|December)'
DATE=rf'{MONTHS}\s+\d{{1,2}},?\s+20\d{{2}}'

def normalized(s):return re.sub(r'\s+',' ',s.replace('\xa0',' ')).strip()

def numbers(s):
    # Parentheses are negative, dollar signs and separate sign cells are harmless.
    return [float(x.replace(',','').replace(' ','').replace('(','-').replace(')',''))
            for x in re.findall(r'\(?\s*-?\d[\d,]*(?:\.\d+)?\s*\)?',s)]

def release_values(soup,ticker):
    """Select an original GAAP quarterly table, never an adjusted reconciliation.

    Each company's first quarter is column 0; ATI puts the preceding quarter in
    column 1 and the prior-year quarter in column 2. Retain table text for audit.
    """
    prior=2 if ticker=='ATI' else 1
    for table in soup.select('table'):
        text=normalized(table.get_text(' ',strip=True));low=text.lower()
        if len(text)>18000 or 'diluted' not in low or 'cost of sales' not in low or not re.search(r'operating \(?(?:income|profit|loss)',low):continue
        sales=op=eps=None;diluted=False;rows=[]
        for tr in table.select('tr'):
            line=normalized(tr.get_text(' ',strip=True));l=line.lower();rows.append(line)
            if sales is None and re.match(r'^(net sales|sales|revenue)\s+\$?\s*\d',l):sales=numbers(line)
            if op is None and re.match(r'^operating \(?(income|profit|loss)',l):op=numbers(line)
            if 'diluted' in l and ('per share' in l or 'per common share' in l or 'per diluted share' in l):
                if 'adjusted' not in l and 'non-gaap' not in l:
                    v=numbers(line)
                    if len(v)>prior:eps=v
                    else:diluted=True
            elif diluted and re.search(r'net income(?: \(loss\))? per share',l):eps=numbers(line);diluted=False
            elif l.startswith('diluted ') and sales and op and eps is None:
                v=numbers(line)
                if v and max(abs(x) for x in v)<100:eps=v
        if all(x is not None and len(x)>prior for x in [sales,op,eps]):
            if min(sales[0],sales[prior])<=0 or max(abs(x) for x in eps[:prior+1])>100:continue
            return dict(eps=eps[0],eps_prior=eps[prior],revenue_release_units=sales[0],revenue_prior_release_units=sales[prior],
                        operating_income_release_units=op[0],operating_income_prior_release_units=op[prior],
                        operating_margin=op[0]/sales[0],operating_margin_prior=op[prior]/sales[prior],
                        financial_table='\n'.join(rows),prior_column=prior)
    return {}

def extract():
    prices=load_prices();sessions=prices['SPY'].index;events=[];excluded=[];audits={}
    for x in json.loads((RAW/'earnings_index.json').read_text()):
        if not x.get('release_path'):
            excluded.append(dict(**x,reason='No earnings-release exhibit; often duplicate presentation or other update'));continue
        soup=BeautifulSoup((ROOT/x['release_path']).read_text(),'html.parser');s=normalized(soup.get_text(' ',strip=True))
        if not re.search(r'(?:reports|announces|rep\s*orts).{0,100}(?:result|earning)',s[:1300],re.I):
            excluded.append(dict(**x,reason='Not a quarterly results release'));continue
        # Find a dateline near the start, excluding dates outside the filing/report range.
        candidates=[]
        for match in re.finditer(DATE,s[:6500],re.I):
            dt=pd.Timestamp(match.group()).strftime('%Y-%m-%d')
            lag=(pd.Timestamp(x['filed'])-pd.Timestamp(dt)).days
            if 0<=lag<=10:candidates.append((match.start(),dt,match.group()))
        date=candidates[0][1] if candidates else x['report_date']
        evidence=candidates[0][2] if candidates else '8-K report date; no exhibit dateline detected'
        explicit=re.search(r'FOR RELEASE AT\s+(\d{1,2}):(\d{2})\s*(AM|PM)\s*(EDT|EST)',s[:1500],re.I)
        timing='date only; next session';after=True
        if explicit:
            hour=int(explicit[1])%12+(12 if explicit[3].upper()=='PM' else 0)
            after=hour>=16;timing='pre-open' if hour<9 else ('after-close' if after else 'intraday')
            evidence+='; '+explicit.group()
        session=session_for_release(sessions,date,after);same=session_for_release(sessions,date,False)
        values=release_values(soup,x['ticker']);audits[x['accession']]=dict(release_excerpt=s[:1800],date_evidence=evidence,**values)
        values.pop('financial_table',None)
        row=dict(**x,release_date=date,session=str(session.date()),same_day_session=str(same.date()),timing=timing,date_evidence=evidence,**values)
        before=prices[x['ticker']].loc[prices[x['ticker']].index<pd.Timestamp(date)].iloc[-1]
        row['pre_release_price']=before.close
        row['earnings_change_scaled']=(row['eps']-row['eps_prior'])/before.close if 'eps' in row else np.nan
        row['operating_margin_change']=row.get('operating_margin',np.nan)-row.get('operating_margin_prior',np.nan)
        row['source_url']=f"https://www.sec.gov/Archives/edgar/data/{CIKS[x['ticker']]}/{x['accession'].replace('-','')}/"
        events.append(row)
    e=pd.DataFrame(events).sort_values(['ticker','release_date','filed'])
    duplicate=e.duplicated(['ticker','release_date']);excluded+=e.loc[duplicate].assign(reason='Duplicate results announcement').to_dict('records')
    e=e.loc[~duplicate];e.to_csv(OUT/'earnings_announcements.csv',index=False)
    (OUT/'earnings_extractions.json').write_text(json.dumps(audits,indent=2))
    pd.DataFrame(excluded).to_csv(OUT/'event_exclusions.csv',index=False)
    return e,prices

def quarter_bootstrap(events,stat,columns,block=2):
    q=events.release_date.astype('datetime64[ns]').dt.to_period('Q')
    quarters=pd.period_range(q.min(),q.max(),freq='Q')
    bins=[np.flatnonzero(q==v) for v in quarters];out=[]
    for draw in block_indices(len(quarters),block,REPS,np.random.default_rng(SEED)):
        idx=np.concatenate([bins[i] for i in draw]);sample=events.iloc[idx]
        out.append(stat(sample))
    return pd.DataFrame(out,columns=columns)

def build():
    initialize();events,prices=extract();returns=pd.read_csv(OUT/'daily_returns.csv',index_col=0,parse_dates=True)
    rows=[]
    for event in events.to_dict('records'):
        for name,win in [('primary',(-1,1)),('short',(0,1)),('wide',(-1,5))]:
            for mapping in ['conservative','same_date']:
                session=event['session'] if mapping=='conservative' else event['same_day_session']
                try:result=event_car(returns[event['ticker']],returns.SPY,session,win)
                except ValueError as ex:result=dict(car=np.nan,exclusion=str(ex))
                rows.append(dict(**event,window=name,mapping=mapping,benchmark='market',**result))
                try:industry=event_car(returns[event['ticker']],returns[['SPY','SOXX','ITA']],session,win)
                except ValueError as ex:industry=dict(car=np.nan,exclusion=str(ex))
                rows.append(dict(**event,window=name,mapping=mapping,benchmark='market + industries',**industry))
    cars=pd.DataFrame(rows);cars.to_csv(OUT/'event_cars.csv',index=False)
    primary=cars[(cars.window=='primary')&(cars.mapping=='conservative')&(cars.benchmark=='market')].dropna(subset=['car']).copy()
    cars.groupby(['ticker','window','mapping','benchmark']).car.agg(['count','mean','var']).reset_index().to_csv(OUT/'event_sensitivity.csv',index=False)
    summary=[]
    for tk,g in primary.groupby('ticker'):
        boots=quarter_bootstrap(g,lambda z:[z.car.mean(),z.car.var()],['mean','variance'])
        summary.append(dict(ticker=tk,n=len(g),mean_car=g.car.mean(),mean_lo=boots['mean'].quantile(.025),mean_hi=boots['mean'].quantile(.975),
                            car_variance=g.car.var(),var_lo=boots.variance.quantile(.025),var_hi=boots.variance.quantile(.975),
                            complete_updates=int(g[['earnings_change_scaled','operating_margin_change']].notna().all(axis=1).sum())))
    pd.DataFrame(summary).to_csv(OUT/'event_summary.csv',index=False)
    complete=primary.dropna(subset=['earnings_change_scaled','operating_margin_change']);nq=pd.to_datetime(complete.release_date).dt.to_period('Q').nunique()
    features=['earnings_change_scaled','operating_margin_change']
    def regress(z):
        X=np.column_stack([*(np.asarray(z.ticker==tk,dtype=float) for tk in CORE),z[features].to_numpy()]);y=z.car.to_numpy()
        if np.linalg.matrix_rank(X)<X.shape[1]:return np.full(len(CORE)+2,np.nan)
        return np.linalg.lstsq(X,y,rcond=None)[0]
    if len(complete)>=60 and nq>=12:
        names=CORE+features;b=regress(complete);boot=quarter_bootstrap(complete,regress,names)
        pd.DataFrame(dict(term=names,estimate=b,lo=boot.quantile(.025).values,hi=boot.quantile(.975).values,
                          n=len(complete),calendar_quarters=nq,valid_bootstrap=int(boot.notna().all(axis=1).sum()))).to_csv(OUT/'event_regression.csv',index=False)
    else:deferred('Pooled earnings-update regression',f'{len(complete)} complete events / {nq} quarters; requires 60 / 12. All eligible CARs retained.')
    # Remove the union of actual [-1,+1] announcement windows for influence diagnostics.
    diagnostics=[]
    for tk in CORE:
        r=returns[tk].loc['2021':].dropna();mask=pd.Series(False,index=r.index)
        for event in primary[primary.ticker==tk].itertuples():mask|=(r.index>=event.window_start)&(r.index<=event.window_end)
        kept=r.loc[~mask]
        diagnostics.append(dict(ticker=tk,n_full=len(r),n_excluded=int(mask.sum()),mean_full=r.mean(),mean_excluding_events=kept.mean(),
                                variance_full=r.var(),variance_excluding_events=kept.var()))
    pd.DataFrame(diagnostics).to_csv(OUT/'announcement_influence.csv',index=False)
    print('Events:',len(events),'announcements;',len(complete),'complete financial updates;',nq,'quarters')

if __name__=='__main__':build()
