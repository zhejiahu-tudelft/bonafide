"""Controlled transformations and honest block permutation diagnostics for ML."""
import numpy as np,pandas as pd
from settings import *
from learning import load_frame,Regressor,tune,feature_sets

def build():
    initialize();frame=load_frame();core=CONFIG['dynamic_core'];_,full=feature_sets()
    records=[];importance=[]
    for tk in CORE:
        d=frame[(frame.ticker==tk)&(frame.date>='2015-12-31')].dropna(subset=['return_target']).reset_index(drop=True).copy()
        for c in core:
            if c+'_lag1' not in d:d[c+'_lag1']=d[c].shift(1)
        corepe=[c if c!='earnings_yield' else 'pe' for c in core]
        specs={'core_pe_level':corepe,'core_pe_difference':[c if c!='pe' else 'pe_diff' for c in corepe],
          'core_pe_percentage':[c if c!='pe' else 'pe_pct_change' for c in corepe],
          'core_pe_lag1':[c if c!='pe' else 'pe_lag1' for c in corepe],
          'core_financial_changes':[c+'_diff' if c in ['revenue_growth','operating_margin','earnings_yield'] else c for c in core],
          'distributed_all_lag1':core+[c+'_lag1' for c in core],
          'distributed_all_lag3':core+[c+'_lag1' for c in core]+[c+'_lag3' for c in core]}
        choices={};saved=[]
        for i in range(84,len(d)):
            tr=d.iloc[:i];te=d.iloc[[i]];r=te.iloc[0];base=float(tr.return_target.mean());refresh=i==84 or r.date[5:7]=='12'
            for name,cols in specs.items():
                if refresh or name not in choices:choices[name],_=tune('ridge',tr[cols],tr.return_target,tr.date.to_numpy())
                fit=Regressor('ridge',choices[name]).fit(tr[cols],tr.return_target)
                records.append(dict(ticker=tk,task='return',horizon=1,window='expanding',model=name,date=r.date,origin=r.origin,target_end=r.target_end,actual=r.return_target,prediction=fit.predict(te[cols])[0],benchmark=base,train_n=i,high_vol_regime=r.high_vol_regime,rate_rising_regime=r.rate_rising_regime,fallback=False,hyperparameter=choices[name],selected_features=str(fit.names)))
            # Retain fitted forests for retrospective paired block permutation;
            # permuted forecasts are diagnostics, never part of the real leaderboard.
            if refresh or 'forest' not in choices:choices['forest'],_=tune('forest',tr[full],tr.return_target,tr.date.to_numpy())
            saved.append(Regressor('forest',choices['forest']).fit(tr[full],tr.return_target))
        test=d.iloc[84:];actual=test.return_target.to_numpy();rng=np.random.default_rng(SEED)
        basepred=np.array([model.predict(test.iloc[[j]][full])[0] for j,model in enumerate(saved)])
        base_loss=np.mean((actual-basepred)**2)
        blocks=[np.arange(i,min(i+3,len(test))) for i in range(0,len(test),3)]
        g=__import__('json').loads((OUT/'feature_groups.json').read_text())
        for group in ['financial','valuation','market','momentum','risk','industry','business','transform']:
            cols=[c for c in g[group] if c in full]
            orders=np.array([np.concatenate([blocks[i] for i in rng.permutation(len(blocks))]) for _ in range(20)])
            predictions=np.empty((20,len(test)))
            for j,model in enumerate(saved):
                perturbed=pd.concat([test.iloc[[j]][full]]*20,ignore_index=True)
                perturbed.loc[:,cols]=test.iloc[orders[:,j]][cols].to_numpy()
                predictions[:,j]=model.predict(perturbed)
            deltas=np.mean((actual[None,:]-predictions)**2,axis=1)-base_loss
            importance.append(dict(ticker=tk,model='forest_full',group=group,block_months=3,repeats=20,mean_mse_increase=np.mean(deltas),permutation_sd=np.std(deltas,ddof=1),interpretation='Retrospective grouped block permutation with fitted models held fixed. Can break cross-group dependence; no causal meaning, no prediction claim, no significance interval.'))
        print('TRANSFORMS/PERMUTATION',tk,flush=True)
    pd.DataFrame(records).to_csv(OUT/'forecasts_transformations.csv',index=False)
    pd.DataFrame(importance).to_csv(OUT/'permutation_importance.csv',index=False)

if __name__=='__main__':build()
