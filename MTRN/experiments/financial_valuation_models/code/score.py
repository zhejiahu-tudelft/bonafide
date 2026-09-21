"""Matched out-of-sample scores and paired, dependent loss comparisons."""
import numpy as np,pandas as pd
from settings import *
from common.code.attribution_statistics import block_indices

def metric_values(g):
    y=g.actual.to_numpy(float);f=g.prediction.to_numpy(float);b=g.benchmark.to_numpy(float);e=y-f
    result=dict(n=len(g),rmse=float(np.sqrt(np.mean(e*e))),mae=float(np.mean(abs(e))),r2_oos=float(1-np.sum(e*e)/np.sum((y-b)**2)) if np.sum((y-b)**2)>0 else np.nan,
       bias=float(np.mean(f-y)),forecast_correlation=float(np.corrcoef(f,y)[0,1]) if np.std(f)>0 and np.std(y)>0 else np.nan,
       fallback_count=int(g.fallback.fillna(False).astype(bool).sum()),start=g.target_end.min(),end=g.target_end.max())
    if g.task.iloc[0] in ('return','excess_return'):
        # Fixed tie convention: np.sign maps an exact zero to 0, so a zero forecast
        # counts as correct only against an exactly zero outcome. Compared below with
        # always-up and with the origin-available benchmark's own direction.
        result.update(directional_accuracy=float(np.mean(np.sign(f)==np.sign(y))),always_up_accuracy=float(np.mean(y>0)),
            benchmark_directional_accuracy=float(np.mean(np.sign(b)==np.sign(y))),zero_forecasts=int(np.sum(f==0)))
    else:
        ratio=y/f
        result.update(qlike=float(np.mean(ratio-np.log(ratio)-1)),volatility_rmse=float(np.sqrt(np.mean((np.sqrt(y)-np.sqrt(f))**2))),volatility_mae=float(np.mean(abs(np.sqrt(y)-np.sqrt(f)))),volatility_correlation=float(np.corrcoef(np.sqrt(y),np.sqrt(f))[0,1]))
    return result

def losses(g):
    if g.task.iloc[0] in ('return','excess_return'):return (g.actual-g.prediction).to_numpy()**2
    ratio=(g.actual/g.prediction).to_numpy();return ratio-np.log(ratio)-1

def holm(pvalues):
    """Holm step-down adjustment over one declared family of comparisons."""
    order=np.argsort(pvalues);m=len(pvalues);adjusted=np.empty(m);running=0.
    for rank,idx in enumerate(order):
        running=max(running,min(1.,(m-rank)*pvalues[idx]));adjusted[idx]=running
    return adjusted

def build():
    initialize();files=[OUT/f'forecasts_return_{t}.csv' for t in CORE]+[OUT/'forecasts_variance.csv',OUT/'forecasts_pooled.csv',OUT/'forecasts_horizon3.csv',OUT/'forecasts_transformations.csv']
    d=pd.concat([pd.read_csv(p) for p in files],ignore_index=True);d=d.sort_values(['task','horizon','ticker','model','date'])
    assert not d.duplicated(['task','horizon','ticker','model','date']).any()
    assert np.isfinite(d[['actual','prediction','benchmark']].to_numpy()).all()
    d.to_csv(OUT/'forecasts.csv',index=False)
    keys=['task','horizon','ticker','model'];rows=[];regimes=[];rolling=[]
    for key,g in d.groupby(keys):
        identity=dict(zip(keys,key));rows.append(dict(**identity,**metric_values(g)))
        for name in ['high_vol_regime','rate_rising_regime']:
            for state,h in g.groupby(name):regimes.append(dict(**identity,regime=name,value=int(state),**metric_values(h)))
        for year,h in g.groupby(g.target_end.str[:4]):regimes.append(dict(**identity,regime='calendar_year',value=year,**metric_values(h)))
        for j in range(11,len(g)):
            h=g.iloc[j-11:j+1];rolling.append(dict(**identity,date=h.target_end.iloc[-1],window=12,**metric_values(h)))
    scores=pd.DataFrame(rows);scores.to_csv(OUT/'model_scores.csv',index=False)
    # Operational performance above includes fallback forecasts. The matched
    # successful-fit view re-scores the same models on origins where no model in the
    # pair fell back, so a failure cannot masquerade as a modelling result.
    matched=[]
    for key,g in d.groupby(keys):
        clean=g[~g.fallback.fillna(False).astype(bool)]
        if len(clean)>=20:matched.append(dict(**dict(zip(keys,key)),excluded_fallbacks=len(g)-len(clean),**metric_values(clean)))
    pd.DataFrame(matched).to_csv(OUT/'successful_fit_scores.csv',index=False)
    # Three fixed calendar offsets, each containing nonoverlapping three-month
    # outcomes. Report all offsets rather than select the most favorable one.
    nonoverlap=[]
    for key,g in d[d.horizon==3].groupby(keys):
        for offset in range(3):
            h=g.sort_values('date').iloc[offset::3]
            nonoverlap.append(dict(**dict(zip(keys,key)),offset=offset,**metric_values(h)))
    pd.DataFrame(nonoverlap).to_csv(OUT/'horizon3_nonoverlapping_scores.csv',index=False)
    pd.DataFrame(regimes).to_csv(OUT/'regime_scores.csv',index=False);pd.DataFrame(rolling).to_csv(OUT/'rolling_scores.csv',index=False)
    comparisons=[]
    return_pairs=[('A1_market','historical_mean'),('A2_financial','A1_market'),('A3_valuation','A2_financial'),('A4_momentum','A3_valuation'),('A5_risk','A4_momentum'),('A6_industry','A5_risk'),('A7_business','A6_industry'),('A8_transform','A7_business'),('A9_interaction','A8_transform'),('financial_valuation','financial_only'),('ridge_full','without_valuation'),('ridge_full','without_financial'),('ridge_full','without_market'),('ridge_full','without_industry'),('ridge_full','without_business'),('arimax','arma_static'),('distributed_lag1','core_ridge'),('distributed_lag3','core_ridge'),('forest_full','ridge_full'),('boost_full','ridge_full'),('pooled_ridge','ridge_full'),('pooled_forest','forest_full'),('pooled_boost','boost_full'),('business_pair_ridge','ridge_full'),('ridge_rolling84','ridge_full'),('claims_proxy_sensitivity','ridge_full')]
    return_pairs += [('core_pe_difference','core_pe_level'),('core_pe_percentage','core_pe_level'),('core_pe_lag1','core_pe_level'),('core_financial_changes','core_ridge'),('distributed_all_lag1','core_ridge'),('distributed_all_lag3','core_ridge')]
    variance_pairs=[('ewma94','historical_variance63'),('arch1','historical_variance63'),('garch11','historical_variance63'),('garchx_market','garch11'),('garchx_industry','garchx_market'),('garchx_business','garchx_industry'),('variance_ridge','garch11'),('variance_forest','garch11'),('variance_boost','garch11'),('variance_ridge_market','variance_ridge_persistence'),('variance_ridge_external','variance_ridge_market'),('pooled_ridge','variance_ridge'),('pooled_forest','variance_forest'),('pooled_boost','variance_boost'),('business_pair_ridge','variance_ridge')]
    return_pairs += [('P1_financial','historical_mean'),('P2_valuation','P1_financial'),('P3_transform','P2_valuation'),('P4_market','P3_transform'),('P5_industry','P4_market'),('P6_business','P5_industry'),('mine_inclusive_fcf','ridge_full'),('zero','historical_mean')]
    return_pairs += [(m,'historical_mean') for m in ['ar1','core_ridge','core_financial_changes','ridge_full','forest_full','boost_full','pooled_boost','arimax']]
    variance_pairs += [(m,'historical_variance63') for m in ['pooled_ridge','business_pair_ridge','garchx_industry','variance_ridge']]
    for (task,horizon,tk),g in d.groupby(['task','horizon','ticker']):
        for expanded,reduced in (variance_pairs if task=='variance' else return_pairs):
            a=g[g.model==expanded].set_index('date');b=g[g.model==reduced].set_index('date');dates=a.index.intersection(b.index)
            if len(dates)<20:continue
            a=a.loc[dates];b=b.loc[dates];delta=losses(b)-losses(a)
            for block in [3,6,12]:
                idx=block_indices(len(delta),min(block,len(delta)),2000,np.random.default_rng(SEED))
                draws=delta[idx].mean(axis=1)
                # Two-sided resampling p-value: how often a recentred block-resampled
                # mean loss difference is at least as extreme as the observed one.
                centred=draws-draws.mean()
                pvalue=float((np.sum(np.abs(centred)>=abs(delta.mean()))+1)/(len(draws)+1))
                comparisons.append(dict(task=task,horizon=horizon,ticker=tk,expanded=expanded,reduced=reduced,n=len(delta),metric='MSE' if task!='variance' else 'QLIKE',mean_loss_reduction=float(delta.mean()),lo=float(np.quantile(draws,.025)),hi=float(np.quantile(draws,.975)),block=block,replications=2000,pvalue=pvalue,interpretation='Positive favors expanded model. Approximate pointwise conditional block interval; no multiplicity-adjusted discovery claim.'))
    comparisons=pd.DataFrame(comparisons);comparisons.to_csv(OUT/'paired_loss_comparisons.csv',index=False)
    # Four one-month-return contrasts per eligible issuer, frozen before scoring.
    # Everything else in this study is exploratory and is labelled as such.
    family=[('valuation_added','ridge_full','without_valuation','Does starting valuation add information to otherwise identical controls?'),
            ('transformations_vs_levels','core_pe_difference','core_pe_level','Do changes improve on the level representation of the same variable?'),
            ('arma_vs_static','arimax','arma_static','Does an AR/MA error process improve on the same static inputs?'),
            ('lags_vs_static','distributed_all_lag1','core_ridge','Do older predictor observations improve on the latest ones?')]
    primary=[]
    for tk in CORE:
        for label,expanded,reduced,question in family:
            row=comparisons[(comparisons.task=='return')&(comparisons.horizon==1)&(comparisons.ticker==tk)&(comparisons.expanded==expanded)&(comparisons.reduced==reduced)&(comparisons.block==6)]
            if row.empty:
                primary.append(dict(ticker=tk,contrast=label,question=question,expanded=expanded,reduced=reduced,eligible=False,reason='Matched forecasts unavailable for this issuer'))
                continue
            row=row.iloc[0]
            # Identical forecasts on both sides mean the contrast could not be run:
            # the distinguishing predictor failed the training coverage gate.
            degenerate=bool(row.lo==0 and row.hi==0 and row.mean_loss_reduction==0)
            primary.append(dict(ticker=tk,contrast=label,question=question,expanded=expanded,reduced=reduced,eligible=True,
                n=int(row.n),mean_loss_reduction=float(row.mean_loss_reduction),lo=float(row.lo),hi=float(row.hi),pvalue=float(row.pvalue),
                degenerate=degenerate,
                note_row='Both specifications produced identical forecasts because the distinguishing predictor failed the training coverage gate; this is an untested contrast, not a measured null.' if degenerate else ''))
    primary=pd.DataFrame(primary)
    valid=primary.eligible & primary.pvalue.notna()
    primary.loc[valid,'holm_adjusted_pvalue']=holm(primary.loc[valid,'pvalue'].to_numpy())
    primary['family_size']=int(valid.sum())
    primary['note']='Prespecified family of four contrasts per eligible established issuer; Holm adjustment applies within this family only. Block-resampling p-values are approximate for nested comparisons in a 44-month sample.'
    primary.to_csv(OUT/'primary_comparison_family.csv',index=False)
    # Equal-company average of benchmark-normalized MSE; avoid a volatile issuer dominating.
    aggregate=scores.groupby(['task','horizon','model']).agg(companies=('ticker','nunique'),mean_r2_oos=('r2_oos','mean'),mean_rmse=('rmse','mean'),mean_mae=('mae','mean'),mean_qlike=('qlike','mean')).reset_index()
    aggregate.to_csv(OUT/'aggregate_scores.csv',index=False)
    score_summary=[]
    for (task,horizon,tk),g in scores.groupby(['task','horizon','ticker']):
        criterion='qlike' if task=='variance' else 'rmse';best=g.sort_values(criterion).iloc[0]
        score_summary.append(dict(task=task,horizon=horizon,ticker=tk,best_observed_model=best.model,selection_metric=criterion,best_score=best[criterion],n=best.n,interpretation='Retrospective best observed score among tested pipelines, not a prospectively validated winner.'))
    pd.DataFrame(score_summary).to_csv(OUT/'observed_leaderboard.csv',index=False)
    # Ablation view: both cumulative ladders and the leave-one-block-out checks, with
    # the paired incremental change that the ordered ladder alone cannot establish.
    from learning import feature_sets
    stages,full=feature_sets()
    ladders={'market_first':[('historical_mean',None)]+[(n,p) for n,p in zip(['A1_market','A2_financial','A3_valuation','A4_momentum','A5_risk','A6_industry','A7_business','A8_transform','A9_interaction'],['historical_mean','A1_market','A2_financial','A3_valuation','A4_momentum','A5_risk','A6_industry','A7_business','A8_transform'])],
             'protocol_order':[('historical_mean',None)]+[(n,p) for n,p in zip(['P1_financial','P2_valuation','P3_transform','P4_market','P5_industry','P6_business'],['historical_mean','P1_financial','P2_valuation','P3_transform','P4_market','P5_industry'])],
             'leave_one_block_out':[('ridge_full',None)]+[('without_'+b,'ridge_full') for b in ['market','financial','valuation','momentum','risk','industry','business']]}
    ablation=[]
    for ladder,steps in ladders.items():
        for stage,previous in steps:
            row=scores[(scores.task=='return')&(scores.horizon==1)&(scores.model==stage)]
            for _,s in row.iterrows():
                paired=comparisons[(comparisons.task=='return')&(comparisons.horizon==1)&(comparisons.ticker==s.ticker)&(comparisons.expanded==stage)&(comparisons.reduced==previous)&(comparisons.block==6)]
                paired=paired.iloc[0] if len(paired) else None
                ablation.append(dict(ladder=ladder,stage=stage,compared_with=previous,ticker=s.ticker,n=int(s.n),
                    predictors=0 if stage=='historical_mean' else len(stages.get(stage,full)),rmse=s.rmse,mae=s.mae,r2_oos=s.r2_oos,
                    mean_loss_reduction=None if paired is None else float(paired.mean_loss_reduction),
                    lo=None if paired is None else float(paired.lo),hi=None if paired is None else float(paired.hi),
                    sign_convention='loss_reduced minus loss_expanded; positive favours the expanded stage'))
    pd.DataFrame(ablation).to_csv(OUT/'ablation_scores.csv',index=False)
    # Named artifacts in the protocol are single consolidated tables.
    for target,pattern in [('split_manifest','splits_return_*.csv'),('parameter_paths','parameter_paths_return_*.csv'),('model_failures','failures_return_*.csv'),('tuning_history','tuning_return_*.csv')]:
        parts=[pd.read_csv(p) for p in sorted(OUT.glob(pattern)) if p.stat().st_size>1]
        combined=pd.concat(parts,ignore_index=True) if parts else pd.DataFrame()
        if target=='model_failures':
            for extra in ['variance_failures.csv','pooled_failures.csv']:
                p=OUT/extra
                if p.exists() and p.stat().st_size>1:combined=pd.concat([combined,pd.read_csv(p).assign(stage=extra[:-4])],ignore_index=True)
        combined.to_csv(OUT/f'{target}.csv',index=False)
    print('SCORED',len(d),'forecasts;',len(scores),'score rows;',len(comparisons),'paired block contrasts',flush=True)

if __name__=='__main__':build()
