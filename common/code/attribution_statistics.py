"""First/second moments, paired block uncertainty, and transparent OLS attribution."""
import numpy as np
import pandas as pd
import statsmodels.api as sm

def complete_week_returns(daily,sessions,cutoff):
    """Compound only complete Friday-ending weeks on the supplied market calendar.

    The calendar must cover the first week's opening, including sessions before
    the data start. Holiday weeks need fewer observations; missing prices do not.
    A bin whose Friday label is beyond the effective cutoff remains incomplete.
    """
    end=pd.Timestamp(cutoff).normalize()
    calendar=pd.DatetimeIndex(sessions).sort_values().unique()
    calendar=calendar[calendar<=end]
    d=daily.sort_index().loc[:end]
    if not d.index.is_unique or not d.index.isin(calendar).all():
        raise ValueError('Daily returns must have unique observed market sessions')
    if d.empty:return d.copy()
    expected=pd.Series(1,index=calendar).resample('W-FRI').sum()
    observed=d.resample('W-FRI').count()
    complete=observed.eq(expected.reindex(observed.index),axis=0).all(axis=1)
    weekly=(1+d).resample('W-FRI').prod(min_count=1)-1
    return weekly.loc[complete & (weekly.index<=end)]

def block_indices(n,length,reps,rng):
    if n<2 or not 1<=length<=n: raise ValueError('Invalid block/sample size')
    starts=rng.integers(0,n-length+1,size=(reps,int(np.ceil(n/length))))
    return (starts[:,:,None]+np.arange(length)).reshape(reps,-1)[:,:n]

def bootstrap_moments(frame,block=10,reps=2000,seed=1):
    """All columns share dates and resampled indices. No IID independence claim."""
    d=frame.dropna();x=d.to_numpy(float);n,k=x.shape
    if n<max(20,2*block): raise ValueError('Insufficient observations for block intervals')
    rng=np.random.default_rng(seed);means=[];variances=[]
    for first in range(0,reps,50):
        idx=block_indices(n,block,min(50,reps-first),rng);sample=x[idx]
        means.append(sample.mean(axis=1));variances.append(sample.var(axis=1,ddof=1))
    means=np.vstack(means);variances=np.vstack(variances)
    rows=[];pairs=[]
    for j,name in enumerate(d.columns):
        v=x[:,j].var(ddof=1);lo,hi=np.quantile(variances[:,j],[.025,.975]);ml,mh=np.quantile(means[:,j],[.025,.975])
        rows.append(dict(ticker=name,n=n,start=str(d.index[0].date()),end=str(d.index[-1].date()),
                         mean=x[:,j].mean(),mean_se=means[:,j].std(ddof=1),mean_lo=ml,mean_hi=mh,
                         variance=v,var_lo=lo,var_hi=hi,volatility=np.sqrt(v),vol_lo=np.sqrt(lo),vol_hi=np.sqrt(hi),
                         lag1_autocorrelation=d[name].autocorr(1),block=block,reps=reps))
        if name!='MTRN' and 'MTRN' in d.columns:
            i=d.columns.get_loc('MTRN');diff=means[:,i]-means[:,j];ratio=variances[:,i]/variances[:,j]
            pairs.append(dict(peer=name,n=n,start=str(d.index[0].date()),end=str(d.index[-1].date()),
                mean_difference=x[:,i].mean()-x[:,j].mean(),mean_diff_lo=np.quantile(diff,.025),mean_diff_hi=np.quantile(diff,.975),
                variance_ratio=x[:,i].var(ddof=1)/v,variance_ratio_lo=np.quantile(ratio,.025),variance_ratio_hi=np.quantile(ratio,.975),
                volatility_ratio=np.sqrt(x[:,i].var(ddof=1)/v),vol_ratio_lo=np.sqrt(np.quantile(ratio,.025)),vol_ratio_hi=np.sqrt(np.quantile(ratio,.975))))
    return pd.DataFrame(rows),pd.DataFrame(pairs)

def fit_attribution(y,factors,lags=3,min_n=60):
    data=pd.concat([y.rename('response'),factors],axis=1).dropna();n=len(data);p=len(factors.columns)+1
    if n<min_n: raise ValueError(f'Insufficient sample: {n} < {min_n}')
    X=sm.add_constant(data[factors.columns],has_constant='add');Y=data.response
    if np.linalg.matrix_rank(X.to_numpy())!=p: raise ValueError('Rank-deficient model')
    fit=sm.OLS(Y,X).fit(cov_type='HAC',cov_kwds={'maxlags':lags,'use_correction':True})
    fitted=fit.fittedvalues;resid=fit.resid
    variance=Y.var(ddof=1);explained=fitted.var(ddof=1);unexplained=resid.var(ddof=1)
    se=fit.bse;ci=fit.conf_int();coef=[]
    for name in X.columns:
        coef.append(dict(factor=name,beta=fit.params[name],se=se[name],lo=ci.loc[name,0],hi=ci.loc[name,1],p_value=fit.pvalues[name],
                         mean_factor=1. if name=='const' else data[name].mean(),mean_contribution=fit.params[name]*(1 if name=='const' else data[name].mean())))
    scaled=(data[factors.columns]-data[factors.columns].mean())/data[factors.columns].std(ddof=0)
    summary=dict(n=n,parameters=p,start=str(data.index[0].date()),end=str(data.index[-1].date()),
        mean_excess=Y.mean(),alpha=fit.params['const'],alpha_lo=ci.loc['const',0],alpha_hi=ci.loc['const',1],alpha_p=fit.pvalues['const'],
        r2=fit.rsquared,adjusted_r2=fit.rsquared_adj,total_variance=variance,fitted_variance=explained,residual_variance=unexplained,
        residual_share=unexplained/variance,residual_volatility=np.sqrt(unexplained),residual_mse=fit.ssr/(n-p),
        condition_scaled=np.linalg.cond(np.column_stack([np.ones(n),scaled])),mean_residual=resid.mean(),
        mean_identity_error=abs(Y.mean()-sum(c['mean_contribution'] for c in coef)),variance_identity_error=abs(variance-explained-unexplained))
    return summary,pd.DataFrame(coef),pd.DataFrame(dict(actual=Y,fitted=fitted,residual=resid))

def bootstrap_model(y,factors,block=3,reps=2000,seed=1):
    d=pd.concat([y.rename('y'),factors],axis=1).dropna();Y=d.y.to_numpy();X=np.column_stack([np.ones(len(d)),d[factors.columns].to_numpy()])
    rng=np.random.default_rng(seed);stats=[];p=X.shape[1]
    for idx in block_indices(len(d),block,reps,rng):
        a=X[idx];b=Y[idx]
        if np.linalg.matrix_rank(a)<p: continue
        beta=np.linalg.lstsq(a,b,rcond=None)[0];e=b-a@beta;v=np.var(b,ddof=1)
        stats.append([beta[0],np.var(e,ddof=1),np.sqrt(np.var(e,ddof=1)),1-np.var(e,ddof=1)/v])
    s=np.asarray(stats)
    if len(s)<.95*reps: raise ValueError('Too many singular bootstrap fits')
    result={'bootstrap_valid':len(s)}
    for j,name in enumerate(['alpha_boot','residual_var_boot','residual_vol_boot','r2_boot']):
        result[name+'_lo'],result[name+'_hi']=np.quantile(s[:,j],[.025,.975])
    return result

def session_for_release(sessions,date,after_close=True):
    date=pd.Timestamp(date).normalize();i=sessions.searchsorted(date,side='right' if after_close else 'left')
    return sessions[i] if i<len(sessions) else pd.NaT

def event_car(stock,market,session,window=(-1,1),min_history=160):
    factors=market.rename('market').to_frame() if isinstance(market,pd.Series) else market
    d=pd.concat([stock.rename('stock'),factors],axis=1).dropna();pos=d.index.get_indexer([pd.Timestamp(session)])[0]
    if pos<0: raise ValueError('Event outside price coverage')
    if pos+window[0]<0 or pos+window[1]>=len(d): raise ValueError('Incomplete event window')
    hist=d.iloc[max(0,pos-252):pos-20]
    if len(hist)<min_history: raise ValueError('Insufficient pre-event history')
    X=np.column_stack([np.ones(len(hist)),hist[factors.columns]]);beta=np.linalg.lstsq(X,hist.stock,rcond=None)[0]
    event=d.iloc[pos+window[0]:pos+window[1]+1]
    ar=event.stock-np.column_stack([np.ones(len(event)),event[factors.columns]])@beta
    return dict(car=ar.sum(),n_estimation=len(hist),estimation_start=str(hist.index[0].date()),estimation_end=str(hist.index[-1].date()),
                window_start=str(event.index[0].date()),window_end=str(event.index[-1].date()),market_beta=beta[1])

def joint_model_bootstrap(responses,factors,block=3,reps=2000,seed=1):
    """Refit every issuer on synchronized blocks; estimate paired model contrasts."""
    d=responses.join(factors).dropna();names=list(responses.columns);fnames=['const']+list(factors.columns)
    X=np.column_stack([np.ones(len(d)),d[factors.columns]]);Y=d[names].to_numpy();p=X.shape[1]
    def statistics(a,b):
        beta=np.linalg.lstsq(a,b,rcond=None)[0];res=b-a@beta
        return beta,np.var(res,axis=0,ddof=1),beta*a.mean(axis=0)[:,None]
    beta,v,contribution=statistics(X,Y);bs=[];vs=[];cs=[]
    for idx in block_indices(len(d),block,reps,np.random.default_rng(seed)):
        if np.linalg.matrix_rank(X[idx])<p:continue
        b,w,c=statistics(X[idx],Y[idx]);bs.append(b);vs.append(w);cs.append(c)
    bs=np.array(bs);vs=np.array(vs);cs=np.array(cs)
    if len(bs)<.95*reps:raise ValueError('Too many singular joint model bootstrap samples')
    summaries=[];contrasts=[];coefficients=[]
    for j,tk in enumerate(names):
        summaries.append(dict(ticker=tk,n=len(d),intercept=beta[0,j],intercept_lo=np.quantile(bs[:,0,j],.025),intercept_hi=np.quantile(bs[:,0,j],.975),
                              residual_variance=v[j],residual_var_lo=np.quantile(vs[:,j],.025),residual_var_hi=np.quantile(vs[:,j],.975),
                              residual_volatility=np.sqrt(v[j]),residual_vol_lo=np.sqrt(np.quantile(vs[:,j],.025)),residual_vol_hi=np.sqrt(np.quantile(vs[:,j],.975))))
        for k,f in enumerate(fnames):
            coefficients.append(dict(ticker=tk,factor=f,beta=beta[k,j],beta_boot_lo=np.quantile(bs[:,k,j],.025),beta_boot_hi=np.quantile(bs[:,k,j],.975),
                                     contribution=contribution[k,j],contribution_lo=np.quantile(cs[:,k,j],.025),contribution_hi=np.quantile(cs[:,k,j],.975)))
        if tk!='MTRN' and 'MTRN' in names:
            i=names.index('MTRN');delta=bs[:,0,i]-bs[:,0,j];ratio=vs[:,i]/vs[:,j]
            contrasts.append(dict(peer=tk,n=len(d),intercept_difference=beta[0,i]-beta[0,j],intercept_diff_lo=np.quantile(delta,.025),intercept_diff_hi=np.quantile(delta,.975),
                                  residual_variance_ratio=v[i]/v[j],variance_ratio_lo=np.quantile(ratio,.025),variance_ratio_hi=np.quantile(ratio,.975),
                                  residual_volatility_ratio=np.sqrt(v[i]/v[j]),volatility_ratio_lo=np.sqrt(np.quantile(ratio,.025)),volatility_ratio_hi=np.sqrt(np.quantile(ratio,.975))))
    return pd.DataFrame(summaries),pd.DataFrame(contrasts),pd.DataFrame(coefficients)
