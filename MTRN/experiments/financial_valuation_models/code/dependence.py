"""Individual variance is distinct from pairwise covariance and correlation."""
import itertools
import numpy as np,pandas as pd
from settings import *
from common.code.attribution_statistics import block_indices

def build():
    initialize();daily=pd.read_csv(OUT/'daily_returns.csv',index_col=0,parse_dates=True)
    marketvol=daily.SPY.dropna().rolling(63).std().shift(1)
    threshold=marketvol.rolling(252,min_periods=126).median()
    high=(marketvol>threshold).where(threshold.notna())
    rows=[];rolling=[];contrasts=[]
    for panel,start,names in [('long','2016-01-01',CORE),('recent','2021-01-01',CORE),('matched','2026-04-24',TICKERS)]:
        d=daily[names].loc[start:CUTOFF].dropna();state=high.reindex(d.index)
        d.cov().to_csv(OUT/f'covariance_{panel}.csv');d.corr().to_csv(OUT/f'correlation_{panel}.csv')
        for a,b in itertools.combinations(names,2):
            for regime,mask in [('all',np.ones(len(d),bool)),('high_vol',state==True),('low_vol',state==False)]:
                x=d.loc[mask,[a,b]]
                rows.append(dict(panel=panel,first=a,second=b,regime=regime,n=len(x),start=str(d.index.min().date()),end=str(d.index.max().date()),variance_first=x[a].var(),variance_second=x[b].var(),covariance=x[a].cov(x[b]),correlation=x[a].corr(x[b])))
            for n in [63,252]:
                corr=d[a].rolling(n,min_periods=n).corr(d[b]);cov=d[a].rolling(n,min_periods=n).cov(d[b])
                rolling.extend(dict(panel=panel,date=str(date.date()),first=a,second=b,window=n,correlation=corr.loc[date],covariance=cov.loc[date]) for date in corr.dropna().index)
            if panel!='long':continue
            x=d[[a,b]].to_numpy();label=state.to_numpy();out=[]
            if min(np.sum(label==True),np.sum(label==False))<30:continue
            for idx in block_indices(len(x),20,2000,np.random.default_rng(SEED)):
                z=x[idx];s=label[idx]
                if min(np.sum(s==True),np.sum(s==False))<20:continue
                out.append(np.corrcoef(z[s==True].T)[0,1]-np.corrcoef(z[s==False].T)[0,1])
            hi=x[label==True];lo=x[label==False]
            contrasts.append(dict(first=a,second=b,high_minus_low_correlation=np.corrcoef(hi.T)[0,1]-np.corrcoef(lo.T)[0,1],lo=np.quantile(out,.025),hi=np.quantile(out,.975),n_high=len(hi),n_low=len(lo),block=20,replications=len(out),interpretation='Pointwise descriptive regime contrast; not a causal contagion test'))
    pd.DataFrame(rows).to_csv(OUT/'covariance_regimes.csv',index=False)
    pd.DataFrame(rolling).to_csv(OUT/'rolling_dependence.csv',index=False)
    pd.DataFrame(contrasts).to_csv(OUT/'correlation_regime_contrasts.csv',index=False)
    # The forecast regimes are monthly and the correlation regime is daily; they use
    # different windows and thresholds and must not be read as the same classification.
    f=pd.read_csv(OUT/'monthly_features_as_known.csv');f=f[(f.ticker=='MTRN')&(f.date>='2022-12-31')&(f.date<='2026-07-31')]
    long=high.loc['2016-01-01':CUTOFF].dropna()
    pd.DataFrame([
      dict(regime='high_vol_regime',frequency='monthly forecast origin',used_for='regime scores of out-of-sample forecasts',
           definition='SPY within-month daily-return SD for the completed origin month above the median of the preceding 60 monthly values (at least 36)',
           timing='Known at the origin close; the target month never enters',states_in_evaluation=f'{int((f.high_vol_regime==1).sum())} high / {int((f.high_vol_regime==0).sum())} low of 44 origins'),
      dict(regime='rate_rising_regime',frequency='monthly forecast origin',used_for='regime scores of out-of-sample forecasts',
           definition='Three-month change in the as-known 10-year Treasury yield above zero; an unavailable change is left unclassified',
           timing='Known at the origin close',states_in_evaluation=f'{int((f.rate_rising_regime==1).sum())} rising / {int((f.rate_rising_regime==0).sum())} not rising of 44 origins'),
      dict(regime='high_vol (correlation)',frequency='trading day',used_for='high- minus low-volatility correlation contrasts',
           definition='SPY 63-session daily-return SD, lagged one session, above its trailing 252-session median (at least 126)',
           timing='Known the session before each daily return',states_in_evaluation=f'{int((long==True).sum())} high / {int((long==False).sum())} low sessions, 2016 to cutoff')
    ]).to_csv(OUT/'regime_definitions.csv',index=False)
    print('DEPENDENCE complete',len(rows),'pair/regime rows',flush=True)

if __name__=='__main__':build()
