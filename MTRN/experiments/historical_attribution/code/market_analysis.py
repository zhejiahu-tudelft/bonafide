"""Saved-data market and factor analysis; no network calls."""
import json,re,zipfile,io
import numpy as np,pandas as pd
from settings import *
from common.code.attribution_statistics import bootstrap_moments,fit_attribution,bootstrap_model,complete_week_returns

def french(name,daily=False):
    p=RAW/name
    if not p.exists():return pd.DataFrame()
    with zipfile.ZipFile(p) as z:text=z.read(z.namelist()[0]).decode('utf-8-sig')
    pattern=r'^\s*\d{8},' if daily else r'^\s*\d{6},'
    lines=text.splitlines();first=next(i for i,x in enumerate(lines) if re.match(pattern,x))
    header=next(x for x in reversed(lines[:first]) if x.strip().startswith(','))
    data='\n'.join([header]+[x.strip() for x in lines[first:] if re.match(pattern,x)])
    d=pd.read_csv(io.StringIO(data),index_col=0);d.columns=d.columns.str.strip();d=d.apply(pd.to_numeric,errors='coerce')
    d.index=pd.to_datetime(d.index.astype(str),format='%Y%m%d' if daily else '%Y%m')
    if not daily:d.index=d.index+pd.offsets.MonthEnd(0)
    d=d.mask(d<=-99).rename(columns={'Mkt-RF':'MKT','Mom':'MOM'})/100
    return d.loc[:CUTOFF]

def load_prices():
    out={}
    for tk in TICKERS+['SPY','SOXX','ITA']:
        p=prices_path(tk)
        if not p.exists():deferred('Prices '+tk,'No retrievable daily series');continue
        d=pd.read_csv(p,index_col='date',parse_dates=True).sort_index().loc[:CUTOFF]
        if tk=='ELMT':d=d.loc['2026-04-23':]
        assert d.index.is_unique and (d.close>0).all()
        out[tk]=d
    return out

def build():
    initialize();prices=load_prices()
    all_returns=pd.concat({tk:p.adj_close.pct_change(fill_method=None) for tk,p in prices.items()},axis=1,sort=True).loc['2015':]
    all_returns.to_csv(OUT/'daily_returns.csv',index_label='date')
    ff=french('F-F_Research_Data_Factors_CSV.zip');mom=french('F-F_Momentum_Factor_CSV.zip')
    ff5=french('F-F_Research_Data_5_Factors_2x3_CSV.zip');ffd=french('F-F_Research_Data_Factors_daily_CSV.zip',True)
    ff.join(mom).to_csv(OUT/'monthly_factors.csv',index_label='date');ffd.to_csv(OUT/'daily_factors.csv',index_label='date')
    deferred('August/September risk-free-adjusted statistics',f'Kenneth French July 2026 vintage ends {ffd.index[-1].date()}; raw returns and benchmark models extend to {CUTOFF}. No risk-free observations extrapolated.')
    # Compounded calendar-month returns, with the incomplete September excluded.
    monthly=(1+all_returns).resample('ME').prod(min_count=1)-1
    monthly=monthly.loc[START:MONTH_END];monthly.to_csv(OUT/'monthly_returns.csv',index_label='date')
    summary=[];pairs=[];wealth=[];residual_daily=[];daily_models=[];covariances=[]
    panels={'long':(START,CORE),'recent':('2021-01-01',CORE),'matched':('2026-04-24',TICKERS)}
    for panel,(start,tks) in panels.items():
        tks=[tk for tk in tks if tk in prices];raw=all_returns[tks].loc[start:].dropna()
        for tk in tks:
            r=raw[tk];cum=(1+r).cumprod();base_date=prices[tk].index[prices[tk].index<r.index[0]][-1];years=(r.index[-1]-base_date).days/365.25
            wealth.append(dict(panel=panel,ticker=tk,start=str(r.index[0].date()),end=str(r.index[-1].date()),n=len(r),total_return=cum.iloc[-1]-1,
                               start_close=str(base_date.date()),cagr=cum.iloc[-1]**(1/years)-1 if years>=1 else np.nan,max_drawdown=(cum/cum.cummax().clip(lower=1)-1).min(),
                               vol_annual=r.std()*np.sqrt(252),mean_annual_arithmetic=252*r.mean() if years>=1 else np.nan))
        for frequency,block,m in [('daily',10,252),('weekly',5,52)]:
            d=raw if frequency=='daily' else complete_week_returns(raw,prices['SPY'].index,CUTOFF)
            for basis,z in [('total',d),('excess',None)]:
                if basis=='excess':
                    joined=raw.join(ffd[['RF']],how='inner').dropna()
                    if frequency=='daily': z=joined[tks].sub(joined.RF,axis=0)
                    else:
                        w=complete_week_returns(joined,prices['SPY'].index,joined.index[-1])
                        z=w[tks].sub(w.RF,axis=0)
                if len(z)<max(20,2*block):continue
                a,b=bootstrap_moments(z,block,REPS,SEED)
                for x in [a,b]:x['panel']=panel;x['frequency']=frequency;x['basis']=basis
                a['vol_annual']=a.volatility*np.sqrt(m);a['vol_annual_lo']=a.vol_lo*np.sqrt(m);a['vol_annual_hi']=a.vol_hi*np.sqrt(m)
                summary.append(a);pairs.append(b)
                if frequency=='daily' and basis=='total':
                    z.cov().to_csv(OUT/f'covariance_{panel}.csv');z.corr().to_csv(OUT/f'correlation_{panel}.csv')
                    # Block-length sensitivity for the primary total-return moments.
                    for alternate in [5,20]:
                        aa,bb=bootstrap_moments(z,alternate,REPS,SEED)
                        aa.to_csv(OUT/f'moment_sensitivity_{panel}_block{alternate}.csv',index=False)
            # Influence diagnostics retain the full sample as the primary result.
        for tk in tks:
            for nremove in [1,5]:
                r=raw[tk];kept=r.drop(r.abs().nlargest(nremove).index)
                covariances.append(dict(panel=panel,ticker=tk,removed=nremove,full_mean=r.mean(),reduced_mean=kept.mean(),full_variance=r.var(),reduced_variance=kept.var()))
        features=all_returns[['SPY']] if panel=='matched' else all_returns[['SPY','SOXX','ITA']]
        res={}
        for tk in tks:
            minimum=60 if panel=='matched' else 252
            try:
                s,c,r=fit_attribution(raw[tk],features,lags=5,min_n=minimum)
                s.update(panel=panel,ticker=tk,model='daily raw-return market' if panel=='matched' else 'daily raw-return market + industries',basis='total returns; intercept is not excess-return alpha')
                daily_models.append(s);res[tk]=r.residual
            except ValueError as e:deferred(f'Daily model {panel} {tk}',str(e))
        if res:
            r=pd.DataFrame(res).dropna();r.to_csv(OUT/f'daily_residuals_{panel}.csv',index_label='date');r.corr().to_csv(OUT/f'residual_correlation_{panel}.csv')
            # Raw model residuals are diagnostic observations. Bootstrap intervals
            # that assume fixed fitted coefficients are not reported as refit CIs.
            for tk in r:
                residual_daily.append(dict(panel=panel,ticker=tk,n=len(r),mean=r[tk].mean(),variance=r[tk].var(),volatility=r[tk].std()))
    for panel,start in [('long',START),('recent','2021-01-01')]:
        joined=monthly[CORE].join(ff[['RF']],how='inner').loc[start:].dropna()
        for basis,z in [('total',joined[CORE]),('excess',joined[CORE].sub(joined.RF,axis=0))]:
            a,b=bootstrap_moments(z,3,REPS,SEED)
            for x in [a,b]:x['panel']=panel;x['frequency']='monthly';x['basis']=basis
            a['vol_annual']=a.volatility*np.sqrt(12);a['vol_annual_lo']=a.vol_lo*np.sqrt(12);a['vol_annual_hi']=a.vol_hi*np.sqrt(12)
            summary.append(a);pairs.append(b)
    pd.concat(summary).to_csv(OUT/'moments.csv',index=False);pd.concat(pairs).to_csv(OUT/'paired_comparisons.csv',index=False)
    pd.DataFrame(wealth).to_csv(OUT/'holding_returns.csv',index=False);pd.DataFrame(daily_models).to_csv(OUT/'daily_models.csv',index=False)
    pd.DataFrame(residual_daily).to_csv(OUT/'daily_residual_moments.csv',index=False);pd.DataFrame(covariances).to_csv(OUT/'influence_checks.csv',index=False)
    factors=ff.join(mom)
    factors=factors.join(monthly[['SOXX','ITA']].sub(ff.RF,axis=0).rename(columns={'SOXX':'SEMIS','ITA':'DEFENSE'}))
    tn=pd.read_csv(prices_path('TNX'),index_col='date',parse_dates=True).close.resample('ME').last().diff().rename('D_NOMINAL')
    factors=factors.join(tn)
    for series,name in [('DFII10','D_REAL'),('BAMLH0A0HYM2','D_CREDIT')]:
        p=RAW/f'{series}.csv'
        if p.exists():
            d=pd.read_csv(p,index_col=0,parse_dates=True);s=pd.to_numeric(d.iloc[:,0],errors='coerce').resample('ME').last().diff()
            factors=factors.join(s.rename(name))
    specifications={'M0':['MKT'],'M1':['MKT','SMB','HML','MOM'],'M2':['MKT','SMB','HML','MOM','SEMIS','DEFENSE']}
    if {'D_REAL','D_CREDIT'}.issubset(factors):specifications['M3']=specifications['M2']+['D_REAL','D_CREDIT']
    else:deferred('M3 real-yield and credit-spread model','Both FRED CSV and alternative text delivery failed. M2 plus nominal Treasury yield change is labeled a sensitivity, not a substitute for M3.')
    specifications['M2_nominal']=specifications['M2']+['D_NOMINAL']
    specifications['M1_nominal']=specifications['M1']+['D_NOMINAL']
    # FF5 uses its own SMB construction, not the FF3 SMB series.
    alternative=ff5.rename(columns={'SMB':'SMB5','HML':'HML5','MKT':'MKT5'}).drop(columns=['RF']).join(mom)
    factors=factors.join(alternative.drop(columns=['MOM']))
    specifications['FF5_MOM']=['MKT5','SMB5','HML5','RMW','CMA','MOM']
    model_rows=[];coef_rows=[];skipped=[]
    for panel,start in [('long',START),('recent','2021-01-01')]:
        required=list(dict.fromkeys(x for cols in specifications.values() for x in cols))
        joined=monthly[CORE].join(factors[required+['RF']]).loc[start:MONTH_END].dropna()
        for name,cols in specifications.items():
            for tk in CORE:
                try:
                    y=joined[tk]-joined.RF;s,c,r=fit_attribution(y,joined[cols],3,max(60,10*(len(cols)+1)))
                    s.update(bootstrap_model(y,joined[cols],3,REPS,SEED));s.update(panel=panel,ticker=tk,model=name)
                    c['panel']=panel;c['ticker']=tk;c['model']=name;coef_rows.append(c);model_rows.append(s)
                    r.to_csv(OUT/f'model_residuals_{panel}_{tk}_{name}.csv',index_label='date')
                except ValueError as e:skipped.append(dict(panel=panel,ticker=tk,model=name,reason=str(e)))
    pd.DataFrame(model_rows).to_csv(OUT/'models.csv',index=False);pd.concat(coef_rows).to_csv(OUT/'coefficients.csv',index=False)
    pd.DataFrame(skipped).to_csv(OUT/'model_exclusions.csv',index=False)
    factors.loc[START:].corr().to_csv(OUT/'factor_correlations.csv')
    print('Market analysis:',len(model_rows),'monthly fits;',len(skipped),'sample-gated fits; factor end',ff.index[-1].date())

if __name__=='__main__':build()
