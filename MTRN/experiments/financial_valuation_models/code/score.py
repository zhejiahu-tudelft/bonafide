"""Matched out-of-sample scores, paired loss comparisons and declared inference families."""
import datetime,hashlib,json
import numpy as np,pandas as pd
from settings import *
from inference import paired_inference,reverse,holm,clark_west,detectable_effect,leave_one_out,null_calibration,REPS,ALPHA

RETURN_TASKS=('return','market_relative_return')
BLOCK=CONFIG['bootstrap_block_months'];BLOCKS=sorted([BLOCK]+CONFIG['bootstrap_block_sensitivity'])

def metric_values(g):
    y=g.actual.to_numpy(float);f=g.prediction.to_numpy(float);b=g.benchmark.to_numpy(float);e=y-f
    result=dict(n=len(g),rmse=float(np.sqrt(np.mean(e*e))),mae=float(np.mean(abs(e))),r2_oos=float(1-np.sum(e*e)/np.sum((y-b)**2)) if np.sum((y-b)**2)>0 else np.nan,
       bias=float(np.mean(f-y)),forecast_correlation=float(np.corrcoef(f,y)[0,1]) if np.std(f)>0 and np.std(y)>0 else np.nan,
       fallback_count=int(g.fallback.fillna(False).astype(bool).sum()),start=g.target_end.min(),end=g.target_end.max())
    if g.task.iloc[0] in RETURN_TASKS:
        # Fixed tie convention: np.sign maps an exact zero to 0, so a zero forecast
        # counts as correct only against an exactly zero outcome. Compared below with
        # always-up and with the origin-available benchmark's own direction.
        result.update(directional_accuracy=float(np.mean(np.sign(f)==np.sign(y))),always_up_accuracy=float(np.mean(y>0)),
            benchmark_directional_accuracy=float(np.mean(np.sign(b)==np.sign(y))),zero_forecasts=int(np.sum(f==0)))
    else:
        # Variance is the within-month sample variance of daily returns. The square
        # roots below put errors on a daily-volatility scale; sqrt of a variance
        # forecast is not itself an expected volatility.
        ratio=y/f
        result.update(qlike=float(np.mean(ratio-np.log(ratio)-1)),root_variance_rmse=float(np.sqrt(np.mean((np.sqrt(y)-np.sqrt(f))**2))),root_variance_mae=float(np.mean(abs(np.sqrt(y)-np.sqrt(f)))),root_variance_correlation=float(np.corrcoef(np.sqrt(y),np.sqrt(f))[0,1]))
    return result

def losses(g):
    if g.task.iloc[0] in RETURN_TASKS:return (g.actual-g.prediction).to_numpy()**2
    ratio=(g.actual/g.prediction).to_numpy();return ratio-np.log(ratio)-1

def identical(a,b):
    """Forecasts equal up to floating-point summation noise."""
    a=np.asarray(a,float);b=np.asarray(b,float)
    return np.abs(a-b)<=1e-10*np.maximum(np.abs(a),np.abs(b))+1e-15

def consolidate():
    """Interim per-issuer and per-stage ledgers become single named tables.

    Idempotent: with no interim files present, the consolidated tables already on
    disk are the ledger and are left untouched.
    """
    parts={'forecasts':'forecasts_*.csv','parameter_paths':'parameter_paths_return_*.csv','tuning_history':'tuning_*.csv',
           'model_failures':'failures_*.csv','split_manifest':'splits_return_*.csv','specification_records':'specifications_*.csv',
           'exclusion_log':'exclusions_*.csv'}
    for target,pattern in parts.items():
        files=sorted(INTERIM.glob(pattern))
        if not files:
            if not (OUT/f'{target}.csv').exists():raise FileNotFoundError(f'No interim or consolidated {target}')
            continue
        frames=[pd.read_csv(p).assign(stage=p.stem) for p in files if p.stat().st_size>1]
        frames=[x for x in frames if len(x)]
        combined=pd.concat(frames,ignore_index=True) if frames else pd.DataFrame(columns=['stage'])
        if target=='forecasts':
            combined=combined.drop(columns='stage').sort_values(['task','horizon','ticker','model','date'])
            assert not combined.duplicated(['task','horizon','ticker','model','date']).any()
            assert np.isfinite(combined[['actual','prediction','benchmark']].to_numpy()).all()
        combined.to_csv(OUT/f'{target}.csv',index=False)

def comparison_type(expanded,reduced):
    procedure={'pooled_ridge','pooled_forest','pooled_boost','business_pair_ridge','ridge_rolling84','panel_company_effects',
               'pooled_variance_persistence','pooled_variance_external'}
    if (expanded in procedure)!=(reduced in procedure) or 'ridge_rolling84' in (expanded,reduced):
        return 'complete procedure: different training histories'
    return 'isolating: same history and target'

def build():
    initialize();consolidate()
    d=pd.read_csv(OUT/'forecasts.csv',low_memory=False)
    specs=pd.read_csv(OUT/'specification_records.csv',low_memory=False)
    keys=['task','horizon','ticker','model'];rows=[];regimes=[];rolling=[]
    for key,g in d.groupby(keys):
        identity=dict(zip(keys,key));rows.append(dict(**identity,**metric_values(g)))
        for name in ['high_vol_regime','rate_rising_regime']:
            for state,h in g.groupby(name):regimes.append(dict(**identity,regime=name,value=int(state),**metric_values(h)))
        for year,h in g.groupby(g.target_end.str[:4]):regimes.append(dict(**identity,regime='calendar_year',value=year,**metric_values(h)))
        for j in range(11,len(g)):
            h=g.iloc[j-11:j+1];rolling.append(dict(**identity,date=h.target_end.iloc[-1],window=12,**metric_values(h)))
    scores=pd.DataFrame(rows);scores.to_csv(OUT/'model_scores.csv',index=False)
    # Descriptive per-model view without fallback origins. Pairwise successful-fit
    # comparisons below use each pair's own intersection instead.
    matched=[]
    for key,g in d.groupby(keys):
        clean=g[~g.fallback.fillna(False).astype(bool)]
        if len(clean)>=20:matched.append(dict(**dict(zip(keys,key)),excluded_fallbacks=len(g)-len(clean),**metric_values(clean)))
    pd.DataFrame(matched).to_csv(OUT/'successful_fit_scores.csv',index=False)
    # Three fixed calendar offsets, each containing nonoverlapping three-month
    # outcomes. Report all offsets rather than select the most favorable one; the
    # offsets share months and are not independent replications.
    nonoverlap=[]
    for key,g in d[d.horizon==3].groupby(keys):
        for offset in range(3):
            h=g.sort_values('date').iloc[offset::3]
            nonoverlap.append(dict(**dict(zip(keys,key)),offset=offset,**metric_values(h)))
    pd.DataFrame(nonoverlap).to_csv(OUT/'horizon3_nonoverlapping_scores.csv',index=False)
    pd.DataFrame(regimes).to_csv(OUT/'regime_scores.csv',index=False);pd.DataFrame(rolling).to_csv(OUT/'rolling_scores.csv',index=False)
    # One- and three-month forecasts on the origins both horizons share. The targets
    # differ: the next month versus the next three months.
    common=[]
    for (tk,model),g3 in d[(d.task=='return')&(d.horizon==3)].groupby(['ticker','model']):
        g1=d[(d.task=='return')&(d.horizon==1)&(d.ticker==tk)&(d.model==model)&d.date.isin(g3.date)]
        for horizon,g in [(1,g1),(3,g3[g3.date.isin(g1.date)])]:
            if len(g):common.append(dict(ticker=tk,model=model,horizon=horizon,origins=f'{g.date.min()} to {g.date.max()}',
                target_period='month after the origin' if horizon==1 else 'three months after the origin (overlapping)',**metric_values(g)))
    pd.DataFrame(common).to_csv(OUT/'horizon_common_origin_scores.csv',index=False)

    return_pairs=[('A1_market','historical_mean'),('A2_financial','A1_market'),('A3_valuation','A2_financial'),('A4_momentum','A3_valuation'),('A5_risk','A4_momentum'),('A6_industry','A5_risk'),('A7_business','A6_industry'),('A8_transform','A7_business'),('A9_interaction','A8_transform'),('financial_valuation','financial_only'),
      ('ridge_full','without_valuation'),('ridge_full','without_financial'),('ridge_full','without_market'),('ridge_full','without_momentum'),('ridge_full','without_risk'),('ridge_full','without_industry'),('ridge_full','without_business'),
      ('arimax','arma_static'),('distributed_lag1','core_ridge'),('distributed_lag3','core_ridge'),('forest_full','ridge_full'),('boost_full','ridge_full'),('pooled_ridge','ridge_full'),('pooled_forest','forest_full'),('pooled_boost','boost_full'),('business_pair_ridge','ridge_full'),('ridge_rolling84','ridge_full'),('claims_proxy_sensitivity','ridge_full'),
      ('core_pe_difference','core_pe_level'),('core_pe_percentage','core_pe_level'),('core_pe_lag1','core_pe_level'),('core_financial_changes','core_ridge'),('distributed_all_lag1','core_ridge'),('distributed_all_lag3','core_ridge'),
      ('P1_financial','historical_mean'),('P2_valuation','P1_financial'),('P3_transform','P2_valuation'),('P4_market','P3_transform'),('P5_industry','P4_market'),('P6_business','P5_industry'),('mine_inclusive_fcf','ridge_full'),('zero','historical_mean'),
      ('core_ridge_financial_ext','core_ridge'),('core_ols_financial_ext','core_ols'),('ridge_full','without_equity_inputs'),('arx','core_ols')]
    return_pairs+=[(m,'historical_mean') for m in ['ar1','core_ols','core_ridge','core_financial_changes','ridge_full','lasso_full','elastic_full','forest_full','boost_full','pooled_boost','arimax','core_ridge_financial_ext']]
    variance_pairs=[('ewma94','historical_variance63'),('arch1','historical_variance63'),('garch11','historical_variance63'),('garchx_market','garch11'),('garchx_industry','garchx_market'),('garchx_business','garchx_industry'),('variance_ridge','garch11'),('variance_forest','garch11'),('variance_boost','garch11'),('variance_ridge_market','variance_ridge_persistence'),('variance_ridge_external','variance_ridge_market'),('pooled_ridge','variance_ridge'),('pooled_forest','variance_forest'),('pooled_boost','variance_boost'),('business_pair_ridge','variance_ridge')]
    variance_pairs+=[(e,r) for _,e,r in CONFIG['families']['V20'] if (e,r) not in variance_pairs]
    variance_pairs+=[(m,'historical_variance63') for m in ['pooled_ridge','business_pair_ridge','garchx_industry','variance_ridge','pooled_variance_persistence','pooled_variance_external','variance_ridge_external']]
    comparisons=[];series={}
    for (task,horizon,tk),g in d.groupby(['task','horizon','ticker']):
        for expanded,reduced in (variance_pairs if task=='variance' else return_pairs):
            a=g[g.model==expanded].set_index('date');b=g[g.model==reduced].set_index('date');dates=a.index.intersection(b.index)
            if len(dates)<20:continue
            a=a.loc[dates];b=b.loc[dates];same=identical(a.prediction,b.prediction)
            delta=losses(b)-losses(a);delta[same]=0.
            fell=(a.fallback.fillna(False).astype(bool)|b.fallback.fillna(False).astype(bool)).to_numpy()
            series[(task,horizon,tk,expanded,reduced)]=(pd.Index(dates),a.target_end.to_numpy(),delta)
            samples=[('operational',np.ones(len(delta),bool))]+([('successful_fit',~fell)] if fell.any() else [])
            for sample,keep in samples:
                if keep.sum()<20:continue
                for block in BLOCKS:
                    r=paired_inference(delta[keep],block)
                    comparisons.append(dict(task=task,horizon=horizon,ticker=tk,expanded=expanded,reduced=reduced,sample=sample,
                        comparison_type=comparison_type(expanded,reduced),metric='MSE' if task!='variance' else 'QLIKE',
                        fallback_origins=int(fell.sum()),identical_share=float(same[keep].mean()),**r,
                        interpretation='Positive favours the expanded model. Pointwise interval and unadjusted p-value from one circular block bootstrap; conditional on saved forecasts; exploratory unless in a declared family.'))
    comparisons=pd.DataFrame(comparisons);comparisons.to_csv(OUT/'paired_loss_comparisons.csv',index=False)

    def lookup(task,tk,expanded,reduced,block=BLOCK,horizon=1):
        """A stored comparison, read in either direction with sign and interval reversed."""
        base=comparisons[(comparisons.task==task)&(comparisons.horizon==horizon)&(comparisons.ticker==tk)&(comparisons.block==block)&(comparisons['sample']=='operational')]
        row=base[(base.expanded==expanded)&(base.reduced==reduced)]
        if len(row):return row.iloc[0].to_dict()
        row=base[(base.expanded==reduced)&(base.reduced==expanded)]
        if len(row):
            r=reverse(row.iloc[0].to_dict());r['expanded'],r['reduced']=expanded,reduced;return r
        return None

    def status(task,tk,expanded,reduced):
        key=(task,1,tk,expanded,reduced)
        if key not in series:return 'ineligible',np.nan
        dates,_,delta=series[key]
        a=d[(d.task==task)&(d.horizon==1)&(d.ticker==tk)&(d.model==expanded)].set_index('date').loc[dates]
        b=d[(d.task==task)&(d.horizon==1)&(d.ticker==tk)&(d.model==reduced)].set_index('date').loc[dates]
        share=float(identical(a.prediction,b.prediction).mean())
        if share<1:return 'tested',share
        if 'arimax' in (expanded,reduced):return 'identical_by_selection',share  # every selected order was (0,0)
        def spec(model):
            who='pooled' if model.startswith('pooled_') else tk
            return specs[(specs.task==task)&(specs.horizon==1)&(specs.ticker==who)&(specs.model==model)].set_index('date').reindex(dates)
        sa,sb=spec(expanded),spec(reduced)
        # Exclusion first: if the distinguishing predictors never passed the coverage
        # gate, the contrast was untestable whatever validation then selected.
        if len(sa) and (sa.retained_set.to_numpy()==sb.retained_set.to_numpy()).all():return 'identical_by_exclusion',share
        if len(sa) and sa.intercept_only.eq(True).all() and sb.intercept_only.eq(True).all():return 'identical_by_selection',share
        return 'identical_other',share

    families=[];joint=[]
    declared={'R16':('return',CONFIG['families']['R16']),'V20':('variance',CONFIG['families']['V20'])}
    for family,(task,contrasts) in declared.items():
        for label,expanded,reduced in contrasts:
            for tk in CORE:
                st,share=status(task,tk,expanded,reduced);row=lookup(task,tk,expanded,reduced)
                families.append(dict(family=family,ticker=tk,contrast=label,expanded=expanded,reduced=reduced,status=st,identical_share=share,
                    **({k:row[k] for k in ['n','mean_loss_reduction','lo','hi','pvalue','bootstrap_se','block','replications']} if row else {})))
            # Joint cross-issuer result: equal-weight average differential per calendar
            # month, resampling whole months so all issuers move together.
            parts=[series.get((task,1,tk,expanded,reduced)) for tk in CORE]
            if all(p is not None for p in parts):
                frame=pd.concat([pd.Series(p[2],index=p[1],name=tk) for p,tk in zip(parts,CORE)],axis=1).dropna()
                r=paired_inference(frame.to_numpy(),BLOCK)
                statuses=[x['status'] for x in families if x['family']==family and x['contrast']==label]
                joint.append(dict(family={'R16':'RJ4','V20':'VJ5'}[family],ticker='joint',contrast=label,expanded=expanded,reduced=reduced,
                    status='tested' if any(s=='tested' for s in statuses) else statuses[0],issuers=len(CORE),**{k:r[k] for k in ['n','mean_loss_reduction','lo','hi','pvalue','bootstrap_se','block','replications']}))
                series[(task,1,'joint',expanded,reduced)]=(frame.index,frame.index.to_numpy(),frame.mean(axis=1).to_numpy())
    fam=pd.DataFrame(families+joint)
    for family,g in fam.groupby('family'):
        tested=g[g.status=='tested']
        fam.loc[tested.index,'holm_adjusted_pvalue']=holm(tested.pvalue.to_numpy())
        fam.loc[g.index,'family_tested']=len(tested);fam.loc[g.index,'family_declared']=len(g)
    fam['unadjusted_decision']=np.where(fam.status=='tested',np.where(fam.pvalue<=ALPHA,'interval excludes zero','interval includes zero'),'untested')
    fam['adjusted_decision']=np.where(fam.status=='tested',np.where(fam.holm_adjusted_pvalue<=ALPHA,'survives Holm','does not survive Holm'),'untested')
    fam['note']=('Declared in REVISION_SPEC.md before rescoring. Holm applies within each family to tested rows only; identical forecasts are '
                 'untested contrasts, not evidence of no effect. Adjusted decisions need not match unadjusted interval exclusion.')
    fam.to_csv(OUT/'inference_families.csv',index=False)
    # Traceability view with the version-3 file name and layout.
    fam[fam.family=='R16'].rename(columns={'family':'family_name'}).to_csv(OUT/'primary_comparison_family.csv',index=False)

    # Clark-West: population predictive content of the extra regressors in fixed,
    # nested OLS forecasts. Kept apart from the operational loss comparison.
    cw=[]
    for tk in CORE:
        g=d[(d.task=='return')&(d.horizon==1)&(d.ticker==tk)]
        for big,small in CONFIG['clark_west_pairs']:
            a=g[g.model==big].set_index('date');b=g[g.model==small].set_index('date');dates=a.index.intersection(b.index)
            if len(dates)<20:continue
            cw.append(dict(ticker=tk,larger=big,smaller=small,**clark_west(a.loc[dates].actual,b.loc[dates].prediction,a.loc[dates].prediction),
                interpretation='One-sided test that the extra regressors have population predictive content; not a test of sample forecast accuracy and not applied to tuned models.'))
    pd.DataFrame(cw).to_csv(OUT/'clark_west.csv',index=False)

    # Size of the paired test under a null that mimics each series' tails and dependence.
    # Declared series first. The supplementary dense series (amendment 1 in
    # revision_freeze.json) is reported beside them and does not enter the rule.
    calibration=[]
    for role,task,(e,r) in [('declared','return',CONFIG['calibration']['return_pair']),('declared','variance',CONFIG['calibration']['variance_pair']),
                            ('supplementary','return',CONFIG['calibration']['supplementary_return_pair'])]:
        for tk in CORE:
            key=(task,1,tk,e,r)
            if key not in series:continue
            nonzero=float(np.mean(series[key][2]!=0))
            for block in BLOCKS:
                calibration.append(dict(series_role=role,task=task,ticker=tk,expanded=e,reduced=r,block=block,nonzero_share=nonzero,
                    **null_calibration(series[key][2],block,CONFIG['calibration']['simulations'])))
    calibration=pd.DataFrame(calibration)
    limit=CONFIG['calibration']['descriptive_only_if_size_above']
    worst=calibration[(calibration.block==BLOCK)&(calibration.series_role=='declared')].groupby('task').empirical_size.max()
    calibration['task_primary_block_max_size']=calibration.task.map(worst)
    calibration['inference_status']=np.where(calibration.task_primary_block_max_size>limit,'descriptive only (size above declared limit)','formal inference supported at the declared limit')
    calibration['rule']=f'Declared rule: p-values for a task are descriptive only if the largest issuer-level empirical size at the {BLOCK}-month block exceeds {limit}.'
    calibration.to_csv(OUT/'inference_calibration.csv',index=False)

    # Smallest mean loss reduction detectable with 80% power at 5% (normal approximation).
    mde=[]
    for (task,horizon,tk,e,r),(dates,_,delta) in series.items():
        if horizon!=1 or tk=='joint':continue
        in_family=any(e==x[1] and r==x[2] for x in CONFIG['families']['R16']+CONFIG['families']['V20'])
        if not (in_family or r in ('historical_mean','historical_variance63')):continue
        res=lookup(task,tk,e,r)
        bench='historical_mean' if task!='variance' else 'historical_variance63'
        scale=d[(d.task==task)&(d.horizon==1)&(d.ticker==tk)&(d.model==bench)&d.date.isin(dates)]
        scale=float(losses(scale).mean()) if len(scale) else np.nan
        effect=detectable_effect(res['bootstrap_se'])
        mde.append(dict(task=task,ticker=tk,expanded=e,reduced=r,n=res['n'],observed_mean_loss_reduction=res['mean_loss_reduction'],bootstrap_se=res['bootstrap_se'],
            detectable_loss_reduction=effect,benchmark_mean_loss=scale,detectable_in_benchmark_units=effect/scale if scale else np.nan,
            note='80% power, two-sided 5%, normal approximation with the bootstrap SE taken as known. For returns the last column is OOS R-squared points relative to the historical mean.'))
    pd.DataFrame(mde).to_csv(OUT/'detectable_effects.csv',index=False)

    # Loss-only influence: forecasts and fitted models held fixed; not a refit test.
    influence=[]
    watched={('return','ridge_full','historical_mean'),('return','core_ols','historical_mean'),('return','boost_full','historical_mean'),('return','arimax','historical_mean'),
             ('variance','pooled_ridge','historical_variance63'),('variance','business_pair_ridge','historical_variance63'),('variance','garch11','historical_variance63'),
             ('variance','pooled_variance_external','historical_variance63'),('variance','variance_ridge_external','historical_variance63')}
    watched|={('return',e,r) for _,e,r in CONFIG['families']['R16']}|{('variance',e,r) for _,e,r in CONFIG['families']['V20']}
    for (task,horizon,tk,e,r),(dates,ends,delta) in series.items():
        if horizon!=1 or (task,e,r) not in watched:continue
        months=pd.Series(ends).astype(str).str[:7].to_numpy();years=np.array([m[:4] for m in months])
        for level,labels in [('target_month',months),('calendar_year',years)]:
            full,rows=leave_one_out(delta,labels,BLOCK)
            for x in rows:influence.append(dict(task=task,ticker=tk,expanded=e,reduced=r,level=level,full_mean=full['mean_loss_reduction'],full_pvalue=full['pvalue'],**x))
    influence=pd.DataFrame(influence)
    influence['named_check']=np.where((influence.level=='target_month')&(((influence.ticker=='MTRN')&(influence.excluded=='2024-08'))|((influence.ticker=='ENTG')&(influence.excluded=='2025-04'))),'revision-named month','')
    influence['basis']='Evaluation months removed with forecasts held fixed; training samples and fitted models unchanged.'
    influence.to_csv(OUT/'influence_diagnostics.csv',index=False)

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
    intercept=specs[(specs.task=='return')&(specs.horizon==1)].groupby(['ticker','model']).intercept_only.mean()
    ablation=[]
    for ladder,steps in ladders.items():
        for stage,previous in steps:
            for _,s in scores[(scores.task=='return')&(scores.horizon==1)&(scores.model==stage)].iterrows():
                paired=lookup('return',s.ticker,stage,previous) if previous else None
                ablation.append(dict(ladder=ladder,stage=stage,compared_with=previous,ticker=s.ticker,n=int(s.n),
                    predictors=0 if stage=='historical_mean' else len(stages.get(stage,full)),rmse=s.rmse,mae=s.mae,r2_oos=s.r2_oos,
                    intercept_only_share=float(intercept.get((s.ticker,stage),np.nan)),
                    mean_loss_reduction=None if paired is None else float(paired['mean_loss_reduction']),
                    lo=None if paired is None else float(paired['lo']),hi=None if paired is None else float(paired['hi']),
                    pvalue=None if paired is None else float(paired['pvalue']),
                    sign_convention='loss(compared_with) minus loss(stage); positive favours the stage. For leave-one-block-out, positive means the model without the block forecast better.'))
    pd.DataFrame(ablation).to_csv(OUT/'ablation_scores.csv',index=False)
    freeze=json.loads((ROOT/'revision_freeze.json').read_text())
    (OUT/'scoring_run.json').write_text(json.dumps(dict(scored_at=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
        spec_sha256=hashlib.sha256((ROOT/freeze['spec']).read_bytes()).hexdigest(),bootstrap_replications=REPS,
        blocks=BLOCKS,primary_block=BLOCK),indent=2)+'\n')
    print('SCORED',len(d),'forecasts;',len(scores),'score rows;',len(comparisons),'paired block contrasts',flush=True)

if __name__=='__main__':build()
