"""Separate monthly realized-variance forecasts from daily volatility models."""
import warnings
import numpy as np,pandas as pd
from scipy.optimize import minimize
from scipy.signal import lfilter
from settings import *
from learning import Regressor,tune,load_frame,feature_sets
from arch import arch_model

def variance_filter(shocks,z,parameters,initial):
    omega,alpha,beta=parameters[:3];gamma=np.asarray(parameters[3:])
    v=np.empty(len(shocks));v[0]=initial
    forcing=omega+alpha*shocks[:-1]**2+z[:-1]@gamma
    v[1:]=lfilter([1.],[1.,-beta],forcing,zi=[beta*initial])[0]
    return v

def fit_garchx(returns,z,horizon):
    r=np.asarray(returns)*100;mu=r.mean();shocks=r-mu
    z=np.asarray(z,float);scale=np.maximum(np.mean(z,axis=0),1e-10);x=z/scale
    initial=max(float(np.var(shocks)),1e-5);k=x.shape[1]
    def objective(p):
        v=variance_filter(shocks,x,p,initial)
        if np.any(v<=0) or not np.isfinite(v).all():return 1e20
        return .5*np.mean(np.log(v)+shocks**2/v)
    start=np.r_[initial*.05,.08,.85,np.full(k,initial*.02/k)]
    fit=minimize(objective,start,method='SLSQP',bounds=[(1e-8,initial*10),(.00001,.995),(.00001,.995)]+[(0,initial*10)]*k,
        constraints=[dict(type='ineq',fun=lambda p:.995-p[1]-p[2])],options={'maxiter':180,'ftol':1e-9})
    if not fit.success:raise ValueError('GARCH-X did not converge: '+fit.message)
    p=fit.x;v=variance_filter(shocks,x,p,initial);expected=x[-21:].mean(axis=0)
    forecasts=[];h=p[0]+p[1]*shocks[-1]**2+p[2]*v[-1]+x[-1]@p[3:]
    for j in range(horizon):
        forecasts.append(h)
        h=p[0]+(p[1]+p[2])*h+expected@p[3:]
    return float(np.mean(forecasts))/10000,dict(omega=p[0],alpha=p[1],beta=p[2],gamma=list(p[3:]),external_scale=list(scale),loglike=-len(r)*objective(p))

def garch_forecast(r,horizon,arch=False):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        fit=arch_model(r.to_numpy()*100,mean='Constant',vol='ARCH' if arch else 'GARCH',p=1,q=0 if arch else 1,rescale=False).fit(disp='off',show_warning=False)
    if fit.convergence_flag!=0:raise ValueError('ARCH/GARCH failed to converge')
    forecast=fit.forecast(horizon=horizon,reindex=False).residual_variance.iloc[-1].mean()/10000
    return float(forecast),dict(aic=float(fit.aic),bic=float(fit.bic),**fit.params.to_dict())

def run():
    initialize();frame=load_frame();_,full=feature_sets()
    daily=pd.read_csv(OUT/'daily_returns.csv',index_col=0,parse_dates=True)
    records=[];parameters=[];failures=[];tuning=[]
    for tk in CORE:
        d=frame[(frame.ticker==tk)&(frame.date>='2015-12-31')].dropna(subset=['variance_target']).reset_index(drop=True)
        industry='SOXX' if tk in ['MTRN','ENTG'] else 'ITA';driver='HG=F' if tk=='MTRN' else 'NG=F'
        specs={'variance_ridge':('ridge',full),'variance_forest':('forest',full),'variance_boost':('boost',full),
               'variance_ridge_persistence':('ridge',['vol_21','vol_63','vol_252']),
               'variance_ridge_market':('ridge',['vol_21','vol_63','vol_252','market_vol','vix','yield_10y_change']),
               'variance_ridge_external':('ridge',['vol_21','vol_63','vol_252','market_vol','vix','industry_vol','driver_vol','yield_10y_change'])}
        choices={}
        for i in range(84,len(d)):
            train=d.iloc[:i];test=d.iloc[[i]];row=test.iloc[0];origin=pd.Timestamp(row.origin)
            past=daily[tk].loc[:origin].dropna();r=past.tail(CONFIG['garch_training_days'])
            baseline=float(past.tail(63).var(ddof=1))
            horizon=len(daily.SPY.loc[(daily.index>origin)&(daily.index<=pd.Timestamp(row.target_end))].dropna())
            if horizon<15:raise ValueError('Incomplete target month')
            def record(name,pred,**extra):
                # A variance forecast must be strictly positive for QLIKE. An invalid
                # value falls back to the recorded persistence benchmark rather than
                # aborting the run or silently dropping an unfavourable test month.
                if not np.isfinite(pred) or pred<=0:
                    failures.append(dict(ticker=tk,date=row.date,model=name,error=f'Invalid variance forecast {pred!r}; persistence fallback used'))
                    pred=baseline;extra=dict(extra,fallback=True)
                records.append(dict(ticker=tk,task='variance',horizon=1,window='expanding',model=name,date=row.date,origin=row.origin,target_end=row.target_end,actual=row.variance_target,prediction=float(pred),benchmark=baseline,train_n=i,high_vol_regime=row.high_vol_regime,rate_rising_regime=row.rate_rising_regime,**dict(dict(fallback=False),**extra)))
            record('historical_variance63',baseline);record('historical_variance21',past.tail(21).var(ddof=1));record('historical_variance252',past.tail(252).var(ddof=1))
            # Center using information in the fit window, no outcome-period mean.
            shocks=(r-r.mean()).to_numpy();v=float(np.var(shocks[:min(63,len(shocks))]))
            for e in shocks:v=.94*v+.06*e*e
            record('ewma94',v)
            base_garch=baseline
            for name,is_arch in [('arch1',True),('garch11',False)]:
                try:
                    value,info=garch_forecast(r,horizon,is_arch);record(name,value)
                    if name=='garch11':base_garch=value
                    parameters.append(dict(ticker=tk,date=row.date,model=name,**info))
                except Exception as e:
                    record(name,baseline);records[-1]['fallback']=True;failures.append(dict(ticker=tk,date=row.date,model=name,error=str(e)))
            for name,xcols in [('garchx_market',['SPY']),('garchx_industry',['SPY',industry]),('garchx_business',['SPY',industry,driver])]:
                try:
                    # Keep the identical stock-session training window. A missing
                    # external quote carries its last observed proxy, never deletes
                    # a stock return or compresses the GARCH recursion's clock.
                    z=daily[xcols].reindex(daily.SPY.dropna().index).ffill()
                    if driver in xcols:z[driver]=z[driver].shift(1)
                    joined=pd.concat([r.rename('stock'),z],axis=1,sort=True).loc[r.index]
                    if joined.isna().any().any():raise ValueError('Unavailable external history on common stock sessions')
                    value,info=fit_garchx(joined.stock, (joined[xcols]*100)**2,horizon)
                    record(name,value);parameters.append(dict(ticker=tk,date=row.date,model=name,**info))
                except Exception as e:
                    record(name,base_garch);records[-1]['fallback']=True;failures.append(dict(ticker=tk,date=row.date,model=name,error=str(e)))
            refresh=i==84 or row.date[5:7]=='12'
            for name,(kind,cols) in specs.items():
                y=np.log(train.variance_target.to_numpy())
                try:
                    if refresh or name not in choices:
                        choices[name],trials=tune(kind,train[cols],y,train.date.to_numpy(),variance=True)
                        tuning.extend(dict(ticker=tk,date=row.date,model=name,**x) for x in trials)
                    fit=Regressor(kind,choices[name]).fit(train[cols],y)
                    smear=float(np.mean(np.exp(y-fit.predict(train[cols]))))
                    pred=float(np.exp(fit.predict(test[cols])[0])*smear)
                    record(name,pred,hyperparameter=choices[name],smearing=smear)
                    if name in ['variance_ridge','variance_forest','variance_boost']:
                        parameters.extend(dict(ticker=tk,date=row.date,model=name,**x) for x in fit.effects())
                except Exception as e:
                    record(name,baseline);records[-1]['fallback']=True;failures.append(dict(ticker=tk,date=row.date,model=name,error=str(e)))
            if refresh:print('VARIANCE',tk,row.target_end,'daily training',len(r),flush=True)
        print('VARIANCE COMPLETE',tk,flush=True)
    for name,rows in [('forecasts_variance',records),('variance_parameters',parameters),('variance_failures',failures),('variance_tuning',tuning)]:
        pd.DataFrame(rows).to_csv(OUT/f'{name}.csv',index=False)

if __name__=='__main__':run()
