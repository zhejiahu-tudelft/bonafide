"""Finite, prespecified stability checks and synchronized refitted contrasts."""
import numpy as np,pandas as pd
from statsmodels.stats.multitest import multipletests
from settings import *
from market_analysis import french
from common.code.attribution_statistics import fit_attribution,joint_model_bootstrap

def build():
    daily=pd.read_csv(OUT/'daily_returns.csv',index_col=0,parse_dates=True)
    monthly=pd.read_csv(OUT/'monthly_returns.csv',index_col=0,parse_dates=True)
    ff=french('F-F_Research_Data_Factors_CSV.zip').join(french('F-F_Momentum_Factor_CSV.zip'))
    f=ff.join(monthly[['SOXX','ITA']].sub(ff.RF,axis=0).rename(columns={'SOXX':'SEMIS','ITA':'DEFENSE'}))
    stats=[];pairs=[];coefs=[];hac=[];stability=[]
    for panel,start,tks,frequency,cols in [('long',START,CORE,'monthly',['MKT','SMB','HML','MOM','SEMIS','DEFENSE']),
           ('recent','2021-01-01',CORE,'monthly',['MKT','SMB','HML','MOM']),
           ('matched','2026-04-24',TICKERS,'daily',['SPY']),
           ('long',START,CORE,'daily',['SPY','SOXX','ITA']),('recent','2021-01-01',CORE,'daily',['SPY','SOXX','ITA'])]:
        if frequency=='monthly':
            d=monthly[tks].join(f).loc[start:].dropna();y=d[tks].sub(d.RF,axis=0);x=d[cols];block=3
        else:d=daily[tks+cols].loc[start:].dropna();y=d[tks];x=d[cols];block=10
        a,b,c=joint_model_bootstrap(y,x,block,REPS,SEED)
        for z in [a,b,c]:z['panel']=panel;z['frequency']=frequency;z['model']=' + '.join(cols);z['basis']='excess' if frequency=='monthly' else 'total'
        stats.append(a);pairs.append(b);coefs.append(c)
        if frequency=='monthly':
            for lag in [0,6]:
                for tk in tks:
                    s,_,_=fit_attribution(y[tk],x,lag,max(60,10*(len(cols)+1)));s.update(ticker=tk,panel=panel,lags=lag);hac.append(s)
            for block_alt in [2,6]:
                aa,bb,cc=joint_model_bootstrap(y,x,block_alt,REPS,SEED)
                aa.assign(panel=panel,block=block_alt).to_csv(OUT/f'monthly_bootstrap_{panel}_block{block_alt}.csv',index=False)
        elif panel!='matched':
            for tk in tks:
                simple,_,_=fit_attribution(y[tk],x[['SPY']],5,252);simple.update(ticker=tk,panel=panel,period='full market-only');stability.append(simple)
                half=len(y)//2
                for label,sl in [('first half',slice(None,half)),('second half',slice(half,None))]:
                    s,cc,_=fit_attribution(y[tk].iloc[sl],x.iloc[sl],5,252);s.update(ticker=tk,panel=panel,period=label,market_beta=cc.loc[cc.factor=='SPY','beta'].iloc[0]);stability.append(s)
    pd.concat(stats).to_csv(OUT/'refitted_model_moments.csv',index=False);pd.concat(pairs).to_csv(OUT/'paired_model_comparisons.csv',index=False)
    pd.concat(coefs).to_csv(OUT/'refitted_contributions.csv',index=False);pd.DataFrame(hac).to_csv(OUT/'hac_sensitivity.csv',index=False)
    pd.DataFrame(stability).to_csv(OUT/'daily_model_stability.csv',index=False)
    # Alpha testing family: four established issuers in the primary long M2 model.
    m=pd.read_csv(OUT/'models.csv');primary=m[(m.panel=='long')&(m.model=='M2')].copy()
    primary['alpha_bh_q']=multipletests(primary.alpha_p,method='fdr_bh')[1]
    primary.to_csv(OUT/'primary_alpha_family.csv',index=False)
    print('Refitted paired model intervals and finite stability checks completed')

if __name__=='__main__':build()
