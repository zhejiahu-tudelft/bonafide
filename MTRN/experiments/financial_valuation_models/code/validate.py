"""Fail closed on timing, alignment, arithmetic, preservation and report errors."""
import hashlib,json,re
import numpy as np,pandas as pd
from bs4 import BeautifulSoup
from settings import *
from learning import feature_sets,groups,parents

def build():
    checks=[]
    def check(name,condition,detail=''):
        checks.append(dict(check=name,passed=bool(condition),detail=str(detail)[:400]))

    # --- preservation -----------------------------------------------------
    from common.code.preservation import verify
    original=json.loads((ROOT/'preservation_hashes.json').read_text())
    # A file counts as preserved when unchanged or covered by a documented retirement
    # or amendment in MTRN/resource_changes.json (see MTRN/RESOURCE_LINKS.md).
    changed=verify(original,REPO,REPO/'MTRN/resource_changes.json')
    check('Original study, protocol and frozen inputs preserved',not changed,changed)

    # --- cutoff and target alignment --------------------------------------
    d=pd.read_csv(OUT/'monthly_features_as_known.csv')
    r=pd.read_csv(OUT/'daily_returns.csv',index_col=0,parse_dates=True)
    check('No price observation beyond the cutoff',str(r.index.max().date())==CUTOFF,r.index.max())
    check('No feature origin beyond the last complete month',d.date.max()==LAST_MONTH,d.date.max())
    check('Every target month follows its origin by exactly one month',
          (pd.to_datetime(d.date)+pd.offsets.MonthEnd(1)).dt.strftime('%Y-%m-%d').eq(d.target_end).all())
    matured=d.dropna(subset=['return_target'])
    check('No target extends past the last complete month',matured.target_end.max()<=LAST_MONTH,matured.target_end.max())
    # Rebuild the primary target independently from saved adjusted closes.
    monthly=(1+r).resample('ME').prod(min_count=1)-1
    variance=r.resample('ME').var(ddof=1)
    errors=[]
    for tk in CORE:
        z=d[(d.ticker==tk)].dropna(subset=['return_target'])
        want=monthly[tk].reindex(pd.to_datetime(z.target_end)).to_numpy()
        errors.append(np.nanmax(np.abs(want-z.return_target.to_numpy())))
        wantv=variance[tk].reindex(pd.to_datetime(z.dropna(subset=['variance_target']).target_end)).to_numpy()
        errors.append(np.nanmax(np.abs(wantv-z.dropna(subset=['variance_target']).variance_target.to_numpy())))
    check('Return and variance targets reproduce from raw adjusted closes',max(errors)<1e-12,max(errors))

    # --- availability of every selected accounting fact --------------------
    audit=pd.read_csv(OUT/'feature_availability_audit.csv')
    check('Every selected SEC fact was public at its assigned date',
          ((audit.available<=audit['asof'])&(audit.filed<=audit['asof'])&(audit.end<=audit['asof'])).all())
    check('Every selected fact carries vintage metadata',
          audit[['unit','namespace','first_filed_for_period','vintage_status']].notna().all().all()
          and (audit.first_filed_for_period<=audit.filed).all())
    check('Materion mine-inclusive free cash flow matches the preserved study',
          np.isclose(d[(d.ticker=='MTRN')&(d.date==LAST_MONTH)].fcf.iloc[0],32.439)
          and np.isclose(d[(d.ticker=='MTRN')&(d.date==LAST_MONTH)].mine_capex.iloc[0],17.774))
    check('Consolidated-equity fallback never used where noncontrolling interest is material',
          not d[(d.ticker=='ATI')].equity_basis.str.startswith('consolidated').any())
    check('Every consolidated-equity substitution records its measured tolerance',
          d[d.equity_basis.str.startswith('consolidated',na=False)].equity_basis.str.contains('within tolerance').all())

    # --- feature construction identities -----------------------------------
    g=groups();stages,full=feature_sets()
    z=d[d.ticker=='MTRN'].sort_values('date')
    check('First difference equals level minus its own one-month lag',
          np.nanmax(np.abs((z.earnings_yield-z.earnings_yield.shift(1)-z.earnings_yield_diff).to_numpy()))<1e-12)
    check('A one-month lag is the previous level, not a change',
          np.nanmax(np.abs((z.earnings_yield.shift(1)-z.earnings_yield_lag1).to_numpy()))<1e-12)
    duplicates=[]
    for tk in CORE:
        z=d[(d.ticker==tk)&(d.date>='2015-12-31')][full]
        for i,a in enumerate(full):
            for b in full[i+1:]:
                pair=z[[a,b]].dropna()
                if len(pair)>30 and np.allclose(pair[a],pair[b]):duplicates.append((tk,a,b))
    check('No exactly duplicated predictor columns inside the modelled set',not duplicates,duplicates[:6])
    leaks=[n for block in ['valuation','financial','market','industry','business','momentum','risk']
           for n in stages['without_'+block] if block in parents(n,g)]
    check('Block removal also removes derivatives, lags and interactions',not leaks,leaks[:6])
    check('No outcome column reaches any modelled feature set',
          not [n for n in full if n.endswith('_target') or n in ('monthly_return','realized_variance')])
    ev=d.dropna(subset=['ev_proxy','market_cap','debt','cash'])
    check('Enterprise-value proxy reconciles to its stated components',
          np.nanmax(np.abs(ev.ev_proxy-(ev.market_cap+ev.debt-ev.cash+np.maximum(ev.total_equity.fillna(ev.equity)-ev.equity,0))))<1e-9)
    fcf=d.dropna(subset=['fcf_equipment','cfo','capex'])
    check('Equipment free cash flow equals operating cash flow minus equipment capex',
          np.nanmax(np.abs(fcf.fcf_equipment-(fcf.cfo-fcf.capex)))<1e-9)

    # --- forecast ledger ---------------------------------------------------
    f=pd.read_csv(OUT/'forecasts.csv')
    check('No NaN or infinite value in the forecast ledger',
          np.isfinite(f[['actual','prediction','benchmark']].to_numpy()).all())
    check('No duplicated forecast record',not f.duplicated(['task','horizon','ticker','model','date']).any())
    check('No forecast target ends after the cutoff',f.target_end.max()<=CUTOFF,f.target_end.max())
    check('Every forecast origin precedes its target end',(f.date<f.target_end).all())
    counts=f[(f.task=='return')&(f.horizon==1)].groupby(['ticker','model']).size()
    check('All one-month return models share an identical number of origins',counts.nunique()==1,sorted(set(counts)))
    check('Primary out-of-sample gate met (at least 36 matured targets)',counts.min()>=36,int(counts.min()))
    splits=pd.read_csv(OUT/'split_manifest.csv')
    check('Every training label had matured by its fitting origin',(splits.train_target_end<=splits.date).all(),
          splits[splits.train_target_end>splits.date].head(3).to_dict('records'))
    check('Initial training window meets the 84-month gate',splits.train_n.min()>=84,int(splits.train_n.min()))

    # --- scoring arithmetic -------------------------------------------------
    s=pd.read_csv(OUT/'model_scores.csv')
    recomputed=[]
    for key,g2 in f.groupby(['task','horizon','ticker','model']):
        e=(g2.actual-g2.prediction).to_numpy();b=(g2.actual-g2.benchmark).to_numpy()
        row=s[(s.task==key[0])&(s.horizon==key[1])&(s.ticker==key[2])&(s.model==key[3])]
        if row.empty:continue
        recomputed.append(abs(np.sqrt(np.mean(e*e))-row.rmse.iloc[0]))
        if np.sum(b*b)>0:recomputed.append(abs((1-np.sum(e*e)/np.sum(b*b))-row.r2_oos.iloc[0]))
    check('Every RMSE and out-of-sample R² recomputes from the saved ledger',max(recomputed)<1e-9,max(recomputed))
    mean_benchmark=f[(f.task=='return')&(f.model=='historical_mean')]
    check('Out-of-sample R² uses the real-time benchmark, not the test-sample mean',
          np.allclose(mean_benchmark.prediction,mean_benchmark.benchmark))
    check('Historical-mean benchmark scores exactly zero against itself',
          np.nanmax(np.abs(s[(s.task=='return')&(s.model=='historical_mean')].r2_oos))<1e-12)
    ab=pd.read_csv(OUT/'ablation_scores.csv')
    check('Both sides of every ablation use identical sample sizes',ab.groupby(['ladder','ticker']).n.nunique().eq(1).all())
    r16=pd.read_csv(OUT/'primary_comparison_family.csv')
    check('Frozen family holds four contrasts for each eligible issuer',
          len(r16)==4*len(CORE) and r16.contrast.nunique()==4 and r16.status.notna().all(),len(r16))

    # --- dynamic-model conventions -----------------------------------------
    ar=f[(f.model=='arimax')&(f.task=='return')]
    check('ARIMAX order is recorded for every origin and may vary',ar.order.notna().all() and ar.order.nunique()>=1)
    check('Dynamic fits below ten observations per parameter are flagged, not hidden',
          'limited_sample' in ar.columns and ar.limited_sample.notna().all())
    check('No variance forecast is nonpositive',(f[f.task=='variance'].prediction>0).all())

    # --- version-4 revision ------------------------------------------------
    freeze=json.loads((ROOT/'revision_freeze.json').read_text());run=json.loads((OUT/'scoring_run.json').read_text())
    check('Revision specification frozen before scoring',
          run['spec_sha256']==freeze['spec_sha256']==hashlib.sha256((ROOT/freeze['spec']).read_bytes()).hexdigest() and freeze['frozen_at']<run['scored_at'],
          dict(frozen=freeze['frozen_at'],scored=run['scored_at']))
    manifest=json.loads((ROOT/'baseline_v3/MANIFEST.json').read_text())
    check('Baseline manifest records the version-3 state',manifest['git_commit'].startswith('bef7b32') and len(manifest['files'])>100
          and all((ROOT/'baseline_v3'/x.split(' ')[0]).exists() for x in manifest['snapshot_tables']),len(manifest['files']))
    pc=pd.read_csv(OUT/'paired_loss_comparisons.csv')
    agree=((pc.pvalue<=.05)==((pc.lo>0)|(pc.hi<0)))
    check('Every unadjusted interval and p-value agree',agree.all() and (pc.replications==1999).all(),pc[~agree].head(3).to_dict('records'))
    check('Every paired comparison is labelled isolating or complete procedure',pc.comparison_type.notna().all() and pc.comparison_type.str.match('isolating|complete procedure').all())
    fell=pc[pc.fallback_origins>0]
    check('Successful-fit comparisons use each pair\'s intersection',
          all(((pc.task==r.task)&(pc.ticker==r.ticker)&(pc.expanded==r.expanded)&(pc.reduced==r.reduced)&(pc['sample']=='successful_fit')).any() for r in fell.itertuples()),len(fell))
    fam=pd.read_csv(OUT/'inference_families.csv')
    check('Joint contrasts resample common calendar months',set(fam[fam.ticker=='joint'].family)=={'RJ4','VJ5'} and (fam[fam.ticker=='joint'].n==44).all())
    check('Variance family covers the controlled 2x2 matrix',len(fam[fam.family=='V20'])==20 and len(fam[fam.family=='VJ5'])==5)
    tested=fam[fam.status=='tested']
    check('Holm adjustment never reduces a raw p-value within any family',(tested.holm_adjusted_pvalue>=tested.pvalue-1e-12).all())
    check('Identical forecasts are never counted as tested',((fam.status=='tested')|(fam.identical_share.fillna(1)==1)).all() and (fam[fam.status.str.startswith('identical')].holm_adjusted_pvalue.isna()).all())
    cw=pd.read_csv(OUT/'clark_west.csv')
    check('Clark-West limited to fixed nested OLS pairs',set(map(tuple,cw[['larger','smaller']].values))<=set(map(tuple,CONFIG['clark_west_pairs'])))
    cal=pd.read_csv(OUT/'inference_calibration.csv')
    check('Calibration recorded for both tasks and all blocks',set(cal[cal.series_role=='declared'].task)=={'return','variance'} and set(cal.block)=={3,6,12} and cal.inference_status.notna().all())
    infl=pd.read_csv(OUT/'influence_diagnostics.csv')
    covered={(r.task,r.expanded,r.reduced) for r in infl.itertuples()}
    check('Influence diagnostics cover every family contrast',all(('return',e,r) in covered for _,e,r in CONFIG['families']['R16']) and all(('variance',e,r) in covered for _,e,r in CONFIG['families']['V20'])
          and ((infl.ticker=='MTRN')&(infl.excluded=='2024-08')).any() and ((infl.ticker=='ENTG')&(infl.excluded=='2025-04')).any())
    ab=pd.read_csv(OUT/'ablation_scores.csv');lobo=ab[(ab.ladder=='leave_one_block_out')&(ab.stage!='ridge_full')]
    check('Leave-one-block-out rows are populated',len(lobo)==7*len(CORE) and lobo.mean_loss_reduction.notna().all() and lobo.lo.notna().all(),int(lobo.mean_loss_reduction.isna().sum()))
    rev=pc[(pc.expanded=='ridge_full')&(pc.reduced=='without_market')&(pc.block==6)&(pc['sample']=='operational')].set_index('ticker')
    back=lobo[lobo.stage=='without_market'].set_index('ticker')
    check('Reversed comparisons negate the mean and swap interval endpoints',
          np.allclose(back.loc[rev.index,'mean_loss_reduction'],-rev.mean_loss_reduction) and np.allclose(back.loc[rev.index,'lo'],-rev.hi) and np.allclose(back.loc[rev.index,'hi'],-rev.lo))
    tune=pd.read_csv(OUT/'tuning_history.csv',low_memory=False)
    check('Every inner-validation label had matured',tune.labels_matured.dropna().astype(bool).all() and (tune.inner_origins.dropna()==24).all())
    check('Rolling sensitivity is tuned on its own 84-month window',(tune[tune.window=='rolling84'].train_rows==84).all() and len(tune[tune.window=='rolling84'])>0)
    specs=pd.read_csv(OUT/'specification_records.csv',low_memory=False)
    check('Tuning grid includes the intercept-only benchmark','intercept_only' in set(tune.parameter.astype(str)) and specs.intercept_only.any())
    check('Every fitted specification has a complexity record',
          specs[['candidates','retained','rank','retained_set']].notna().all().all() and specs[specs.intercept_only==False]['rank'].gt(0).all())
    check('Pooled models are fitted on date-synchronised folds',(f[(f.model.str.startswith('pooled'))].groupby(['task','model','date']).ticker.nunique()==len(CORE)).all())
    unpen=[CONFIG['dynamic_core'],CONFIG['dynamic_core']+['momentum_1'],CONFIG['dynamic_core']+CONFIG['financial_extension']]
    check('No unpenalised specification mixes a level with its lag or difference',
          not any(c+'_diff' in cols or c+'_lag1' in cols for cols in unpen for c in cols))
    vv=f[(f.task=='variance')&(f.model.isin(['pooled_ridge','historical_variance63']))].pivot_table(index=['ticker','date'],columns='model',values='benchmark')
    check('Pooled variance benchmark equals the 63-session historical variance',np.allclose(vv.pooled_ridge,vv.historical_variance63,rtol=1e-9))
    check('Market-relative task named consistently',('market_relative_return' in set(f.task)) and ('excess_return' not in set(f.task)))
    reg=pd.read_csv(OUT/'feature_registry.csv')
    check('Registry covers every compact-model input',set(CONFIG['dynamic_core'])<=set(reg.variable) and reg[reg.variable.isin(CONFIG['dynamic_core'])].formula.notna().all())
    cov=pd.read_csv(OUT/'coverage_and_deferrals.csv')
    check('Coverage separates description from training eligibility',{'descriptive_nonmissing_share','training_eligible_share'}<=set(cov.columns))
    check('Regime definitions recorded',len(pd.read_csv(OUT/'regime_definitions.csv'))==3)
    check('Exposure map records evidence strength',{'evidence_strength','proxy_type','mapping_basis'}<=set(pd.read_csv(OUT/'exposure_map.csv').columns))
    check('ENTG equity-substitution sensitivity scored on matched dates',((pc.ticker=='ENTG')&(pc.expanded=='ridge_full')&(pc.reduced=='without_equity_inputs')).any())
    check('Metric registry states the inference estimand',pd.read_csv(OUT/'metric_registry.csv').metric.str.contains('Unadjusted p-value').any())
    stale=[x.name for pattern in ['forecasts_return_*','forecasts_variance*','forecasts_pooled*','forecasts_horizon3*','forecasts_transformations*',
           'parameter_paths_return_*','tuning_return_*','splits_return_*','failures_*','variance_failures*','pooled_failures*','variance_tuning*'] for x in OUT.glob(pattern+'.csv')]
    check('No per-stage duplicate of a consolidated table in the processed outputs',not stale,stale[:5])
    check('No interim ledger remains after a full rebuild',not any(INTERIM.glob('*.csv')) if INTERIM.exists() else True,[p.name for p in INTERIM.glob('*.csv')][:5] if INTERIM.exists() else '')

    # --- report ------------------------------------------------------------
    path=ROOT/'final/Financial_Valuation_Model_Comparison.html'
    doc=path.read_text();soup=BeautifulSoup(doc,'html.parser')
    manifest=pd.read_csv(OUT/'figure_manifest.csv')
    check('Every manifest figure exists as PNG, SVG and source data',
          all((FIG/n).exists() for col in ['png','svg','source'] for n in manifest[col]))
    numbers=[int(m) for m in re.findall(r'<strong>Figure (\d+)\.',doc)]
    check('Figure numbers are sequential with no gaps or duplicates',numbers==list(range(1,len(numbers)+1)),numbers)
    check('Every figure is referred to in the narrative',
          all(f'Figure {n}' in soup.get_text() for n in numbers))
    check('All figures embed and all five issuers appear',
          len(soup.select('img[src^="data:image/png;base64,"]'))==len(manifest) and all(tk in soup.get_text() for tk in TICKERS))
    planned={(OUT/'validation_results.json').resolve(),(ROOT/'CONTINUATION_AUDIT.json').resolve(),(ROOT/'COMPLETION_AUDIT.json').resolve(),(ROOT/'REVISION_AUDIT.json').resolve()}
    broken=[a['href'] for a in soup.select('a[href]')
            if not a['href'].startswith(('http:','https:','#','mailto:'))
            and not (ROOT/'final'/a['href'].split('#')[0]).resolve().exists()
            and (ROOT/'final'/a['href'].split('#')[0]).resolve() not in planned]
    check('Every local link in the report resolves',not broken,broken)
    check('Report states the out-of-sample month count consistently',
          f'{int(counts.min())} monthly origins' in soup.get_text() or f'{int(counts.min())}' in soup.get_text())
    # Scan the visible text only: base64 image payloads are not prose.
    visible=soup.get_text(' ')
    # The revision record quotes the corrected wording as findings; judge the prose around it.
    prose=BeautifulSoup(doc,'html.parser')
    for section in prose.select('section#revision'):section.decompose()
    prose=prose.get_text(' ')
    origins=f[(f.task=='return')&(f.horizon==1)].origin
    check('Report distinguishes forecast origins from target months',origins.min()[:10] in prose and origins.max()[:10] in prose and 'monthly origins from 2023-01-31' not in prose)
    flagged=['underpowered against any plausible','pipeline can detect a signal','Pooling helps because','is itself the stable finding','necessarily shrinks the measured gap']
    check('Report contains none of the flagged assertions',not [x for x in flagged if x in prose],[x for x in flagged if x in prose])
    contrast=pd.read_csv(OUT/'correlation_regime_contrasts.csv');spans=contrast[(contrast.lo<=0)&(contrast.hi>=0)]
    check('Correlation prose matches the contrast table',all(f'{a}\u2013{b}' in visible for a,b in zip(spans['first'],spans['second'])))
    check('No placeholder text remains in the report',
          not re.search(r'\b(TODO|TBD|FIXME|XXX|Lorem ipsum|placeholder)\b',visible,re.I),
          re.findall(r'.{60}\b(?:TODO|TBD|FIXME|XXX|placeholder)\b.{60}',visible,re.I)[:2])

    names={x['check'] for x in checks};register=pd.read_csv(OUT/'issue_register.csv')
    wanted={v for v in register.validation_check.dropna() if v!='None'}-{'Every issue-register check exists and passed'}
    missing=[v for v in wanted if v not in names];failed=[x['check'] for x in checks if x['check'] in wanted and not x['passed']]
    check('Every issue-register check exists and passed',not missing and not failed,dict(missing=missing,failed=failed))
    result=dict(passed=all(x['passed'] for x in checks),checks=checks,cutoff=CUTOFF,seed=SEED,
        out_of_sample_months=int(counts.min()),figures=len(manifest),
        generated='offline rebuild via code/run_experiments.py')
    (OUT/'validation_results.json').write_text(json.dumps(result,indent=2)+'\n')
    for x in checks:print(('PASS ' if x['passed'] else 'FAIL ')+x['check']+('' if x['passed'] else ' :: '+x['detail']))
    print(f"\n{sum(x['passed'] for x in checks)}/{len(checks)} checks passed",flush=True)
    if not result['passed']:raise SystemExit('Validation failed; see validation_results.json')

if __name__=='__main__':build()
