"""Chronological company-effects pools and a purged three-month sensitivity."""
import numpy as np,pandas as pd
from settings import *
from learning import Regressor,SpecLog,tune,load_frame,feature_sets

def build():
    initialize();d=load_frame();d=d[(d.ticker.isin(CORE))&(d.date>='2015-12-31')].copy()
    _,full=feature_sets();identity=[]
    for tk in CORE[1:]:
        name='company_'+tk;d[name]=(d.ticker==tk).astype(float);identity.append(name)
    records=[];params=[];failures=[];tuning=[];log=SpecLog()
    dates=sorted(d.dropna(subset=['return_target']).date.unique());choices={}
    # Controlled variance matrix: the pooled models reuse the individual models'
    # exact persistence and external column lists and add only company indicators.
    variance_only=[('pooled_variance_persistence','ridge',CONFIG['variance_persistence']+identity),
                   ('pooled_variance_external','ridge',CONFIG['variance_external']+identity)]
    for i in range(84,len(dates)):
        # Folds are synchronised by calendar date: every issuer's row at an origin is
        # forecast by one fit on all issuers' earlier, matured rows.
        date=dates[i];train=d[(d.date<date)&d.return_target.notna()];test=d[(d.date==date)&d.return_target.notna()]
        if test.empty:continue
        refresh=i==84 or date[5:7]=='12'
        for task in ['return','variance']:
            target=task+'_target';tr=train.dropna(subset=[target]);tt=test.dropna(subset=[target])
            models=[('pooled_ridge','ridge',full+identity),('pooled_forest','forest',full+identity),('pooled_boost','boost',full+identity),('panel_company_effects','ols',CONFIG['dynamic_core']+identity)]
            for name,kind,cols in models+(variance_only if task=='variance' else []):
                key=task+'_'+name;y=np.log(tr[target]) if task=='variance' else tr[target]
                try:
                    if refresh or key not in choices:
                        choices[key],trials=tune(kind,tr[cols],y,tr.date.to_numpy(),variance=task=='variance')
                        tuning.extend(dict(ticker='pooled',task=task,window='expanding',date=date,model=name,**x) for x in trials)
                    fit=Regressor(kind,choices[key]).fit(tr[cols],y);pred=fit.predict(tt[cols])
                    if task=='variance':pred=np.exp(pred)*np.mean(np.exp(y-fit.predict(tr[cols])))
                    log.add(fit,task=task,horizon=1,ticker='pooled',model=name,window='expanding',date=date)
                    for (_,row),f in zip(tt.iterrows(),pred):
                        own=tr[tr.ticker==row.ticker]
                        benchmark=float(own.return_target.mean()) if task=='return' else float(row.vol_63**2)
                        records.append(dict(ticker=row.ticker,task=task,horizon=1,window='expanding',model=name,date=date,origin=row.origin,target_end=row.target_end,actual=row[target],prediction=f,benchmark=benchmark,train_n=len(own),pool_n=len(tr),high_vol_regime=row.high_vol_regime,rate_rising_regime=row.rate_rising_regime,fallback=False,hyperparameter=str(choices[key])))
                    if name in ['pooled_ridge','panel_company_effects','pooled_variance_persistence','pooled_variance_external']:params.extend(dict(task=task,date=date,model=name,**x) for x in fit.effects())
                except Exception as e:failures.append(dict(task=task,date=date,model=name,error=str(e)))
            for pair in [('MTRN','ENTG'),('CRS','ATI')]:
                a=tr[tr.ticker.isin(pair)];b=tt[tt.ticker.isin(pair)];key=task+'_pair_'+pair[0]
                y=np.log(a[target]) if task=='variance' else a[target]
                if refresh or key not in choices:
                    choices[key],trials=tune('ridge',a[full+identity],y,a.date.to_numpy(),variance=task=='variance')
                    tuning.extend(dict(ticker='+'.join(pair),task=task,window='expanding',date=date,model='business_pair_ridge',**x) for x in trials)
                fit=Regressor('ridge',choices[key]).fit(a[full+identity],y);pred=fit.predict(b[full+identity])
                if task=='variance':pred=np.exp(pred)*np.mean(np.exp(y-fit.predict(a[full+identity])))
                log.add(fit,task=task,horizon=1,ticker='+'.join(pair),model='business_pair_ridge',window='expanding',date=date)
                for (_,row),f in zip(b.iterrows(),pred):
                    own=a[a.ticker==row.ticker];benchmark=float(own.return_target.mean()) if task=='return' else float(row.vol_63**2)
                    records.append(dict(ticker=row.ticker,task=task,horizon=1,window='expanding',model='business_pair_ridge',date=date,origin=row.origin,target_end=row.target_end,actual=row[target],prediction=f,benchmark=benchmark,train_n=len(own),pool_n=len(a),high_vol_regime=row.high_vol_regime,rate_rising_regime=row.rate_rising_regime,fallback=False,hyperparameter=str(choices[key])))
        if refresh:print('POOLS',date,flush=True)
    pd.DataFrame(records).to_csv(INTERIM/'forecasts_pooled.csv',index=False)
    pd.DataFrame(params).to_csv(OUT/'pooled_parameters.csv',index=False)
    pd.DataFrame(failures).to_csv(INTERIM/'failures_pooled.csv',index=False)

    records=[]
    for tk in CORE:
        z=d[(d.ticker==tk)&d.return_target_3m.notna()].copy();z['end3']=(pd.to_datetime(z.date)+pd.offsets.MonthEnd(3)).dt.strftime('%Y-%m-%d');choices={}
        for _,row in z.iterrows():
            train=z[(z.date<row.date)&(z.end3<=row.date)];test=z.loc[[row.name]]
            # Two additional complete labels ensure >=60 fit observations after inner purging.
            if len(train)<86:continue
            baseline=float(train.return_target_3m.mean())
            for name,kind,cols in [('historical_mean',None,[]),('ridge_full','ridge',full),('forest_full','forest',full),('boost_full','boost',full),('core_ols','ols',CONFIG['dynamic_core'])]:
                if kind is None:f=baseline
                else:
                    if name not in choices or row.date[5:7]=='12':
                        choices[name],trials=tune(kind,train[cols],train.return_target_3m,train.date.to_numpy(),horizon=3)
                        tuning.extend(dict(ticker=tk,task='return',horizon=3,window='expanding',date=row.date,model=name,**x) for x in trials)
                    fit=Regressor(kind,choices[name]).fit(train[cols],train.return_target_3m);f=fit.predict(test[cols])[0]
                    log.add(fit,task='return',horizon=3,ticker=tk,model=name,window='expanding',date=row.date)
                records.append(dict(ticker=tk,task='return',horizon=3,window='expanding',model=name,date=row.date,origin=row.origin,target_end=row.end3,actual=row.return_target_3m,prediction=f,benchmark=baseline,train_n=len(train),train_end=train.end3.max(),high_vol_regime=row.high_vol_regime,rate_rising_regime=row.rate_rising_regime,fallback=False))
        print('HORIZON3',tk,flush=True)
    pd.DataFrame(records).to_csv(INTERIM/'forecasts_horizon3.csv',index=False)
    pd.DataFrame(tuning).to_csv(INTERIM/'tuning_pooled.csv',index=False)
    pd.DataFrame(log.rows).to_csv(INTERIM/'specifications_pooled.csv',index=False)
    pd.DataFrame(log.exclusions).to_csv(INTERIM/'exclusions_pooled.csv',index=False)

if __name__=='__main__':build()
