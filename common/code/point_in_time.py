"""Accession-audited SEC facts selected using public filing availability.

Date-only filings become usable on the next observed market session. Earnings
release values are not silently backdated from later company-facts records.
"""
import json,datetime
import pandas as pd
import numpy as np

class PointInTimeFacts:
    def __init__(self,path,sessions,ticker):
        self.data=json.loads(path.read_text());self.sessions=sessions;self.ticker=ticker;self.audit=[];self._entries={}
    def entries(self,tags,unit='USD',namespace='us-gaap'):
        tags=[tags] if isinstance(tags,str) else tags;key=(tuple(tags),unit,namespace)
        if key in self._entries:return self._entries[key]
        rows=[]
        for priority,tag in enumerate(tags):
            for e in self.data['facts'].get(namespace,{}).get(tag,{}).get('units',{}).get(unit,[]):
                if e.get('form') not in ['10-K','10-Q','10-K/A','10-Q/A','S-1','S-1/A','424B4']:continue
                e=dict(e,tag=tag,priority=priority,unit=unit,namespace=namespace)
                e['days']=(pd.Timestamp(e['end'])-pd.Timestamp(e['start'])).days+1 if e.get('start') else 0
                i=self.sessions.searchsorted(pd.Timestamp(e['filed']),side='right')
                e['available']=str(self.sessions[i].date()) if i<len(self.sessions) else '9999-12-31'
                rows.append(e)
        self._entries[key]=rows
        return rows
    def select(self,tags,asof,end=None,start=None,min_days=None,max_days=None,unit='USD',namespace='us-gaap',label=''):
        rows=[x for x in self.entries(tags,unit,namespace) if x['available']<=asof and x['end']<=asof]
        if end: rows=[x for x in rows if x['end']==end]
        if start: rows=[x for x in rows if x.get('start')==start]
        if min_days is not None:rows=[x for x in rows if x['days']>=min_days]
        if max_days is not None:rows=[x for x in rows if x['days']<=max_days]
        if not rows:return None
        # Latest period, preferred tag, latest vintage actually available then.
        best=max(rows,key=lambda x:(x['end'],-x['priority'],x['filed'],x.get('accn','')))
        self._record(best,asof,label)
        return best
    def _record(self,best,asof,label):
        vintages=[x for x in self.entries(best['tag'],best['unit'],best['namespace']) if x['end']==best['end'] and x.get('start')==best.get('start')]
        first=min(vintages,key=lambda x:x['filed'])
        status='changed from earliest filed value' if best['val']!=first['val'] else 'same value as earliest filing'
        self.audit.append(dict(ticker=self.ticker,asof=asof,metric=label or best['tag'],first_filed_for_period=first['filed'],vintage_status=status,**best))
    def value(self,*args,**kwargs):
        x=self.select(*args,**kwargs);return x['val'] if x else np.nan
    def ttm(self,tags,asof,unit='USD',label=''):
        annual=self.select(tags,asof,min_days=330,max_days=400,unit=unit,label=label)
        if not annual:return np.nan,None
        current=self.select(tags,asof,min_days=60,max_days=310,unit=unit,label=label)
        if not current or current['end']<=annual['end']:return annual['val'],annual['end']
        if (pd.Timestamp(current['end'])-pd.Timestamp(annual['end'])).days>310:
            return np.nan,current['end']  # Do not combine a stale annual tag with recent YTD.
        # Choose the largest available YTD duration ending at the current cutoff.
        candidates=[x for x in self.entries(tags,unit) if x['end']==current['end'] and x['available']<=asof and 60<=x['days']<=310]
        days=max(x['days'] for x in candidates)
        current=self.select(tags,asof,end=current['end'],min_days=days,max_days=days,unit=unit,label=label)
        prev=[x for x in self.entries(tags,unit) if x['available']<=asof and
              abs((pd.Timestamp(current['end'])-pd.Timestamp(x['end'])).days-365)<=10 and abs(x['days']-current['days'])<=10]
        if not prev:return np.nan,current['end']
        prior=max(prev,key=lambda x:(-abs(x['days']-current['days']),-x['priority'],x['filed']))
        self._record(prior,asof,label)
        return annual['val']+current['val']-prior['val'],current['end']
