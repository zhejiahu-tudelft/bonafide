"""Option retrieval, quote validation, and consistent European-model Greeks.

Equity options are American: Black-Scholes-Merton is a diagnostic approximation,
not an early-exercise model. Delta/gamma per share; theta per calendar day; vega
per one percentage point of IV; vanna = d(delta)/d(sigma), vomma = d²V/dsigma²
for sigma in decimal units. Multiply by position quantity and contract multiplier.
"""
from pathlib import Path
import json, datetime as dt, re, math
import pandas as pd
import requests
from scipy.stats import norm

def retrieve_cboe(ticker, destination):
    url=f'https://cdn.cboe.com/api/global/delayed_quotes/options/{ticker.upper()}.json'
    r=requests.get(url,headers={'User-Agent':'Mozilla/5.0'},timeout=30)
    Path(destination).write_text(r.text)
    r.raise_for_status()
    return r.json(),url

def normalize_cboe(raw):
    rows=[]
    data=raw.get('data',{})
    for x in data.get('options',[]):
        m=re.search(r'(\d{6})([CP])(\d{8})$',x.get('option',''))
        if not m: continue
        date,kind,k=m.groups()
        rows.append(dict(contract=x['option'],expiration=dt.datetime.strptime(date,'%y%m%d').date().isoformat(),
            type='call' if kind=='C' else 'put',strike=int(k)/1000,spot=data.get('current_price'),
            bid=x.get('bid'),ask=x.get('ask'),last=x.get('last_trade_price'),volume=x.get('volume'),
            open_interest=x.get('open_interest'),iv=x.get('iv'),vendor_delta=x.get('delta'),
            vendor_gamma=x.get('gamma'),vendor_theta=x.get('theta'),vendor_vega=x.get('vega'),
            quote_timestamp=raw.get('timestamp'),last_trade_timestamp=x.get('last_trade_time'),
            underlying_last_trade_timestamp=data.get('last_trade_time'),
            multiplier=100))
    return pd.DataFrame(rows)

def validate_chain(chain,asof,max_spread=.30,min_oi=20):
    d=chain.copy()
    if d.empty: return d
    for c in ['bid','ask','iv','volume','open_interest','spot','strike']:
        d[c]=pd.to_numeric(d[c],errors='coerce')
    d['midpoint']=(d.bid+d.ask)/2
    d['spread_pct']=(d.ask-d.bid)/d.midpoint.where(d.midpoint>0)
    d['days_to_expiration']=(pd.to_datetime(d.expiration)-pd.Timestamp(asof)).dt.days
    d['moneyness']=d.spot/d.strike
    qt=pd.to_datetime(d.quote_timestamp,utc=True,errors='coerce')
    anchor=pd.Timestamp(asof,tz='UTC')
    # Date-based check: a saved quote must be from the selected session.
    d['same_session']=qt.dt.date==anchor.date()
    if 'underlying_last_trade_timestamp' in d:
        # Cboe's file timestamp has no timezone and can roll to the next UTC
        # date. Use underlying trade date only as a session alignment proxy;
        # this does not verify freshness of each individual bid and ask.
        d['same_session']=pd.to_datetime(d.underlying_last_trade_timestamp,errors='coerce').dt.date==anchor.date()
    lt=pd.to_datetime(d.last_trade_timestamp,errors='coerce')
    d['trade_age_days']=(pd.Timestamp(asof)-lt.dt.normalize()).dt.days
    d['usable']=((d.bid>0)&(d.ask>=d.bid)&(d.iv>0)&(d.iv<5)&(d.days_to_expiration>0)&
       (d.spread_pct<=max_spread)&(d.open_interest>=min_oi)&d.same_session)
    return d

def bsm_greeks(spot,strike,t,rate,dividend_yield,sigma,kind):
    if min(spot,strike,t,sigma)<=0 or kind not in ('call','put'): raise ValueError('Invalid BSM input')
    root=math.sqrt(t); df=math.exp(-rate*t); dq=math.exp(-dividend_yield*t)
    d1=(math.log(spot/strike)+(rate-dividend_yield+.5*sigma*sigma)*t)/(sigma*root)
    d2=d1-sigma*root; phi=norm.pdf(d1); sign=1 if kind=='call' else -1
    price=sign*(spot*dq*norm.cdf(sign*d1)-strike*df*norm.cdf(sign*d2))
    delta=sign*dq*norm.cdf(sign*d1)
    theta=(-spot*dq*phi*sigma/(2*root)+sign*dividend_yield*spot*dq*norm.cdf(sign*d1)-sign*rate*strike*df*norm.cdf(sign*d2))/365
    vega_unit=spot*dq*phi*root
    return dict(price=price,delta=delta,gamma=dq*phi/(spot*sigma*root),theta=theta,vega=vega_unit/100,
        vanna=-dq*phi*d2/sigma,vomma=vega_unit*d1*d2/sigma)
