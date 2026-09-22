"""Fail closed on numerical, source-preservation, sample and report errors."""
import json,hashlib,re
import numpy as np,pandas as pd
from bs4 import BeautifulSoup
from settings import *

def build():
    checks=[]
    def check(name,condition,detail=''):
        checks.append(dict(check=name,passed=bool(condition),detail=detail))
    from common.code.preservation import verify
    original=json.loads((ROOT/'baseline_hashes.json').read_text())
    # Documented link-only retirements and amendments (MTRN/RESOURCE_LINKS.md) count as preserved.
    changed=verify(original,REPO,REPO/'MTRN/resource_changes.json')
    check('Original MTRN research, original inputs, HPE code and protocol preserved',not changed,changed)
    r=pd.read_csv(OUT/'daily_returns.csv',index_col=0,parse_dates=True)
    check('No price observation beyond cutoff',str(r.index.max().date())==CUTOFF)
    check('ELMT matched public history only',r.ELMT.notna().sum()==102 and str(r.ELMT.first_valid_index().date())=='2026-04-24')
    f=pd.read_csv(OUT/'financial_fact_audit.csv')
    check('Every selected SEC fact available at assigned date',((f.available<=f['asof'])&(f.filed<=f['asof'])&(f.end<=f['asof'])).all())
    check('All selected facts, including TTM comparatives, have vintage metadata',
          f[['unit','namespace','first_filed_for_period','vintage_status']].notna().all().all() and (f.first_filed_for_period<=f.filed).all())
    moments=pd.read_csv(OUT/'moments.csv')
    weekly=moments[moments.frequency=='weekly']
    expected_week_counts={('long','total'):559,('long','excess'):552,('recent','total'):298,('recent','excess'):291,('matched','total'):21}
    observed_week_counts={(panel,basis):set(g.n) for (panel,basis),g in weekly.groupby(['panel','basis'])}
    check('Complete opening weeks retained and ELMT partial week excluded',
          observed_week_counts=={k:{v} for k,v in expected_week_counts.items()} and
          weekly.loc[weekly.panel=='long','start'].eq('2016-01-08').all() and
          weekly.loc[weekly.panel=='recent','start'].eq('2021-01-08').all() and
          weekly.loc[weekly.panel=='matched','start'].eq('2026-05-01').all())
    check('Risk-free-adjusted moments do not extrapolate beyond factor coverage',moments.loc[moments.basis=='excess','end'].max()=='2026-07-31')
    monthly=pd.read_csv(OUT/'monthly_returns.csv',index_col=0,parse_dates=True)
    check('Partial September excluded from monthly returns',monthly.index.max()==pd.Timestamp(MONTH_END) and monthly.index.is_month_end.all())
    s=pd.read_csv(OUT/'financial_snapshots.csv');last=s[(s.ticker=='MTRN')&(s['asof']==CUTOFF)].iloc[0]
    check('Materion TTM FCF includes mine development',np.isclose(last.fcf,32.439) and np.isclose(last.mine_capex,17.774),{'fcf_m':last.fcf,'mine_capex_m':last.mine_capex})
    check('No negative investment outflow from stale tag selection',(s.total_capex.dropna()>=0).all() and (s.mine_capex.dropna()>=0).all())
    b=pd.read_csv(OUT/'accounting_bridges.csv');valid=b[b.valid]
    check('All requested bridge panels represented',len(b)==17 and b.panel.nunique()==4)
    check('Price/EPS/multiple log identities reconcile',valid.identity_error.max()<1e-12)
    check('Invalid EPS bridges are excluded',not b[b.ticker=='ELMT'].valid.any() and b[~b.valid].log_eps.isna().all())
    m=pd.read_csv(OUT/'models.csv')
    check('Monthly gates, calendar alignment, and no ELMT full model',((m.n>=np.maximum(60,10*m.parameters))&(m.end<='2026-08-31')).all() and 'ELMT' not in set(m.ticker))
    check('Nested models share observations',m.groupby('panel').n.nunique().eq(1).all() and set(m.n)=={67,127})
    check('Mean and variance decomposition identities',m.mean_identity_error.max()<1e-12 and m.variance_identity_error.max()<1e-12)
    check('Residual mean not confused with alpha',m.mean_residual.abs().max()<1e-12 and m.alpha.abs().max()>1e-4)
    e=pd.read_csv(OUT/'earnings_announcements.csv')
    check('Complete 2021-cutoff quarterly earnings census',e.groupby('ticker').size().to_dict()=={tk:23 for tk in CORE})
    check('Original-release update coverage',e[['eps','eps_prior','operating_margin','operating_margin_prior']].notna().all().all())
    crs=e[(e.ticker=='CRS')&(e.release_date=='2023-10-26')].iloc[0]
    check('Carpenter prior-year column, not sequential column',np.isclose(crs.eps,.88) and np.isclose(crs.eps_prior,-.14))
    mt=e[(e.ticker=='MTRN')&(e.release_date=='2025-02-19')].iloc[0]
    check('Loss EPS sign preserved',np.isclose(mt.eps,-2.33) and np.isclose(mt.eps_prior,.93))
    check('Announcement release dates precede filing dates',((e.release_date<=e.filed)&(e.release_date>='2021-01-01')).all())
    c=pd.read_csv(OUT/'event_cars.csv')
    check('Event windows end by cutoff and estimation ends before window',((c.window_end<=CUTOFF)&(c.estimation_end<c.window_start)&(c.n_estimation>=160)).all())
    check('Event primary, wider, timing and industry sensitivities present',len(c)==92*3*2*2)
    sec=pd.read_csv(OUT/'secondary_price_checks.csv')
    check('ELMT secondary price source reconciled',len(sec)>10 and sec.difference.abs().max()<.006,{'observations':len(sec),'max_price_difference':float(sec.difference.abs().max())})
    html=(ROOT/'final/Historical_Attribution.html').read_text();soup=BeautifulSoup(html,'html.parser')
    check('Report contains embedded figures and all five firms',len(soup.select('img[src^="data:image/png;base64,"]'))>=6 and all(tk in soup.get_text() for tk in TICKERS))
    broken=[]
    for a in soup.select('a[href]'):
        href=a['href']
        planned=[(OUT/'validation_results.json').resolve(),(OUT/'input_hashes.csv').resolve()]
        target=(ROOT/'final'/href.split('#')[0]).resolve()
        if not href.startswith(('https:','http:','#','mailto:')) and not target.exists() and target not in planned:broken.append(href)
    check('Report local evidence/output links exist',not broken,broken)
    coverage=pd.read_csv(OUT/'report_coverage.csv')
    observed_daily={a.Component:int(a.Observations.split()[0].replace(',','')) for a in coverage.itertuples() if a.Component.endswith('raw-return panel') or a.Component=='Matched five-company panel'}
    check('Report coverage counts match computed moments',observed_daily=={
        'Long raw-return panel':int(moments.query('panel=="long" and frequency=="daily" and basis=="total"').n.iloc[0]),
        'Recent raw-return panel':int(moments.query('panel=="recent" and frequency=="daily" and basis=="total"').n.iloc[0]),
        'Matched five-company panel':int(moments.query('panel=="matched" and frequency=="daily" and basis=="total"').n.iloc[0])})
    inventory=[]
    files=[p for d in [RAW,SOURCES] for p in d.rglob('*') if p.is_file()]
    files += [REPO/p for p in original if p.startswith(('MTRN/data/','MTRN/report/')) and (REPO/p).exists()]
    for p in sorted(set(files)):
        inventory.append(dict(path=str(p.relative_to(REPO)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
    pd.DataFrame(inventory).to_csv(OUT/'input_hashes.csv',index=False)
    result=dict(passed=all(x['passed'] for x in checks),checks=checks,cutoff=CUTOFF,seed=SEED,bootstrap_replications=REPS)
    (OUT/'validation_results.json').write_text(json.dumps(result,indent=2))
    for x in checks:print(('PASS ' if x['passed'] else 'FAIL ')+x['check'])
    if not result['passed']:raise SystemExit('Validation failed; see validation_results.json')

if __name__=='__main__':build()
