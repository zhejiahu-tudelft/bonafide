"""Training-only collinearity and residual diagnostics; descriptive parameter paths."""
import json
import numpy as np,pandas as pd
from statsmodels.stats.diagnostic import acorr_ljungbox
from settings import *
from learning import Regressor,load_frame,feature_sets

def build():
    d=load_frame();_,full=feature_sets();rows=[];corr=[];res=[];vif=[]
    for tk in CORE:
        z=d[(d.ticker==tk)&(d.date>='2015-12-31')].dropna(subset=['return_target']).reset_index(drop=True)
        for n,label in [(84,'initial'),(len(z)-1,'final')]:
            tr=z.iloc[:n]
            for name,cols in [('core',CONFIG['dynamic_core']),('broad',full)]:
                fit=Regressor('ols',0).fit(tr[cols],tr.return_target);x=fit.transform(tr[cols]);sv=np.linalg.svd(np.column_stack([np.ones(n),x]),compute_uv=False)
                rows.append(dict(ticker=tk,fit=label,origin=z.date.iloc[n],specification=name,n=n,p=x.shape[1],rank=np.linalg.matrix_rank(x),condition_number=sv[0]/max(sv[-1],1e-16),note='Broad OLS is a design diagnostic, not a forecast candidate. Condition number includes intercept and missing indicators.'))
                if name=='core':
                    # Variance inflation for the small unpenalised design: how much
                    # each predictor is already explained by the others.
                    for j,column in enumerate(fit.names):
                        others=np.delete(x,j,axis=1)
                        if not others.size:continue
                        design=np.column_stack([np.ones(n),others])
                        residual=x[:,j]-design@np.linalg.lstsq(design,x[:,j],rcond=None)[0]
                        total=float(np.sum((x[:,j]-x[:,j].mean())**2))
                        r2=1-float(np.sum(residual**2))/total if total>1e-18 else np.nan
                        vif.append(dict(ticker=tk,fit=label,specification=name,variable=column,n=n,
                            r2_on_other_predictors=r2,vif=np.nan if not np.isfinite(r2) or r2>=1-1e-12 else 1/(1-r2),
                            note='Training-window VIF for the compact unpenalised design; regularised models are not ranked by it.'))
                if name=='broad':
                    c=pd.DataFrame(x,columns=fit.names).corr()
                    for i,a in enumerate(c.columns):
                        for b in c.columns[i+1:]:
                            if abs(c.at[a,b])>=.9:corr.append(dict(ticker=tk,fit=label,first=a,second=b,correlation=c.at[a,b]))
                else:
                    e=tr.return_target-fit.predict(tr[cols]);lb=acorr_ljungbox(e,lags=[3,6],return_df=True)
                    for lag,row in lb.iterrows():res.append(dict(ticker=tk,fit=label,origin=z.date.iloc[n],n=n,lag=lag,lb_stat=row.lb_stat,diagnostic_pvalue=row.lb_pvalue,note='Unadjusted descriptive residual serial-dependence diagnostic; no model selected using final-fit p-values.'))
    pd.DataFrame(rows).to_csv(OUT/'collinearity_diagnostics.csv',index=False)
    pd.DataFrame(vif).to_csv(OUT/'variance_inflation.csv',index=False)
    pd.DataFrame(corr).to_csv(OUT/'high_predictor_correlations.csv',index=False)
    pd.DataFrame(res).to_csv(OUT/'residual_diagnostics.csv',index=False)
    paths=pd.concat([pd.read_csv(OUT/f'parameter_paths_return_{t}.csv') for t in CORE])
    paths=paths[paths.model=='core_ols'].copy();paths['raw_slope']=paths.effect/paths.scale
    summaries=[]
    for (tk,v),g in paths.groupby(['ticker','variable']):
        summaries.append(dict(ticker=tk,variable=v,origins=len(g),median_standardized_effect=g.effect.median(),q25_standardized_effect=g.effect.quantile(.25),q75_standardized_effect=g.effect.quantile(.75),median_raw_slope=g.raw_slope.median(),positive_fraction=(g.effect>0).mean(),note='Across-refit variability, not a confidence interval. Standardized coefficient is return-fraction change per training SD.'))
    pd.DataFrame(summaries).to_csv(OUT/'coefficient_stability.csv',index=False)
    f=pd.read_csv(OUT/'forecasts.csv');ar=f[(f.model=='arimax')&(f.horizon==1)]
    ar.groupby(['ticker','order'],dropna=False).size().rename('origins').reset_index().to_csv(OUT/'dynamic_order_counts.csv',index=False)
    print('DIAGNOSTICS',len(rows),'designs;',len(res),'residual checks',flush=True)
if __name__=='__main__':build()
