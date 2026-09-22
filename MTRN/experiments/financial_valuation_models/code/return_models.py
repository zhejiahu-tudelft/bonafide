"""Expanding-window return forecasts, baselines, ablations and dynamic models."""
import argparse,hashlib,json,warnings
import numpy as np,pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
from settings import *
from learning import Regressor,SpecLog,tune,load_frame,feature_sets

def dynamic_forecast(train,test,cols,order,target='return_target'):
    prep=Regressor('ols',0).fit(train[cols],train[target])
    x=prep.transform(train[cols]);xx=prep.transform(test[cols])
    # Omit missing indicators from this compact unpenalized specification if needed.
    parameters=x.shape[1]+sum(order)+2
    if len(train)<5*parameters:raise ValueError('Dynamic parameter sample gate')
    y=train[target].to_numpy()*100
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        fit=SARIMAX(y,exog=np.column_stack([np.ones(len(x)),x]),order=(order[0],0,order[1]),trend='n',enforce_stationarity=True,enforce_invertibility=True).fit(disp=False,maxiter=100)
    if not fit.mle_retvals.get('converged',True):raise ValueError('ARMA maximum likelihood did not converge')
    pred=float(fit.forecast(1,exog=np.column_stack([np.ones(len(xx)),xx]))[0])/100
    # Ten training observations per estimated parameter is the preferred workflow
    # threshold; five is the hard floor. Fits in between are reported, not hidden.
    return pred,dict(aic=float(fit.aic),bic=float(fit.bic),parameters=len(fit.params),order=str(order),
        limited_sample=bool(len(train)<10*parameters),observations_per_parameter=round(len(train)/parameters,2),
        selected_features=json.dumps(prep.names))

def select_order(train,cols):
    # Same scheme as every other tuned model: at each of the last 24 origins, refit
    # the full ARMA-error regression on labels matured by that origin and forecast it.
    trials=[];origins=train.date.iloc[-24:].tolist()
    for p,q in CONFIG['arima_orders']:
        losses=[]
        for v in origins:
            a=train[(train.date<v)&(train.target_end<=v)];t=train[train.date==v]
            try:pred,_=dynamic_forecast(a,t,cols,[p,q]);losses.append((float(t.return_target.iloc[0])-pred)**2)
            except Exception:losses.append(np.inf)
        trials.append(dict(order=[p,q],validation_loss=float(np.mean(losses)),inner_origins=len(origins),first_inner_origin=origins[0]))
    finite=[x for x in trials if np.isfinite(x['validation_loss'])]
    return min(finite,key=lambda x:(x['validation_loss'],sum(x['order'])))['order'] if finite else [0,0],trials

def run(ticker):
    initialize();frame=load_frame();d=frame[(frame.ticker==ticker)&(frame.date>='2015-12-31')].dropna(subset=['return_target']).reset_index(drop=True).copy()
    stages,full=feature_sets();core=CONFIG['dynamic_core'];extension=core+CONFIG['financial_extension']
    specs={'core_ols':('ols',core),'core_ridge':('ridge',core),'arx':('ols',core+['momentum_1']),
      'ridge_full':('ridge',full),'lasso_full':('lasso',full),'elastic_full':('elastic',full),'forest_full':('forest',full),'boost_full':('boost',full),
      'distributed_lag1':('ridge',core+[c+'_lag1' for c in core if c+'_lag1' in d]),
      'distributed_lag3':('ridge',core+[c+'_lag1' for c in core if c+'_lag1' in d]+[c+'_lag3' for c in core]),
      'ar1':('ols',['momentum_1']),
      # Post-hoc exploratory group, declared in REVISION_SPEC.md before rescoring.
      'core_ridge_financial_ext':('ridge',extension),'core_ols_financial_ext':('ols',extension)}
    specs.update({name:('ridge',cols) for name,cols in stages.items()})
    if ticker!='MTRN':specs.pop('mine_inclusive_fcf',None)  # Only MTRN reports mine development.
    # Only Entegris uses the consolidated-equity substitution; matched exclusion shows
    # how much the conclusions depend on it.
    if ticker=='ENTG':specs['without_equity_inputs']=('ridge',[c for c in full if c not in CONFIG['equity_inputs']])
    forecasts=[];parameters=[];tuning=[];failures=[];splits=[];choices={};order=[0,0];log=SpecLog()
    d['market_relative_target']=d.return_target-d.market_target
    relative_specs={'historical_mean':(None,[]),'zero':(None,[]),'core_ridge':('ridge',core),'ridge_full':('ridge',full),'boost_full':('boost',full)}
    for i in range(84,len(d)):
        train=d.iloc[:i];test=d.iloc[[i]];row=test.iloc[0]
        # Month-end labels can fall on weekends; the month is complete at its
        # last exchange close. Compare calendar labels, audit actual closes too.
        if train.target_end.max()>row.date:raise AssertionError('Unmatured training target')
        refresh=i==84 or row.date[5:7]=='12'
        baseline=float(train.return_target.mean());mkt=float(train.market_target.tail(12).mean())
        cap_beta=np.linalg.lstsq(np.column_stack([np.ones(i),train.market_target]),train.return_target,rcond=None)[0]
        def record(name,pred,**extra):
            forecasts.append(dict(ticker=ticker,task='return',horizon=1,window='expanding',model=name,date=row.date,origin=row.origin,target_end=row.target_end,actual=row.return_target,prediction=float(pred),benchmark=baseline,train_n=i,train_start=train.date.iloc[0],train_end=train.target_end.iloc[-1],high_vol_regime=row.high_vol_regime,rate_rising_regime=row.rate_rising_regime,fallback=False,**extra))
        record('historical_mean',baseline);record('zero',0.);record('market_mean',mkt);record('capm_style',cap_beta[0]+cap_beta[1]*mkt)
        splits.append(dict(ticker=ticker,date=row.date,origin=row.origin,target_end=row.target_end,train_start=train.date.iloc[0],train_target_end=train.target_end.iloc[-1],train_n=i,inner_first_origin=train.date.iloc[-24],inner_last_origin=train.date.iloc[-1],retuned=refresh))
        for name,(kind,cols) in specs.items():
            cols=[c for c in cols if c in d]
            if refresh or name not in choices:
                choices[name],trials=tune(kind,train[cols],train.return_target,train.date.to_numpy())
                tuning.extend(dict(ticker=ticker,task='return',window='expanding',date=row.date,model=name,**x) for x in trials)
            try:
                fit=Regressor(kind,choices[name]).fit(train[cols],train.return_target)
                pred=fit.predict(test[cols])[0];record(name,pred,hyperparameter=str(choices[name]),selected_features=json.dumps(fit.names))
                log.add(fit,task='return',horizon=1,ticker=ticker,model=name,window='expanding',date=row.date)
                if name in ['core_ols','core_ridge','ridge_full','lasso_full','elastic_full','forest_full','boost_full','core_ols_financial_ext']:
                    parameters.extend(dict(ticker=ticker,date=row.date,model=name,hyperparameter=str(choices[name]),**x) for x in fit.effects())
            except Exception as e:
                record(name,baseline,failure=str(e));forecasts[-1]['fallback']=True;failures.append(dict(ticker=ticker,date=row.date,model=name,error=str(e)))
        if refresh:
            order,trials=select_order(train,core);tuning.extend(dict(ticker=ticker,task='return',window='expanding',date=row.date,model='arimax',**x) for x in trials)
        for name,chosen in [('arma_static',[0,0]),('arimax',order)]:
            try:pred,info=dynamic_forecast(train,test,core,chosen);record(name,pred,**info)
            except Exception as e:record(name,baseline,failure=str(e));forecasts[-1]['fallback']=True;failures.append(dict(ticker=ticker,date=row.date,model=name,error=str(e)))
        # Prespecified rolling-window sensitivity: same targets, only the last 84
        # months, and its own hyperparameter chosen inside that window.
        tr=train.tail(84)
        try:
            if refresh or 'ridge_rolling84' not in choices:
                choices['ridge_rolling84'],trials=tune('ridge',tr[full],tr.return_target,tr.date.to_numpy())
                tuning.extend(dict(ticker=ticker,task='return',window='rolling84',date=row.date,model='ridge_rolling84',train_rows=len(tr),**x) for x in trials)
            fit=Regressor('ridge',choices['ridge_rolling84']).fit(tr[full],tr.return_target)
            record('ridge_rolling84',fit.predict(test[full])[0],hyperparameter=str(choices['ridge_rolling84']))
            log.add(fit,task='return',horizon=1,ticker=ticker,model='ridge_rolling84',window='rolling84',date=row.date)
        except Exception as e:
            record('ridge_rolling84',float(tr.return_target.mean()),failure=str(e));forecasts[-1]['fallback']=True
            failures.append(dict(ticker=ticker,date=row.date,model='ridge_rolling84',error=str(e)))
        forecasts[-1]['window']='rolling84';forecasts[-1]['train_n']=len(tr);forecasts[-1]['train_start']=tr.date.iloc[0]
        # Secondary target: the stock's return minus SPY's return over the identical
        # month. A market-relative return, not alpha and not a risk-adjusted return.
        # The future market return belongs to the outcome, never to the predictors.
        if np.isfinite(row.market_relative_target) and train.market_relative_target.notna().all():
            relative_base=float(train.market_relative_target.mean())
            for name,(kind,cols) in relative_specs.items():
                cols=[c for c in cols if c in d]
                try:
                    if kind is None:pred=0. if name=='zero' else relative_base
                    else:
                        key='relative_'+name
                        if refresh or key not in choices:
                            choices[key],trials=tune(kind,train[cols],train.market_relative_target,train.date.to_numpy())
                            tuning.extend(dict(ticker=ticker,task='market_relative_return',window='expanding',date=row.date,model=name,**x) for x in trials)
                        fit=Regressor(kind,choices[key]).fit(train[cols],train.market_relative_target)
                        pred=fit.predict(test[cols])[0]
                        log.add(fit,task='market_relative_return',horizon=1,ticker=ticker,model=name,window='expanding',date=row.date)
                    fallback=False
                except Exception as e:
                    pred=relative_base;fallback=True;failures.append(dict(ticker=ticker,date=row.date,model='relative_'+name,error=str(e)))
                forecasts.append(dict(ticker=ticker,task='market_relative_return',horizon=1,window='expanding',model=name,date=row.date,
                    origin=row.origin,target_end=row.target_end,actual=row.market_relative_target,prediction=float(pred),benchmark=relative_base,
                    train_n=i,train_start=train.date.iloc[0],train_end=train.target_end.iloc[-1],
                    high_vol_regime=row.high_vol_regime,rate_rising_regime=row.rate_rising_regime,fallback=fallback))
        if refresh:print('RETURNS',ticker,row.target_end,'n',i,'order',order,flush=True)
    for name,records in [('forecasts',forecasts),('parameter_paths',parameters),('tuning',tuning),('failures',failures),('splits',splits),
                         ('specifications',log.rows),('exclusions',log.exclusions)]:
        pd.DataFrame(records).to_csv(INTERIM/f'{name}_return_{ticker}.csv',index=False)
    print('RETURN COMPLETE',ticker,len(forecasts),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--ticker',choices=CORE);a=p.parse_args()
    for tk in [a.ticker] if a.ticker else CORE:run(tk)
