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
    print('DEPENDENCE complete',len(rows),'pair/regime rows',flush=True)

if __name__=='__main__':build()
