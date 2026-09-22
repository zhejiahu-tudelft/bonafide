"""Readable variable/metric registries generated from the actual implementation."""
import json
import numpy as np
import pandas as pd
from settings import *

def build():
    r=pd.read_csv(OUT/'feature_registry.csv')
    definitions={
      'ebitda_growth':('TTM operating EBITDA / its as-known value 12 calendar months earlier - 1; positive prior base required','fraction','Profit growth after adding compatible D&A; acquisition/accounting changes may dominate.'),
      'gross_margin':('TTM gross profit / TTM revenue','fraction','Gross profitability; metal-price pass-through affects comparability.'),
      'operating_margin':('TTM operating income / TTM revenue','fraction','Operating profitability; exceptional charges remain in GAAP values.'),
      'net_margin':('TTM earnings attributed to common / TTM revenue','fraction','After-tax shareholder profitability; taxes and financing also matter.'),
      'ebitda_margin':('TTM (operating income + compatible D&A) / TTM revenue','fraction','Cash-earnings proxy, not CFO and not company-adjusted EBITDA.'),
      'debt_assets':('Reported interest-bearing debt / latest total assets','fraction','Balance-sheet leverage; financing claims have issuer-specific tag limitations.'),
      'debt_equity':('Reported interest-bearing debt / positive parent book equity','ratio','Debt relative to book capital; invalid for nonpositive equity.'),
      'cash_assets':('Latest cash and cash equivalents / latest total assets','fraction','Liquidity buffer and potential balance-sheet flexibility.'),
      'cfo_assets':('TTM operating cash flow / latest total assets','fraction','Operating cash generation; denominator is end-period assets, not average assets.'),
      'fcf_assets':('TTM CFO less equipment capex and MTRN mine development / latest total assets','fraction','Cash after recorded investment; missing mining history remains missing.'),
      'capex_assets':('TTM total investment capex / latest total assets','fraction','Reinvestment intensity can support growth while reducing current cash.'),
      'market_return':('SPY adjusted-close compounded return during the completed origin month','fraction','Past broad-market performance, not realized future market return.'),
      'smallcap_return':('IWM adjusted-close compounded return in origin month','fraction','Small-cap reference, not a claim of verified issuer index membership.'),
      'market_vol':('Sample standard deviation of SPY daily returns in origin month','daily return fraction','Observable market risk state before the target month.'),
      'vix':('Last available VIX close, delayed one US session, divided by 100','annualized volatility fraction','Option-implied market volatility; different frequency/meaning from realized daily volatility.'),
      'yield_10y':('Last TNX 10-year nominal yield quote, delayed one US session, /100','yield fraction','Long-term nominal discount-rate/funding environment.'),
      'yield_short':('Last IRX short Treasury yield quote, delayed one US session, /100','yield fraction','Cash-rate predictor; not a realized risk-free holding-period return.'),
      'yield_10y_change':('Origin short-delayed 10-year yield minus preceding monthly value','yield-fraction change','Rate change known at origin; 0.01 means one percentage point.'),
      'term_spread':('10-year nominal yield minus short Treasury yield','yield fraction','Slope of the yield curve; a macro/financing-state proxy.'),
      'real_yield':('FRED DFII10 last available daily quote /100, delayed one US session','yield fraction','Real discount-rate environment; retrieved vintage is reconstructed historical data.'),
      'real_yield_change':('Real yield at origin minus preceding monthly value','yield-fraction change','Change in the real discount-rate environment.'),
      'credit_spread':('FRED BAMLH0A0HYM2 last quote /100, delayed one US session','spread fraction','High-yield credit conditions; download starts September 2023 and fails initial training coverage.'),
      'credit_spread_change':('Credit-spread origin value minus preceding monthly value','spread-fraction change','Funding-stress change; insufficient historical training coverage in this archive.'),
      'industry_return':('SOXX monthly return for MTRN/ENTG; ITA monthly return for CRS/ATI','fraction','Reference industry exposure; not an inferred segment-revenue weight.'),
      'industry_relative':('Origin industry-reference monthly return minus SPY monthly return','percentage-point fraction','Industry performance beyond the broad market in the past month.'),
      'industry_vol':('Daily-return sample SD of the issuer industry reference during origin month','daily return fraction','Industry risk state; semiconductor or aerospace/defense reference.'),
      'sector_return':('XLB adjusted-close monthly return','fraction','Materials-sector reference; not asserted to be every issuer’s formal classification.'),
      'semis_return':('SOXX adjusted-close monthly return','fraction','Semiconductor-equity co-movement proxy, not physical chip-production growth.'),
      'defense_return':('ITA adjusted-close monthly return','fraction','Aerospace/defense-equity proxy, not government spending or aircraft orders.'),
      'relative_momentum':('Own trailing three-month compounded return minus SPY equivalent','fraction','Past company performance relative to the broad market.'),
      'industry_momentum_relative':('Own trailing three-month compounded return minus industry-reference equivalent','fraction','Past company performance relative to its designated industry reference.'),
      'beta_252':('Prior 252-session sample covariance(stock,SPY) / variance(SPY)','dimensionless','Historical market sensitivity measured entirely before the target.'),
      'idio_vol':('sqrt(max(stock daily variance - beta_252^2 × SPY variance,0)) over prior 252 sessions','daily return fraction','Residual SD of the trailing market regression with an intercept.'),
      'drawdown_252':('Most negative wealth/running-peak - 1 within preceding 252 sessions','fraction','Prior peak-to-trough loss; window restarts its own wealth baseline.'),
      'log_dollar_volume':('Natural log of mean(close × reported shares traded) over prior 21 sessions','log USD/day','Trading-activity proxy; no historical bid–ask quotes are inferred.'),
      'turnover':('Prior 21-session mean shares traded / latest filed actual shares outstanding','fraction/day','Trading activity relative to share count; outstanding shares can be stale.'),
      'driver_vol':('Prior 21-session SD of delayed copper-futures returns for MTRN, gas-futures returns otherwise','daily price-change fraction','Mapped input-price uncertainty; exploratory cost/pass-through proxy.'),
      'pe_pct_change':('Valid as-known P/E at origin / preceding monthly P/E - 1','fraction','Past multiple change; target-month price never enters.'),
      'earnings_yield_z':('Current earnings yield less preceding 36-month mean, divided by preceding 36-month SD; minimum 24 prior months','standard deviations','Valuation relative to the issuer’s own prior history.'),
      'revenue_valuation_interaction':('Quarterly year-over-year revenue growth × origin earnings yield','product of fractions','Tests a limited valuation/growth interaction; no causal interpretation.'),
      'margin_valuation_interaction':('TTM operating margin × origin earnings yield','product of fractions','Tests a limited profitability/valuation interaction.'),
    }
    asset_names={'copper':'HG=F copper futures','gold':'GC=F gold futures','silver':'SI=F silver futures','gas':'NG=F natural gas futures','oil':'CL=F crude oil futures','eurusd':'EURUSD=X (USD per EUR)','dollar':'DX-Y.NYB dollar index'}
    for name,series in asset_names.items():definitions[name+'_return']=(f'{series}: percentage change between month-end closes after a one-US-session delay','fraction','Known commodity/input-price or currency movement; futures vendor construction/roll effects are retained.')
    for idx,row in r.iterrows():
        name=row.variable
        if name in definitions:r.loc[idx,['formula','units','rationale']]=definitions[name]
        if row['group'] in ['market','industry','business','momentum','risk']:
            r.loc[idx,'frequency']='daily market observations aggregated at monthly forecast origins'
            r.loc[idx,'availability']='Origin close; commodity/FX/macro observations delayed one US session'
        if name=='quick_ratio':r.loc[idx,'name']='Quick-ratio proxy: current assets less inventories'
        if name in ['roic_proxy','ev_ebitda_proxy','ev_sales_proxy']:r.loc[idx,'name']=row['name'].split(' (unreconciled')[0]+' (unreconciled claims sensitivity)'
    extra=[]
    for name in CONFIG['dynamic_core']:
        for lag in [1,3]:
            label=f'{name}_lag{lag}'
            if label not in set(r.variable):extra.append(dict(variable=label,name=f'{name.replace("_"," ").title()}, {lag}-month lag',group='transform',formula=f'{name} recorded {lag} calendar months before the origin; not a first difference',units='same as parent variable',frequency='monthly lag of as-known series',availability='known strictly before origin',rationale='Tests delayed predictor effects with otherwise identical current predictors.',status='implemented in controlled lag comparison'))
    # The compact model's issuer-specific aliases are not in the broad catalogue (they
    # would duplicate named series there), so they are registered explicitly.
    compact={'industry_return':('market','SOXX monthly return for MTRN/ENTG; ITA monthly return for CRS/ATI','fraction','Reference industry exposure; a traded equity proxy, not segment revenue or physical demand.'),
      'industry_relative':('market','Origin-month industry-reference return (SOXX for MTRN/ENTG, ITA for CRS/ATI) minus the SPY return over the same completed month','fraction (difference of returns)','Industry performance beyond the broad market in the month before the target; a traded proxy, not physical demand.'),
      'driver_return':('business','Completed-month change in the mapped input price, delayed one US session: HG=F copper futures for MTRN, NG=F natural gas futures for ENTG, CRS and ATI','fraction','MTRN: copper is a named input with disclosed pass-through. ENTG/CRS/ATI: a weak, exploratory energy-cost hypothesis with no disclosed exposure weight.')}
    for name,(group,formula,units,why) in compact.items():
        if name not in set(r.variable):
            extra.append(dict(variable=name,name=name.replace('_',' ').title(),group=group,formula=formula,units=units,
                frequency='daily market observations aggregated at monthly forecast origins',availability='Origin close; futures delayed one US session',
                rationale=why,status='implemented in the compact model; issuer-specific alias excluded from the broad set to avoid duplicate columns'))
    r=pd.concat([r,pd.DataFrame(extra)],ignore_index=True)
    r['in_compact_model']=r.variable.isin(CONFIG['dynamic_core'])
    r['in_financial_extension']=r.variable.isin(CONFIG['financial_extension'])
    for name,formula in [('pe_diff','Valid origin P/E minus preceding monthly P/E'),('pe_lag1','Valid P/E recorded one calendar month before origin')]:
        if name not in set(r.variable):r.loc[len(r),['variable','name','group','formula','units','frequency','availability','rationale','status']]=[name,name.replace('_',' ').title(),'transform',formula,'multiple','monthly','known at origin','Controlled P/E transformation comparison with other compact predictors held fixed.','implemented in controlled P/E comparison']
    d=pd.read_csv(OUT/'monthly_features_as_known.csv')
    r['missing_treatment']='Training coverage >=70%, median imputation with missing indicators; training-only 1st/99th percentile clipping and scaling. All-null/constant features excluded.'
    r['economic_sign']='Not constrained; demand, pass-through, expectations and financing can offset each other.'
    r['transformation']=r.variable.map(lambda n:'first difference' if n.endswith('_diff') else ('lagged level' if '_lag' in n else ('percentage change' if 'pct_change' in n else ('trailing z-score' if n.endswith('_z') else 'level or specified growth/rolling measure'))))
    r.to_csv(OUT/'feature_registry.csv',index=False)
    metrics=[
     ('RMSE','sqrt(mean((actual-forecast)^2))','lower','Target units; emphasizes large errors.'),
     ('MAE','mean(abs(actual-forecast))','lower','Target units; checks typical absolute errors.'),
     ('R2_OOS','1 - sum(error_model^2)/sum(error_realtime_baseline^2)','higher','Negative means worse than the specified origin-available benchmark.'),
     ('Direction','mean(sign(actual)==sign(forecast))','higher relative to directional baselines','Exact zero is a separate sign; magnitudes are ignored.'),
     ('Forecast correlation','Pearson correlation(forecast,actual)','higher, jointly with calibration/loss','Undefined for a constant series; high correlation alone does not ensure small errors.'),
     ('QLIKE','mean(actual_variance/predicted_variance - log(actual_variance/predicted_variance) - 1)','lower','Positive variance forecasts required; main variance ranking score.'),
     ('Root-variance RMSE','sqrt(mean((sqrt(actual_variance)-sqrt(predicted_variance))^2))','lower','Daily-volatility scale. The square root of a variance forecast is not an expected volatility (Jensen), so this is an error on the root of the variance forecast.'),
     ('AIC/BIC','-2 log-likelihood + 2k / -2 log-likelihood + k log(n)','lower on compatible training likelihoods','Recorded for dynamic/volatility fits, not the OOS selection score.'),
     ('Loss reduction','mean over calendar months of d = loss(reduced) - loss(expanded)','positive favours expanded','Estimand of every paired comparison: paired same-month MSE for returns, QLIKE for variance. Identical forecasts give d = 0 exactly.'),
     ('Paired interval','95% percentile interval, order statistics 50 and 1950 of B = 1999 circular block bootstrap means (blocks of 3, 6 or 12 months; 6 primary; seed 20260918)','excludes zero','Resamples whole calendar months; conditional on saved forecasts, so estimation, tuning and specification-search uncertainty are not included.'),
     ('Unadjusted p-value','2 (min(#d*<=0, #d*>=0) + 1) / (B + 1)','smaller','Inverts the same interval: p <= 0.05 exactly when the 95% interval excludes zero. Monte Carlo resolution 0.001.'),
     ('Joint cross-issuer contrast','Equal-weight average of the issuers\' d within each calendar month, then the same bootstrap','excludes zero','Whole months are resampled, never individual company-month rows.'),
     ('Holm-adjusted p-value','Holm step-down over the tested rows of one declared family (R16, RJ4, V20, VJ5)','smaller','A multiplicity-adjusted decision; it need not agree with unadjusted interval exclusion. Other comparisons are exploratory.'),
     ('Clark-West statistic','mean of (e_small^2 - (e_big^2 - (f_small - f_big)^2)), Newey-West t, one-sided','larger','Fixed nested OLS pairs only: population predictive content of extra regressors, not sample forecast accuracy.'),
     ('Detectable loss reduction','2.80 x bootstrap standard error of the mean differential','n/a','80% power at 5% two-sided under a normal approximation; for returns also shown in OOS R-squared points relative to the historical mean.'),
     ('Empirical size','Rejection rate at nominal 5% over 500 synthetic null samples (stationary bootstrap of the demeaned observed differential)','close to 0.05','Calibration of the paired test for series like the observed ones; above 0.10 at the primary block means p-values are descriptive only.'),
     ('Family status','tested / identical_by_exclusion / identical_by_selection / identical_other / ineligible','n/a','Identical forecasts at every origin are an untested contrast, not evidence of no effect.'),
     ('Rolling stability','12-month RMSE, MAE, bias and OOS R2','interpret jointly','Overlapping windows are not independent evidence.')]
    pd.DataFrame(metrics,columns=['metric','formula','preferred_direction','interpretation']).to_csv(OUT/'metric_registry.csv',index=False)
    # Protocol section 16 fixes the E-series identifiers the report is organised by.
    # The RQ labels from the execution addendum are carried as a cross-reference so
    # the two vocabularies cannot drift apart.
    questions=[
     ('E1','Do company financial characteristics add predictive information beyond simple return benchmarks and common market conditions?',
      'P1 vs historical mean; full model vs full-minus-financial; financial-only','Paired OOS MSE with moving-block intervals; RMSE, MAE, OOS R2','RQ1'),
     ('E2','Does starting valuation add information beyond the same financial and external controls?',
      'Broad Ridge vs Broad Ridge minus valuation (frozen family); P2 vs P1; financial+valuation vs financial-only','Paired OOS MSE, Holm-adjusted within the frozen family','RQ1'),
     ('E3','Do first differences, percentage changes or changes in growth rates improve on factor levels?',
      'Controlled P/E level vs difference vs percentage change vs lag; financial changes; P3 vs P2','Matched OOS MSE, MAE and paired intervals','RQ3'),
     ('E4','Do market, industry and relevant commodity/business drivers add value beyond financial and valuation variables?',
      'Both cumulative ladders and leave-one-block-out, with derivatives removed alongside their block','Paired OOS loss change in both orderings; grouped block permutation as a noncausal diagnostic','RQ1, RQ4'),
     ('E5','Do older predictor observations improve forecasts beyond the latest information?',
      'Lag sets {0}, {0,1} and {0,1,3} on the same compact base inputs','Paired OOS MSE and lag-length sensitivity; cumulative paired loss','RQ3'),
     ('E6','Does a forecastable AR/MA error process improve on a static model using the same information?',
      'Selected ARIMAX vs the matching ARMA(0,0) fit with identical inputs, likelihood and intercept convention','Paired OOS MSE; AIC/BIC as training screens only','RQ3'),
     ('E7','Do the main comparisons remain stable across forecast horizons, training windows and market regimes?',
      'One- and three-month horizons on common origins; expanding vs separately tuned rolling 84-month; origin-known volatility and rate regimes; leave-one-month and leave-one-year influence','Rolling 12-month loss, regime, horizon and influence tables; all nonoverlapping three-month offsets','RQ7'),
     ('E8','Can the same information improve a separately defined forecast of realised variance?',
      'Historical variance, EWMA, ARCH, GARCH, GARCH-X; controlled 2x2 matrix of individual/pooled x persistence/persistence+external (declared family V20, joint VJ5); regularised and tree variance models','QLIKE primary, Holm within V20 and VJ5; root-variance errors reported separately','RQ5, RQ6, RQ8')]
    pd.DataFrame(questions,columns=['experiment','research_question','comparison','evaluation','addendum_cross_reference']).to_csv(OUT/'experiment_registry.csv',index=False)
    # Descriptive availability (origins from December 2015) is not training
    # eligibility: each outer fit applies the 70% gate to its own training window.
    coverage=pd.read_csv(OUT/'feature_coverage.csv')
    aliases=[]
    for tk,g in d.groupby('ticker'):
        use=g[g.date>='2015-12-31']
        for v,group in [('industry_relative','market'),('driver_return','business')]:
            if not ((coverage.ticker==tk)&(coverage.variable==v)).any():
                aliases.append(dict(ticker=tk,variable=v,group=group,observations=len(use),available=int(use[v].notna().sum()),status='implemented in the compact model'))
    coverage=pd.concat([coverage,pd.DataFrame(aliases)],ignore_index=True)
    coverage['descriptive_nonmissing_share']=coverage.available/coverage.observations.where(coverage.observations>0)
    paths=pd.read_csv(OUT/'parameter_paths.csv')
    used=paths.assign(variable=paths.variable.str.replace(' missing','',regex=False)).groupby('ticker').variable.apply(set).to_dict()
    coverage['selected_by_a_recorded_primary_model']=[v in used.get(t,set()) for t,v in zip(coverage.ticker,coverage.variable)]
    gate=CONFIG['feature_training_min_coverage'];eligible={}
    for tk in CORE:
        z=d[(d.ticker==tk)&(d.date>='2015-12-31')].dropna(subset=['return_target']).reset_index(drop=True)
        for v in set(coverage.variable)&set(z.columns):
            x=pd.to_numeric(z[v],errors='coerce').replace([np.inf,-np.inf],np.nan)
            ok=[bool(x.iloc[:i].notna().mean()>=gate and x.iloc[:i].std()>1e-12) for i in range(84,len(z))]
            eligible[(tk,v)]=(float(np.mean(ok)),next((z.date.iloc[84+j] for j,flag in enumerate(ok) if flag),''))
    coverage['training_eligible_share']=[eligible.get((t,v),(np.nan,''))[0] for t,v in zip(coverage.ticker,coverage.variable)]
    coverage['first_eligible_origin']=[eligible.get((t,v),(np.nan,''))[1] for t,v in zip(coverage.ticker,coverage.variable)]
    coverage['coverage_note']='descriptive_nonmissing_share: origins from December 2015; training_eligible_share: share of the 44 outer training windows in which the variable passed the 70% gate.'
    coverage.to_csv(OUT/'coverage_and_deferrals.csv',index=False)
    print('DOCUMENTATION',len(r),'variable definitions',flush=True)

if __name__=='__main__':build()
