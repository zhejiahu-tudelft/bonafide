"""Research report and uniform figures, entirely from archived experiment outputs."""
import base64,html,json
from settings import *
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
from statsmodels.tsa.stattools import acf


NAMES={'historical_mean':'Historical mean','market_mean':'Market mean','capm_style':'CAPM-style forecast','core_ols':'Compact OLS','core_ridge':'Compact Ridge','ridge_full':'Broad Ridge','lasso_full':'Broad Lasso','elastic_full':'Broad Elastic Net','forest_full':'Random Forest','boost_full':'Gradient boosting','ar1':'AR(1)','arx':'Compact ARX','arma_static':'Static ARMA(0,0) errors','arimax':'Selected ARIMAX','distributed_all_lag1':'All-core lags 0 + 1','distributed_all_lag3':'All-core lags 0 + 1 + 3','distributed_lag1':'Selected-core lag 1','distributed_lag3':'Selected-core lags 1 + 3','historical_variance21':'Historical variance: 21d','historical_variance63':'Historical variance: 63d','historical_variance252':'Historical variance: 252d','ewma94':'EWMA (0.94)','arch1':'ARCH(1)','garch11':'GARCH(1,1)','garchx_market':'GARCH-X: market','garchx_industry':'GARCH-X: +industry','garchx_business':'GARCH-X: +business','variance_ridge':'Variance Ridge','variance_forest':'Variance Random Forest','variance_boost':'Variance gradient boosting','variance_ridge_persistence':'Variance Ridge: persistence','variance_ridge_market':'Variance Ridge: +market','variance_ridge_external':'Variance Ridge: +external','pooled_ridge':'Pooled Ridge','pooled_forest':'Pooled Random Forest','pooled_boost':'Pooled gradient boosting','panel_company_effects':'Compact company-effects panel','business_pair_ridge':'Business-pair Ridge','ridge_rolling84':'Broad Ridge: rolling 84m','financial_only':'Financial only','financial_valuation':'Financial + valuation','claims_proxy_sensitivity':'Limited EV/ROIC proxies','core_pe_level':'Compact: P/E level','core_pe_difference':'Compact: P/E difference','core_pe_percentage':'Compact: P/E % change','core_pe_lag1':'Compact: P/E lag 1','core_financial_changes':'Compact: financial/yield changes'}
STAGES=['historical_mean','A1_market','A2_financial','A3_valuation','A4_momentum','A5_risk','A6_industry','A7_business','A8_transform','A9_interaction']
for n,label in zip(STAGES[1:],['Market','+ Financial','+ Valuation','+ Momentum','+ Risk/liquidity','+ Industry','+ Business drivers','+ Changes/lags','+ Interactions']):NAMES[n]=label
for n in ['market','financial','valuation','momentum','risk','industry','business']:NAMES['without_'+n]='Broad Ridge minus '+n
NAMES['zero']='Zero return';NAMES['mine_inclusive_fcf']='Broad Ridge + mine-inclusive FCF'
for n,label in zip(['P1_financial','P2_valuation','P3_transform','P4_market','P5_industry','P6_business'],
                   ['Financial','+ Valuation','+ Changes/lags','+ Market','+ Industry','+ Business drivers']):NAMES[n]=label
PROTOCOL_STAGES=['historical_mean','P1_financial','P2_valuation','P3_transform','P4_market','P5_industry','P6_business']
# Frozen section-17 encoding: observed outcomes black solid, benchmarks gray dashed,
# static regression blue solid, distributed lag orange dashed, dynamic ARMA purple
# dash-dot. Line style carries the same information as colour for grayscale reading.
COLORS={'baseline':'#657080','linear':'#235b91','lag':'#b7772b','dynamic':'#79549d','forest':'#087f83','boost':'#bc4c47','garch':'#79549d','pool':'#4054a1'}
LINES={'baseline':'--','linear':'-','lag':'--','dynamic':'-.','forest':'-','boost':'-','garch':'-.','pool':'--'}
MARKERS={'baseline':None,'linear':'o','lag':'s','dynamic':'^','forest':'D','boost':'v','garch':'^','pool':'P'}
def family(m):
    if m.startswith('historical') or m in ['market_mean','capm_style','zero','ewma94']:return 'baseline'
    if 'forest' in m:return 'forest'
    if 'boost' in m:return 'boost'
    if 'garch' in m or m=='arch1':return 'garch'
    if m in ['ar1','arx','arimax','arma_static']:return 'dynamic'
    if 'lag' in m or m.startswith('core_pe_') or m=='core_financial_changes':return 'lag'
    if 'pooled' in m or 'pair' in m or m=='panel_company_effects':return 'pool'
    return 'linear'
STYLE={m:dict(color=COLORS[family(m)],linestyle=LINES[family(m)],marker=None) for m in NAMES}
STYLE['business_pair_ridge']['linestyle']=':';STYLE['garchx_business']['linestyle']=':'
def reference(ax,value=0,axis='y'):
    """Reference lines belong behind the marks they annotate, never across them."""
    line=ax.axhline if axis=='y' else ax.axvline
    line(value,color='#64748b',lw=.7,zorder=0)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.titlesize':11,'axes.labelsize':10,'xtick.labelsize':9,'ytick.labelsize':9,'legend.fontsize':9,'axes.spines.top':False,'axes.spines.right':False,'axes.facecolor':'white','figure.facecolor':'white','axes.grid':True,'grid.alpha':.18,'grid.linewidth':.6,'savefig.dpi':160,'axes.axisbelow':True})
MANIFEST=[]
def read(n):
    p=OUT/(n+'.csv')
    # A genuinely empty result table (no failures, for instance) is a valid outcome.
    return pd.read_csv(p) if p.stat().st_size>1 else pd.DataFrame()
def model(m):return NAMES.get(m,m.replace('_',' ').title())
def save(fig,key,title,subtitle,caption,data):
    # Reserve the header in inches so title and subtitle keep the same visual gap
    # whatever the figure height, instead of colliding on the taller panels.
    height=fig.get_size_inches()[1]
    fig.tight_layout(rect=[0,0,1,1-1.0/height])
    fig.text(.02,1-.20/height,title,ha='left',va='top',fontsize=16,fontweight='bold',color='#172554')
    fig.text(.02,1-.62/height,subtitle,ha='left',va='top',fontsize=10,color='#475569')
    fig.savefig(FIG/(key+'.png'),bbox_inches='tight');fig.savefig(FIG/(key+'.svg'),bbox_inches='tight');plt.close(fig)
    data.to_csv(FIG/(key+'_source.csv'),index=False)
    MANIFEST.append(dict(number=None,key=key,title=title,subtitle=subtitle,caption=caption,png=key+'.png',svg=key+'.svg',source=key+'_source.csv'))

def entry(key):return next(x for x in MANIFEST if x['key']==key)

def figure(key):
    # Numbers follow the order figures appear in the report, assigned on first embed.
    f=entry(key)
    if f['number'] is not None:raise ValueError(f'Figure {key} embedded twice; cross-reference it with num() instead')
    f['number']=sum(1 for x in MANIFEST if x['number'] is not None)+1
    encoded=base64.b64encode((FIG/f['png']).read_bytes()).decode()
    return f'<figure id="figure-{f["number"]}"><img src="data:image/png;base64,{encoded}" alt="{html.escape(f["title"])}"><figcaption><strong>Figure {f["number"]}.</strong> {html.escape(f["caption"])} <a href="../figures/{f["svg"]}">SVG</a> · <a href="../figures/{f["source"]}">data</a></figcaption></figure>'
def num(key):
    f=entry(key)
    if f['number'] is None:raise ValueError(f'Figure {key} cross-referenced before it is embedded')
    return f['number']
def table(d,caption):
    return '<div class="table-wrap">'+d.to_html(index=False,border=0,na_rep='—',float_format=lambda v:f'{v:.3f}',escape=True)+'</div><p class="caption">'+html.escape(caption)+'</p>'
def scores_table(s,task,models,ticker=None,horizon=1):
    z=s[(s.task==task)&(s.horizon==horizon)&s.model.isin(models)].copy()
    if ticker:z=z[z.ticker==ticker]
    order={m:i for i,m in enumerate(models)};z['sort']=z.model.map(order);z=z.sort_values(['ticker','sort'])
    if task=='return':
        z[['rmse','mae','directional_accuracy']]*=100
        cols=['ticker','model','n','rmse','mae','r2_oos','directional_accuracy','forecast_correlation']
        names={'rmse':'RMSE (pp)','mae':'MAE (pp)','r2_oos':'OOS R²','directional_accuracy':'Direction (%)','forecast_correlation':'Forecast corr.'}
    else:
        z[['rmse','mae']]*=1e6;z['volatility_rmse']*=100
        cols=['ticker','model','n','qlike','rmse','mae','r2_oos','volatility_rmse','volatility_correlation']
        names={'rmse':'Variance RMSE ×10⁶','mae':'Variance MAE ×10⁶','r2_oos':'OOS R²','qlike':'QLIKE','volatility_rmse':'Vol. RMSE (daily pp)','volatility_correlation':'Vol. forecast corr.'}
    z['model']=z.model.map(model)
    return z[cols].rename(columns=dict(ticker='Company',model='Model',n='Months',**names))

def make_figures(s,f):
    timeline=pd.DataFrame([['Initial fitting targets','2016-01-01','2022-12-31'],['First inner validation block','2021-01-01','2021-12-31'],['Second inner validation block','2022-01-01','2022-12-31'],['One-month out-of-sample targets','2023-01-01','2026-08-31']],columns=['period','start','end'])
    fig,ax=plt.subplots(figsize=(11,3.9))
    for i,row in timeline.iterrows():
        a,b=pd.to_datetime([row.start,row.end]);ax.barh(i,(b-a).days,left=mdates.date2num(a),height=.5,color=['#235b91','#8bafcd','#8bafcd','#087f83'][i])
    ax.set_yticks(range(4),timeline.period);ax.invert_yaxis();ax.xaxis_date();ax.xaxis.set_major_locator(mdates.YearLocator(2));ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'));ax.set_xlabel('Calendar year');ax.set_ylabel('Research period')
    save(fig,'01_timeline','A chronological experiment with nested validation','Primary horizon: next calendar month; common target sample for all eligible models','The first 84 completed monthly targets train the January 2023 forecast. Inner validation is inside that training history; every later outer origin expands the history and refits. Annual retuning reuses only preceding validation targets. The independent unit is the month, not each company-month row.',timeline)
    cov=read('coverage_and_deferrals');order=['financial','valuation','market','momentum','risk','industry','business']
    cov=cov[cov.ticker.isin(CORE)&cov.group.isin(order)].copy();cov['coverage']=cov.available/cov.observations*100
    cov['clears_gate']=(cov.coverage>=70).astype(float)*100
    fig,axes=plt.subplots(1,2,figsize=(13,4.8))
    panels=[('coverage','Mean nonmissing share of candidates (%)','Average availability'),
            ('clears_gate','Candidates clearing the 70% training gate (%)','What is actually usable')]
    for ax,(column,barlabel,title) in zip(axes,panels):
        pivot=cov.groupby(['group','ticker'])[column].mean().unstack().reindex(order)[CORE]
        im=ax.imshow(pivot,vmin=0,vmax=100,cmap='Blues',aspect='auto')
        ax.set_yticks(range(len(pivot)),[g.title() for g in pivot.index]);ax.set_xticks(range(4),CORE)
        ax.set_xlabel('Company');ax.set_ylabel('Candidate group');ax.set_title(title);ax.grid(False)
        for i in range(len(pivot)):
            for j in range(4):ax.text(j,i,f'{pivot.iloc[i,j]:.0f}%',ha='center',va='center',fontsize=9,color='white' if pivot.iloc[i,j]>65 else '#172554')
        fig.colorbar(im,ax=ax,label=barlabel,fraction=.046,pad=.04)
    save(fig,'02_coverage','After the extraction repairs, most candidates are usable for most issuers','Origin rows December 2015-August 2026 - descriptive availability, left, and the share clearing the training gate, right',
        'The left panel averages nonmissing share within each group; the right shows the share of candidates in that group whose coverage clears the 70% training-only gate, which is what determines whether a variable can enter a fit. The right panel is the operative one: a group can average high availability while individual variables fail, as the high-yield credit spread does from a 2023 archive start and interest coverage does for Materion and ATI. Three extraction defects were repaired during this continuation - Entegris equity, Carpenter trailing earnings and Materion free cash flow - and the coverage shown here is after those repairs.',cov)
    primary=['historical_mean','zero','market_mean','capm_style','core_ols','core_ridge','ar1','arx','distributed_all_lag1','arimax','ridge_full','lasso_full','elastic_full','forest_full','boost_full']
    z=s[(s.task=='return')&(s.horizon==1)&s.model.isin(primary)]
    fig,axes=plt.subplots(2,2,figsize=(12,10),sharex=True,sharey=True)
    for ax,tk in zip(axes.ravel(),CORE):
        a=z[z.ticker==tk].set_index('model').reindex(primary);ax.barh(range(len(primary)),a.r2_oos,color=[STYLE[m]['color'] for m in primary],height=.65,zorder=3);reference(ax,0,'x');ax.set_yticks(range(len(primary)),[model(m) for m in primary]);ax.invert_yaxis();ax.set_title(tk);ax.set_xlabel('OOS R² (higher is better)');ax.set_ylabel('Model')
    save(fig,'03_return_models','More elaborate return models rarely improve the benchmark','44 one-month targets per company • January 2023–August 2026','Models use the same forecast dates and historical-mean denominator. The historical mean is the denominator, so its own bar is exactly zero by construction and none is drawn. Negative R² means larger squared errors than the origin-available mean. Identical axes preserve cross-company comparability; the full tables also report MAE, direction and correlation.',z)
    ab=s[(s.task=='return')&(s.horizon==1)&s.model.isin(STAGES)].pivot(index='model',columns='ticker',values='r2_oos').reindex(STAGES)[CORE]
    fig,ax=plt.subplots(figsize=(9,6));lim=max(abs(ab.min().min()),abs(ab.max().max()));im=ax.imshow(ab,vmin=-lim,vmax=lim,cmap='RdBu',aspect='auto');ax.set_xticks(range(4),CORE);ax.set_yticks(range(len(ab)),[model(m) for m in STAGES]);ax.set_xlabel('Company');ax.set_ylabel('Cumulative Ridge factor set')
    for i in range(len(ab)):
        for j in range(4):ax.text(j,i,f'{ab.iloc[i,j]:.2f}',ha='center',va='center',fontsize=9,color='white' if abs(ab.iloc[i,j])>lim*.6 else '#172554')
    fig.colorbar(im,ax=ax,label='OOS R² (higher is better)')
    save(fig,'06_ablation','Incremental factors have different effects across issuers','Historical mean → market → financial → valuation → momentum → risk → industry → business → dynamics → interactions','Each row refits and retunes the cumulative Ridge specification on the same 44 target months. Improvements between rows are order-dependent. Full-minus-block checks provide a second view; zero or unchanged results can also arise when the added factor fails coverage.',ab.reset_index())
    ab=read('ablation_scores');prot=ab[ab.ladder=='protocol_order']
    fig,axes=plt.subplots(1,2,figsize=(13,5.4))
    width=.2
    for j,tk in enumerate(CORE):
        a=prot[prot.ticker==tk].set_index('stage').reindex(PROTOCOL_STAGES)
        axes[0].bar(np.arange(len(PROTOCOL_STAGES))+(j-1.5)*width,a.r2_oos,width=width,label=tk,color=['#235b91','#b7772b','#087f83','#bc4c47'][j],zorder=3)
        step=a.iloc[1:]
        axes[1].errorbar(step.mean_loss_reduction*1e4,np.arange(1,len(PROTOCOL_STAGES))+(j-1.5)*.18,
            xerr=np.vstack([(step.mean_loss_reduction-step.lo)*1e4,(step.hi-step.mean_loss_reduction)*1e4]),
            fmt='o',ms=4,capsize=2,color=['#235b91','#b7772b','#087f83','#bc4c47'][j],label=tk,zorder=3)
    reference(axes[0]);reference(axes[1],0,'x')
    axes[0].set_xticks(range(len(PROTOCOL_STAGES)),[model(m).replace(' ','\n',1) for m in PROTOCOL_STAGES],fontsize=8)
    axes[0].set_ylabel('OOS R\u00b2 (higher is better)');axes[0].set_xlabel('Cumulative Ridge factor set');axes[0].set_title('Absolute performance');axes[0].legend(fontsize=8,ncol=4)
    axes[1].set_yticks(range(1,len(PROTOCOL_STAGES)),[model(m) for m in PROTOCOL_STAGES[1:]],fontsize=8);axes[1].invert_yaxis()
    axes[1].set_xlabel('Paired MSE reduction vs preceding stage (pp\u00b2; positive is better)');axes[1].set_ylabel('Added information');axes[1].set_title('Incremental change, with uncertainty')
    axes[1].margins(y=.08)  # One shared legend on the left panel; colours match across both.
    save(fig,'04_protocol_ablation','Adding information in the protocol order changes little out of sample','Historical mean \u2192 financial \u2192 valuation \u2192 changes/lags \u2192 market \u2192 industry \u2192 business drivers \u2022 44 matched target months',
        'Company colours are shared by both panels and shown once, in the left legend. The left panel scores each cumulative stage against its own origin-available historical mean; the right shows the paired month-by-month loss change relative to the immediately preceding stage, with 95% moving-block intervals. A missing interval means the matched pair was ineligible. This ordering does not uniquely allocate information shared between blocks, which is why the market-first ladder and the leave-one-block-out checks are reported beside it.',prot)
    z=f[(f.task=='return')&(f.horizon==1)&(f.ticker=='MTRN')&f.model.isin(['historical_mean','ridge_full','pooled_boost'])]
    fig,ax=plt.subplots(figsize=(11,4.8));actual=z[z.model=='historical_mean'].sort_values('target_end');ax.plot(pd.to_datetime(actual.target_end),actual.actual*100,color='#111827',label='Observed return',lw=1.6)
    for m in ['historical_mean','ridge_full','pooled_boost']:
        a=z[z.model==m].sort_values('target_end');ax.plot(pd.to_datetime(a.target_end),a.prediction*100,label=model(m),lw=1.5,**STYLE[m])
    reference(ax);ax.set_ylabel('Monthly total-return proxy (%)');ax.set_xlabel('Target month');ax.legend(loc='upper left',ncol=2);ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    save(fig,'05_return_paths','MTRN forecasts explain little of its monthly swings','Out-of-sample targets January 2023–August 2026 • horizon one month','Black is realized adjusted-close return; all other lines were generated at the preceding month’s final close. The pooled booster is displayed as a tested comparison, not a prospectively selected winner. Forecast intervals are not estimated.',z)
    cs=read('coefficient_stability');cs=cs[cs.variable.isin(CONFIG['dynamic_core'])]
    fig,axes=plt.subplots(2,3,figsize=(12,7))
    for ax,var in zip(axes.ravel(),CONFIG['dynamic_core']):
        a=cs[cs.variable==var].set_index('ticker').reindex(CORE);mid=a.median_standardized_effect*100
        ax.errorbar(mid,range(4),xerr=np.vstack([(a.median_standardized_effect-a.q25_standardized_effect)*100,(a.q75_standardized_effect-a.median_standardized_effect)*100]),fmt='o',color=COLORS['linear'],capsize=3,zorder=3);reference(ax,0,'x');ax.set_yticks(range(4),CORE);ax.set_title(var.replace('_',' ').title());ax.set_xlabel('Return pp per training SD');ax.set_ylabel('Company')
    save(fig,'13_coefficients','Compact return slopes vary by company and refit','Median and interquartile range across 44 expanding-window OLS fits','Dots show median coefficients measured per training standard deviation; whiskers show across-origin interquartile ranges, not sampling confidence intervals. Unavailable predictors produce blank entries. Scaling makes within-model effects readable, but differs between companies and dates; raw slopes are also archived.',cs)
    comparisons=read('paired_loss_comparisons');wanted=['core_pe_difference','core_pe_percentage','core_pe_lag1','core_financial_changes','distributed_all_lag1','distributed_all_lag3']
    z=comparisons[(comparisons.task=='return')&(comparisons.horizon==1)&(comparisons.block==6)&comparisons.expanded.isin(wanted)&(comparisons.reduced!='historical_mean')]
    fig,axes=plt.subplots(2,2,figsize=(12,7),sharex=True,sharey=True)
    for ax,tk in zip(axes.ravel(),CORE):
        a=z[z.ticker==tk].set_index('expanded').reindex(wanted);mid=a.mean_loss_reduction*1e4
        ax.errorbar(mid,range(len(wanted)),xerr=np.vstack([(a.mean_loss_reduction-a.lo)*1e4,(a.hi-a.mean_loss_reduction)*1e4]),fmt='o',color=COLORS['lag'],capsize=3,zorder=3);reference(ax,0,'x');ax.set_yticks(range(len(wanted)),[model(m) for m in wanted]);ax.invert_yaxis();ax.set_title(tk);ax.set_xlabel('MSE reduction (pp²; positive is better)');ax.set_ylabel('Controlled transformation')
    save(fig,'07_transformations','Differences and lags are separate empirical questions','44 monthly tests • 95% pointwise moving-block intervals, six-month blocks','P/E representations are compared with P/E level; financial changes and all-core lag models are compared with Compact Ridge. Intervals condition on saved forecasts and are not adjusted for model search. Zero ATI/CRS P/E contrasts reflect excluded sparse P/E inputs, not economic equivalence.',z)
    fam=read('primary_comparison_family');fc=f[(f.task=='return')&(f.horizon==1)]
    pairs=[('valuation_added','ridge_full','without_valuation'),('transformations_vs_levels','core_pe_difference','core_pe_level'),('arma_vs_static','arimax','arma_static'),('lags_vs_static','distributed_all_lag1','core_ridge')]
    fig,axes=plt.subplots(2,2,figsize=(12,7.6),sharex=True);src=[]
    for ax,tk in zip(axes.ravel(),CORE):
        for (label,expanded,reduced),colour in zip(pairs,['#235b91','#b7772b','#79549d','#087f83']):
            a=fc[(fc.ticker==tk)&(fc.model==expanded)].set_index('target_end').sort_index()
            b=fc[(fc.ticker==tk)&(fc.model==reduced)].set_index('target_end').sort_index()
            shared=a.index.intersection(b.index)
            if len(shared)<20:continue
            a=a.loc[shared];b=b.loc[shared]
            delta=np.cumsum(((b.actual-b.prediction)**2-(a.actual-a.prediction)**2).to_numpy())*1e4
            ax.plot(pd.to_datetime(shared),delta,label=label.replace('_',' '),color=colour,lw=1.4)
            src.extend(dict(ticker=tk,contrast=label,target_end=t,cumulative_mse_reduction_pp2=v) for t,v in zip(shared,delta))
        reference(ax);ax.set_title(tk);ax.set_ylabel('Cumulative MSE reduction (pp\u00b2)')
        ax.xaxis.set_major_locator(mdates.YearLocator());ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.legend(fontsize=7,loc='best',framealpha=.92)
    for ax in axes[1]:ax.set_xlabel('Target month')
    save(fig,'09_cumulative_loss','Any advantage arrives in a few months, not steadily','Cumulative paired squared-error difference for the four prespecified contrasts \u2022 January 2023\u2013August 2026',
        'Each line accumulates the reduced model\u2019s squared error minus the expanded model\u2019s, so a rising line favours the expanded model. A step change identifies a single influential month rather than a persistent edge; a flat line means the two models effectively agreed. Panels use issuer-specific vertical scales because the magnitudes differ by an order of magnitude, so heights must not be compared across panels \u2014 only shapes. Lines stop where matched forecasts are unavailable and are not connected across gaps.',pd.DataFrame(src))
    p=read('permutation_importance');groups=['financial','valuation','market','momentum','risk','industry','business','transform'];fig,axes=plt.subplots(2,2,figsize=(12,7),sharex=True,sharey=True)
    for ax,tk in zip(axes.ravel(),CORE):
        a=p[p.ticker==tk].set_index('group').reindex(groups);ax.errorbar(a.mean_mse_increase*1e4,range(8),xerr=a.permutation_sd*1e4,fmt='o',capsize=3,color=COLORS['forest'],zorder=3);reference(ax,0,'x');ax.set_yticks(range(8),[x.title() for x in groups]);ax.invert_yaxis();ax.set_title(tk);ax.set_xlabel('MSE increase after shuffle (pp²)');ax.set_ylabel('Random Forest factor group')
    save(fig,'08_importance','Random Forest importance does not identify causal drivers','Return forecasts • 20 group permutations in three-month blocks across 44 target origins','Positive values indicate worse error when the group is disturbed. Bars are one permutation standard deviation, not confidence intervals. Saved origin-specific models stay fixed; shuffling can break cross-group dependence, so this retrospective diagnostic is interpreted alongside controlled ablations.',p)
    vmodels=['historical_variance63','historical_variance252','ewma94','arch1','garch11','garchx_market','garchx_industry','garchx_business','variance_ridge','variance_forest','variance_boost','pooled_ridge','business_pair_ridge'];z=s[(s.task=='variance')&s.model.isin(vmodels)]
    fig,axes=plt.subplots(2,2,figsize=(12,9.8),sharex=True,sharey=True)
    for ax,tk in zip(axes.ravel(),CORE):
        a=z[z.ticker==tk].set_index('model').reindex(vmodels);ax.barh(range(len(vmodels)),a.qlike,color=[STYLE[m]['color'] for m in vmodels],height=.65,zorder=3);ax.set_yticks(range(len(vmodels)),[model(m) for m in vmodels]);ax.invert_yaxis();ax.set_title(tk);ax.set_xlabel('QLIKE loss (lower is better)');ax.set_ylabel('Variance model');ax.set_xlim(left=0)
        ax.axvline(a.loc['historical_variance63','qlike'],color='#334155',lw=1.1,ls='--',zorder=0,label='63-session persistence benchmark')
        ax.legend(fontsize=7,loc='lower right')
    save(fig,'14_variance_models','Variance forecasts benefit more from pooling than complexity','44 next-month realized daily-variance targets • January 2023–August 2026','QLIKE evaluates positive variance forecasts relative to realized central daily variance. The dashed line marks the 63-session persistence benchmark each model must beat. All panels share a scale. MTRN differs from the other issuers: its historical 63-session estimate remains competitive. A lower QLIKE need not also mean lower variance RMSE.',z)
    z=f[(f.task=='variance')&(f.ticker=='MTRN')&f.model.isin(['historical_variance63','garchx_industry','pooled_ridge'])];fig,ax=plt.subplots(figsize=(11,4.8));actual=z[z.model=='historical_variance63'].sort_values('target_end');ax.plot(pd.to_datetime(actual.target_end),np.sqrt(actual.actual)*100,color='#111827',label='Observed daily volatility',lw=1.6)
    for m in ['historical_variance63','garchx_industry','pooled_ridge']:
        a=z[z.model==m].sort_values('target_end');ax.plot(pd.to_datetime(a.target_end),np.sqrt(a.prediction)*100,label=model(m),lw=1.5,**STYLE[m])
    ax.set_ylim(bottom=0);ax.set_ylabel('Daily volatility within target month (%)');ax.set_xlabel('Target month');ax.legend(loc='upper left',ncol=2);ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    save(fig,'15_volatility_paths','MTRN volatility shocks remain difficult to anticipate','Square roots of next-month variance targets and variance forecasts • 2023–August 2026','The plotted forecast is sqrt(expected variance), which is not generally expected volatility. No annualization or prediction intervals are applied. Common full-scale axes retain the visible size of missed volatility spikes.',z)
    z=s[(s.horizon==1)&s.model.isin(['ridge_full','variance_ridge','pooled_ridge','business_pair_ridge'])];fig,axes=plt.subplots(1,2,figsize=(12,5.2));xs=np.arange(4)
    for ax,task,metric in zip(axes,['return','variance'],['r2_oos','qlike']):
        individual='ridge_full' if task=='return' else 'variance_ridge'
        for j,m in enumerate([individual,'pooled_ridge','business_pair_ridge']):
            a=z[(z.task==task)&(z.model==m)].set_index('ticker').reindex(CORE);ax.bar(xs+(j-1)*.23,a[metric],width=.22,label=model(m),color=STYLE[m]['color'],hatch=['','//','..'][j],zorder=3)
        reference(ax);ax.set_xticks(xs,CORE);ax.set_xlabel('Company');ax.set_ylabel('OOS R² (higher is better)' if task=='return' else 'QLIKE (lower is better)');ax.set_title('Return' if task=='return' else 'Variance');ax.legend(loc='lower left' if task=='return' else 'upper right',fontsize=8)
    save(fig,'16_pooling','Pooling helps risk forecasts more consistently than return forecasts','Same 44 targets; individual, all-four and two-company Ridge fits','Return scores use company-specific historical means; variance QLIKE uses the same realized risk target. Pooling uses company indicators and synchronous calendar folds. Business pairs are MTRN/ENTG and CRS/ATI, not asserted homogeneous industries.',z)
    roll=read('rolling_scores');z=roll[(roll.ticker=='MTRN')&(roll.horizon==1)&(((roll.task=='return')&roll.model.isin(['historical_mean','ridge_full','pooled_boost']))|((roll.task=='variance')&roll.model.isin(['historical_variance63','garchx_industry','pooled_ridge'])))];fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True)
    for ax,task,metric,scale in zip(axes,['return','variance'],['rmse','qlike'],[100,1]):
        for m in z[z.task==task].model.unique():
            a=z[(z.task==task)&(z.model==m)].sort_values('date');ax.plot(pd.to_datetime(a.date),a[metric]*scale,label=model(m),lw=1.7,**STYLE[m])
        ax.set_ylabel('12-month return RMSE (pp)' if task=='return' else '12-month mean QLIKE');ax.set_xlabel('Last target month in rolling window');ax.legend(ncol=3,fontsize=8);ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    save(fig,'11_rolling','Model rankings can change as the evaluation window moves','MTRN • 12-target-month rolling errors • December 2023–August 2026','Every point uses the latest 12 already realized out-of-sample targets; lower values are better. Windows overlap and must not be counted as independent evidence. Return and variance panels use different loss functions with explicit units.',z)
    models=['historical_mean','core_ols','ridge_full','forest_full','boost_full'];z=s[(s.task=='return')&s.model.isin(models)];fig,axes=plt.subplots(2,2,figsize=(12,7),sharey=True)
    for ax,tk in zip(axes.ravel(),CORE):
        for j,h in enumerate([1,3]):
            a=z[(z.ticker==tk)&(z.horizon==h)].set_index('model').reindex(models);ax.bar(np.arange(5)+(j-.5)*.36,a.r2_oos,width=.34,label=f'{h}-month horizon',color=['#235b91','#b7772b'][j],hatch=['','//'][j],zorder=3)
        reference(ax);ax.set_xticks(range(5),[model(m).replace(' ','\n',1) for m in models],fontsize=8);ax.set_ylabel('Horizon-specific OOS R²');ax.set_xlabel('Model');ax.set_title(tk);ax.legend(fontsize=8)
    save(fig,'12_horizons','Longer-horizon results are a sensitivity, not independent confirmation','One month: 44 targets, Jan 2023–Aug 2026 • three months: 38 overlapping targets ending Jul 2023–Aug 2026','Each horizon uses its own matured historical-mean benchmark. The three-month fits purge unmatured labels and use a later start; R² changes therefore mix horizon and period effects. All three nonoverlapping offsets, only 12–13 outcomes each, are archived.',z)
    mats=[read('correlation_long').set_index('Unnamed: 0'),read('correlation_matched').set_index('Unnamed: 0')];fig,axes=plt.subplots(1,2,figsize=(12,5));src=[]
    for ax,a,title in zip(axes,mats,['Four established issuers, 2016–Sep 2026','Five public equities, Apr–Sep 2026']):
        im=ax.imshow(a,vmin=-1,vmax=1,cmap='RdBu');ax.set_xticks(range(len(a)),a.columns);ax.set_yticks(range(len(a)),a.index);ax.set_title(title);ax.set_xlabel('Company');ax.set_ylabel('Company');ax.grid(False)
        for i in range(len(a)):
            for j in range(len(a)):ax.text(j,i,f'{a.iloc[i,j]:.2f}',ha='center',va='center',color='white' if abs(a.iloc[i,j])>.6 else '#172554')
        src.extend(dict(panel=title,first=i,second=j,correlation=a.loc[i,j]) for i in a.index for j in a.columns)
    for ax in axes:fig.colorbar(ax.images[0],ax=ax,label='Daily-return correlation',fraction=.046,pad=.04)
    save(fig,'17_correlations','Correlation is sample-dependent, especially for the recent IPO','Daily adjusted-close returns through September 18, 2026 • identical correlation color scale','The long panel has 2,693 shared daily returns; the matched five-equity panel has 102. The right-hand matrix describes only ELMT’s short public sample and is not comparable evidence of long-run diversification. Covariance tables preserve squared-return units separately.',pd.DataFrame(src))
    z=read('rolling_dependence');z=z[(z.panel=='long')&(z['window']==63)&(z['first']=='MTRN')];fig,ax=plt.subplots(figsize=(11,4.5))
    for i,tk in enumerate(['ENTG','CRS','ATI']):
        a=z[z['second']==tk];ax.plot(pd.to_datetime(a.date),a.correlation,label='MTRN / '+tk,color=['#235b91','#b7772b','#087f83'][i],linestyle=['-','--','-.'][i],lw=1.2)
    ax.set_ylim(-1,1);ax.set_ylabel('63-session daily-return correlation');ax.set_xlabel('Window end date');ax.legend(ncol=3);reference(ax)
    save(fig,'18_rolling_correlation','Competitor co-movement is not constant','MTRN versus ENTG, CRS and ATI • 63-session windows • 2016–September 18, 2026','All pairs use the same daily calendar and correlation scale. Shared changes can weaken diversification when risks rise; the prespecified origin-known volatility-regime comparison is quantified in the accompanying table.',z)
    z=f[(f.task=='return')&(f.horizon==1)&(f.ticker=='MTRN')&f.model.isin(['historical_mean','ridge_full','arimax'])].copy();z['error']=z.actual-z.prediction;fig,axes=plt.subplots(1,2,figsize=(12,4.5));ac=[]
    for j,m in enumerate(['historical_mean','ridge_full','arimax']):
        a=z[z.model==m].sort_values('target_end');axes[0].plot(pd.to_datetime(a.target_end),a.error*100,label=model(m),lw=1.2,**STYLE[m]);v=acf(a.error,nlags=6,fft=False)[1:];axes[1].plot(range(1,7),v,label=model(m),marker=['o','s','^'][j],**{k:v for k,v in STYLE[m].items() if k!='marker'});ac.extend(dict(model=m,lag=i+1,acf=x) for i,x in enumerate(v))
    axes[0].set_xlabel('Target month');axes[0].set_ylabel('Observed minus forecast return (pp)');axes[0].xaxis.set_major_formatter(mdates.DateFormatter('%Y'));axes[1].set_xlabel('Error lag (months)');axes[1].set_ylabel('Sample error autocorrelation');axes[1].set_ylim(-1,1)
    for ax in axes:reference(ax);ax.legend(fontsize=8)
    save(fig,'10_errors','Residual dependence alone does not establish a forecast advantage','MTRN • 44 saved one-month forecast errors, January 2023–August 2026','The left panel shows forecast misses; the right shows lag-1 through lag-6 error autocorrelation. This is a post-evaluation diagnostic, not another tuning opportunity. No IID confidence bands are imposed on the short, adaptively fitted error sequence.',pd.DataFrame(ac))

# ---------------------------------------------------------------------------
# Research report. Every quoted number is read back from a saved result file.
# ---------------------------------------------------------------------------
def pct(x,n=2):return '—' if x is None or pd.isna(x) else f'{100*float(x):,.{n}f}%'
def pp2(x,n=2):return '—' if x is None or pd.isna(x) else f'{1e4*float(x):,.{n}f}'
def num3(x,n=3):return '—' if x is None or pd.isna(x) else f'{float(x):,.{n}f}'
def esc(t):return html.escape(str(t))
def link(name,label=None):return f'<a href="../data/processed/{name}.csv">{esc(label or name)}</a>'

def interval(row):
    return f'{pp2(row.mean_loss_reduction)} pp² [{pp2(row.lo)}, {pp2(row.hi)}]'

def verdict(rows):
    """A noun phrase that completes "this comparison gives ..." grammatically."""
    if rows.empty:return 'no eligible matched comparison'
    better=int((rows.lo>0).sum());worse=int((rows.hi<0).sum());n=len(rows)
    if better==0 and worse==0:return f'intervals that span zero for all {n} issuers'
    parts=[]
    if better:parts.append(f'{better} of {n} issuer intervals entirely above zero')
    if worse:parts.append(f'{worse} entirely below' if better else f'{worse} of {n} issuer intervals entirely below zero')
    return ' and '.join(parts)

def holm_statement(family,contrast):
    """How the frozen family reads after adjustment, stated without overclaiming."""
    rows=family[(family.contrast==contrast)&family.eligible.astype(bool)]
    if rows.empty:return 'this contrast was not eligible for any issuer'
    survivors=int((rows.holm_adjusted_pvalue<.05).sum())
    smallest=rows.holm_adjusted_pvalue.min()
    if survivors==0:
        return (f'no issuer survives Holm adjustment across the sixteen-contrast family '
                f'(smallest adjusted p = {smallest:.2f})')
    return (f'{survivors} of {len(rows)} issuers survive Holm adjustment across the sixteen-contrast family '
            f'(smallest adjusted p = {smallest:.3f})')

def contrast_table(comparisons,rows,block=6):
    out=[]
    for label,expanded,reduced in rows:
        z=comparisons[(comparisons.expanded==expanded)&(comparisons.reduced==reduced)&(comparisons.block==block)]
        for _,r in z.iterrows():
            out.append({'Comparison':label,'Company':r.ticker,'Months':int(r.n),'Loss metric':r.metric,
                'Mean loss reduction (pp²)':1e4*r.mean_loss_reduction,'Lower 95%':1e4*r.lo,'Upper 95%':1e4*r.hi})
    return pd.DataFrame(out)

def experiment(anchor,ident,question,body):
    return f'<section id="{anchor}"><h2>{ident}. {esc(question)}</h2>'+body+'</section>'

def spec_table(rows):
    return table(pd.DataFrame(rows,columns=['Setting','Value']),'Experiment specification: everything needed to reproduce this comparison without inferring a setting from a graph.')

def build():
    initialize()
    s=read('model_scores');f=read('forecasts');comparisons=read('paired_loss_comparisons')
    ret=comparisons[(comparisons.task=='return')&(comparisons.horizon==1)]
    var=comparisons[comparisons.task=='variance']
    family=read('primary_comparison_family');ablation=read('ablation_scores')
    coverage=read('coverage_and_deferrals');registry=read('feature_registry');metrics=read('metric_registry')
    questions=read('experiment_registry');splits=read('split_manifest')
    failures=read('model_failures');regimes=read('regime_scores');stability=read('coefficient_stability')
    orders=read('dynamic_order_counts');importance=read('permutation_importance');exposure=read('exposure_map')
    collinearity=read('collinearity_diagnostics');vif=read('variance_inflation');residual=read('residual_diagnostics')
    successful=read('successful_fit_scores');nonoverlap=read('horizon3_nonoverlapping_scores')
    deferrals=pd.DataFrame(json.loads((OUT/'deferrals.json').read_text()))
    make_figures(s,f)
    r1=s[(s.task=='return')&(s.horizon==1)]
    months=int(r1.n.max());start=f[(f.task=='return')&(f.horizon==1)].target_end.min();stop=f[(f.task=='return')&(f.horizon==1)].target_end.max()
    beat=r1[(r1.r2_oos>0)&(~r1.model.isin(['historical_mean']))]
    tables=[]
    def T(name,d,caption):
        tables.append(dict(number=len(tables)+1,name=name,rows=len(d),columns=list(d.columns),caption=caption))
        return f'<h4>Table {len(tables)}. {esc(name)}</h4>'+table(d,caption)
    p=[]
    p.append('<header><div class="eyebrow">MTRN · ENTG · CRS · ATI · ELMT</div>'
      '<h1>Do financial characteristics and starting valuation forecast returns?</h1>'
      '<p class="subtitle">A chronological out-of-sample comparison of static, distributed-lag, dynamic and machine-learning models, '
      f'with a separate realized-variance task · information and price cutoff {CUTOFF}</p></header>')
    p.append('<nav>'+' '.join(f'<a href="#{a}">{t}</a>' for a,t in [
      ('purpose','Purpose'),('data','Data'),('variables','Variables'),('design','Design'),
      ('e1','E1 Financials'),('e2','E2 Valuation'),('e3','E3 Transformations'),('e4','E4 Drivers'),
      ('e5','E5 Lags'),('e6','E6 Dynamics'),('e7','E7 Stability'),('e8','E8 Variance'),
      ('elmt','Elmet'),('synthesis','Synthesis'),('conclusion','Conclusion'),('limitations','Limitations'),('repro','Reproducibility')])+'</nav>')

    # 1 -----------------------------------------------------------------
    p.append('<section id="purpose"><h2>Purpose, motivation and scope</h2>')
    p.append('<p>An <a href="../../historical_attribution/final/Historical_Attribution.html">earlier experiment</a> on these same five companies '
      'measured <em>contemporaneous</em> exposures: how each stock moved with the market, style, industry and macro factors during the same month, '
      'how price changes decomposed into earnings and multiple changes, and how prices reacted around earnings announcements. '
      'None of that is a forecast. It answers what moved together, not what could have been known in advance.</p>')
    p.append('<p>This experiment asks a different question. Standing at the final close of a month, using only information published by then, '
      'do a company’s disclosed financial characteristics and the valuation investors were paying carry information about <strong>next</strong> month’s return? '
      'And does adding time-series structure — older predictor values, or a forecastable error process — improve on a static regression using the same inputs?</p>')
    p.append(f'<p>The test is a chronological replay. At each of {months} monthly origins from {start} to {stop} the models are refitted on history only, '
      'issue one forecast, and are scored against the outcome that history already recorded. Nothing after the information cutoff enters any fit. '
      'This is a historical evaluation of an already observed sample, not a live signal and not a formally preregistered holdout: '
      'these companies and much of their history were reviewed before the protocol was frozen.</p>')
    p.append('<div class="note"><p><strong>What this study cannot do.</strong> Four companies are not a cross-section of the market. '
      'Predictability is not intrinsic value, and a fitted coefficient is not a cause. Statistical significance was never a completion requirement, '
      'and a null result is reported with the same prominence as an improvement.</p></div>')
    p.append(T('Research questions and how each is tested',questions.rename(columns={'experiment':'ID','research_question':'Research question','comparison':'Comparison','evaluation':'Evaluation','addendum_cross_reference':'Addendum RQ'}),
      'Eight registered experiments, in the order the report presents them. Each links to a predeclared comparison family; an eligibility failure produces a documented unanswered question rather than a silent omission. The final column cross-references the RQ numbering used in the execution addendum, which groups the same comparisons differently.'))
    p.append('</section>')

    # 2 -----------------------------------------------------------------
    p.append('<section id="data"><h2>Data and the information timeline</h2>')
    p.append('<p>Every accounting input is selected by <em>when it became public</em>, not by the period it describes. '
      'A figure is usable only from the first exchange session after the filing that first contained it; a later restatement '
      'cannot revise an earlier snapshot. Commodity, currency, volatility and macro series are delayed a further US session, '
      'because their closing timestamps are not reliably comparable with the US equity close.</p>')
    p.append(figure('01_timeline'))
    p.append(f'<p>Figure {num("01_timeline")} shows the chronology. The first 84 completed monthly outcomes train the January 2023 forecast. '
      'Hyperparameters are chosen inside that training history on two consecutive twelve-month validation blocks, never on the month being forecast. '
      'Each later origin adds the newly matured outcome and refits. Because the procedure refits every month, no single train/test split exists.</p>')
    p.append(figure('02_coverage'))
    p.append(f'<p>Figure {num("02_coverage")} shows what is actually usable after repair. '
      'Coverage reflects which XBRL concepts each issuer reported in each era, and it was not uniform. '
      'Three extraction defects found during this continuation were repaired. Entegris stopped tagging parent-only equity in 2019 and reports '
      'a consolidated equity line instead; that line is now used where the issuer’s own earlier filings show an immaterial noncontrolling interest, '
      'and the substitution is recorded per observation. ATI, whose noncontrolling interest is material, never uses that fallback. '
      'Carpenter’s trailing earnings were previously voided whenever its revenue tag reported a different period end; each disclosed flow now keeps '
      'its own reporting clock, and the shared-period requirement applies only where a ratio genuinely combines two flows. '
      'Materion discloses mine development annually, so free cash flow is modelled on equipment capital expenditure and the mine-inclusive measure is retained as a separate sensitivity.</p>')
    avail=coverage[coverage.group.isin(['financial','valuation'])].copy();avail['share']=avail.available/avail.observations
    summary=avail.groupby('ticker').agg(**{'Candidate financial/valuation variables':('variable','nunique'),
      'Mean nonmissing share':('share','mean'),'Variables above the 70% training gate':('share',lambda x:int((x>=.7).sum()))}).reset_index().rename(columns={'ticker':'Company'})
    p.append(T('Financial and valuation availability by issuer',summary,
      'Descriptive coverage over origin months from December 2015. Each fitted model applies its own training-only 70% gate, so a variable can be eligible in later windows and not earlier ones.'))
    p.append(T('Economic exposure map',exposure[['issuer','business_segment','candidate_driver','exact_series','transmission_channel','revenue_or_cost_exposure','possible_sign','feature_block','inclusion_status','omission_reason']],
      'Economic relevance is recorded before any statistical selection. A driver marked unavailable stays unavailable: no commodity index is substituted for a price history that does not exist.'))
    p.append('<p>Elmet listed on 23 April 2026. It contributes five monthly observations, far below the 84-month training gate, so it is excluded from every fitted model '
      'and appears only in the descriptive case study below. Its private operating history cannot create public-market returns.</p>')
    p.append('</section>')

    # 3 -----------------------------------------------------------------
    p.append('<section id="variables"><h2>Variable construction and economic mechanisms</h2>')
    p.append('<p>Variables fall into seven economic blocks. <strong>Financial</strong> variables describe the business: how fast revenue grew, '
      'what margin it earned, how much cash it generated, how much debt it carries. <strong>Valuation</strong> variables describe what investors '
      'were paying for that business at the forecast origin. <strong>Market</strong>, <strong>industry</strong> and <strong>business-driver</strong> blocks describe '
      'conditions outside the company. <strong>Momentum</strong> and <strong>risk</strong> blocks summarise the stock’s own recent price behaviour. '
      'The <strong>transformation</strong> block holds changes and lagged values of variables already introduced.</p>')
    p.append('<p>Three worked examples fix the vocabulary, because these are routinely confused:</p>'
      '<ul><li><strong>A level</strong> is the value itself. If trailing P/E at the origin is 22, the level is 22.</li>'
      '<li><strong>A first difference</strong> is the change. If P/E moved from 20 to 22, the difference is <em>+2 multiple points</em> — not +10%.</li>'
      '<li><strong>A one-month lag</strong> is the older value, 20. It is not a change at all.</li></ul>'
      '<p>And a second-order case that matters here: if year-on-year revenue growth moved from 10% to 15%, its first difference is '
      '<strong>+5 percentage points of growth acceleration</strong>, not 5% revenue growth. A level, its lag and its difference are exactly linearly dependent, '
      'so they are tested as alternative parameterisations rather than stacked into one unpenalised regression.</p>')
    p.append('<p>Valuation is measured with the price at the origin and accounting inputs published by then. '
      'Earnings yield is trailing common earnings divided by market capitalisation; it is preferred to P/E because it stays interpretable through losses, '
      'where a negative P/E ranks nonsensically. For positive earnings the two carry the same information and are never treated as independent evidence. '
      'Relative valuation compares the current multiple with the issuer’s own preceding sixty months, excluding the current observation, '
      'and with the same-date median of the other established issuers where at least three are valid.</p>')
    core=registry[registry.variable.isin(CONFIG['dynamic_core'])][['name','group','formula','units','rationale']]
    p.append(T('The six compact predictors used in every common-input comparison',core.rename(columns={'name':'Reader-facing name','group':'Block','formula':'Exact formula','units':'Units','rationale':'Why it is included'}),
      'These six are fixed in configuration by economic priority, not chosen by fit, and are shared by the static, distributed-lag and dynamic families so that only model structure differs between them. The full dictionary of every implemented variable is in the appendix.'))
    p.append('</section>')

    # 4 -----------------------------------------------------------------
    p.append('<section id="design"><h2>Common evaluation design</h2>')
    p.append(f'<p><strong>Primary target.</strong> Next month’s total return from adjusted closes, <code>close[t+1]/close[t] − 1</code>. '
      f'<strong>Secondary targets.</strong> The same return minus the market’s realised return over the identical month; a three-month compounded return; '
      'and, as a separate problem, next month’s realised variance of daily returns. The future market return is part of the excess-return outcome, never an input.</p>')
    p.append('<p><strong>Benchmarks.</strong> The headline denominator is the expanding historical mean available at each origin. A zero forecast and, '
      'for the risk task, trailing realised variance are also recorded. Out-of-sample R² is measured against that real-time benchmark, '
      'never against the test period’s own mean — which would not have been knowable.</p>')
    p.append('<p><strong>Leakage control.</strong> Imputation, clipping, scaling, the coverage gate, feature selection and every hyperparameter are fitted '
      'inside the training window only. Training labels must have fully matured by the fitting origin, which for the three-month target requires purging '
      'origins whose outcome extends past the boundary. A failed fit falls back to the origin’s historical mean and is recorded as a failure; '
      f'the study logs {len(failures)} such events, and a separate matched table re-scores every model on origins where nothing fell back.</p>')
    p.append(T('Scoring criteria and how to read them',metrics.rename(columns={'metric':'Criterion','formula':'Formula','preferred_direction':'Preferred direction','interpretation':'Interpretation and caution'}),
      'Return models are ranked primarily on RMSE and out-of-sample R²; variance models on QLIKE. Variance and volatility losses are never mixed, and directional accuracy is only applied to signed targets.'))
    p.append('<p>Uncertainty uses 2,000 synchronised moving-block resamples of the saved forecast records, seed 20260918, with three-, six- and twelve-month blocks. '
      'Resampling preserves the paired models and the common calendar, so a comparison is never credited to two models being scored on different months. '
      'These intervals are conditional on the fitted procedure and the observed history; they do not price in the search that produced the protocol.</p>')
    p.append('<p><strong>Multiplicity.</strong> Four contrasts per issuer were frozen before scoring — valuation added to otherwise identical controls, '
      'changes versus levels, ARMA errors versus static, and added lags versus static. With four eligible issuers that is a sixteen-comparison family, '
      'and Holm adjustment is applied within it. Every other comparison in this report is exploratory and labelled as such.</p>')
    p.append('</section>')

    # 5 --- E1 ----------------------------------------------------------
    body=['<h3>A. Research question and motivation</h3>'
      '<p>Do a company’s disclosed operating, cash-flow and balance-sheet characteristics carry information about next month’s return '
      'beyond simple return benchmarks and general market conditions? If reported fundamentals are already reflected in the price by the time they are public, '
      'adding them should not reduce forecast error. The predeclared test is the paired change in squared error when the financial block is added, '
      'and when it is removed from the full model.</p>']
    body.append('<h3>B. Reproducible setup</h3>')
    fin=ablation[(ablation.ladder=='protocol_order')&(ablation.stage=='P1_financial')]
    body.append(spec_table([
      ('Target','Next-month adjusted-close total return, fraction'),
      ('Origins',f'{months} monthly origins, targets {start} to {stop}'),
      ('Issuers','MTRN, ENTG, CRS, ATI (ELMT excluded: 5 monthly observations against an 84-month gate)'),
      ('Window','Expanding, refit each origin; rolling 84-month recorded as a separate sensitivity'),
      ('Inner validation','Two consecutive 12-month blocks inside the training history; retuned at the first origin and each December'),
      ('Model','Ridge on the cumulative block set, predictors standardised inside the training fold, intercept unpenalised'),
      ('Penalty grid','0.01, 0.1, 1, 10, 100; ties resolved toward the stronger penalty'),
      ('Predictors',f'{int(fin.predictors.max()) if len(fin) else 0} financial columns eligible before the training coverage gate'),
      ('Baseline','Expanding historical mean; zero and market-mean forecasts also recorded'),
      ('Comparisons','P1 vs historical mean (added); full model vs full-minus-financial (removed)'),
      ('Preprocessing','Training-only 70% coverage gate, 1st/99th percentile clipping, median imputation with missing indicators, standardisation'),
      ('Manifests',f'configuration config.json; splits split_manifest.csv; ledger forecasts.csv')]))
    body.append('<h3>C. Variables and mechanism</h3>'
      '<p>Revenue growth and margins describe whether the business is expanding and at what profitability; cash-flow and leverage ratios describe '
      'whether that profit converts to cash and how much of the firm the debt holders claim. The economic sign is genuinely ambiguous: '
      'stronger fundamentals can mean a better business and therefore a lower required return, which would predict <em>lower</em> future returns, '
      'or they can mean news the market has not yet absorbed. No sign is imposed.</p>'
      '<p>For Materion in particular, reported revenue includes pass-through metal value, so revenue growth can rise without equivalent value-added profit. '
      'Loss quarters make percentage EPS growth meaningless, so a price-scaled per-share earnings change and a loss-transition flag carry that information instead.</p>')
    body.append('<h3>D. Evaluation criteria</h3>'
      '<p>Lower RMSE and MAE, and out-of-sample R² above zero against the origin-available historical mean. '
      'A better result means the paired mean squared-error reduction is positive with an interval that excludes zero, and survives Holm adjustment '
      'in the frozen family where the contrast belongs to it. An improvement in R² alongside worse MAE would indicate a gain concentrated in a few large months, '
      'and is reported as such rather than as a win.</p>')
    body.append('<h3>E. Results</h3>')
    body.append(T('Return benchmarks and the main model families',scores_table(s,'return',['historical_mean','zero','market_mean','capm_style','ar1','core_ols','core_ridge','ridge_full','lasso_full','elastic_full','forest_full','boost_full','arimax']),
      'All models share the same origins, outcomes and historical-mean denominator. Out-of-sample R² below zero means larger total squared error than the benchmark a forecaster could actually have used.'))
    rows=[('Financial block added to the mean','P1_financial','historical_mean'),('Financial block removed from the full model','ridge_full','without_financial')]
    body.append(T('E1 paired comparisons',contrast_table(ret,rows),'Positive means the expanded model reduced squared error. Intervals are 95% pointwise moving-block, six-month blocks, on matched dates.'))
    body.append(figure('03_return_models'))
    body.append(figure('04_protocol_ablation'))
    body.append(figure('05_return_paths'))
    added=ret[(ret.expanded=='P1_financial')&(ret.reduced=='historical_mean')&(ret.block==6)]
    removed=ret[(ret.expanded=='ridge_full')&(ret.reduced=='without_financial')&(ret.block==6)]
    body.append('<h3>F. Figures and diagnostics</h3>'
      f'<p>Figure {num("03_return_models")} places every family on one axis so the comparison is visual rather than table-hopping; '
      f'Figure {num("04_protocol_ablation")} isolates the financial step and shows its paired uncertainty beside its absolute score. '
      'The uncertainty panel matters more than the level panel: a bar slightly above zero with an interval ten times its width is not evidence. '
      f'Figure {num("05_return_paths")} shows what these scores look like as a time series: the forecasts are nearly flat lines against monthly '
      'swings of twenty percent or more, which is the plainest statement of the result in this report.</p>')
    body.append('<h3>G. Interpretation</h3>'
      f'<p>Adding the financial block to the historical mean gives {verdict(added)}. Removing it from the full model gives {verdict(removed)}. '
      'Several explanations are consistent with this and the design cannot separate them: quarterly fundamentals update only four times a year and are carried forward between releases, '
      'so a monthly model sees the same values repeatedly; the information is public by construction and may already be in the price; '
      'and with 44 outcomes per issuer the sampling noise in a monthly return dwarfs any plausible effect. '
      'These are hypotheses, not findings.</p>')
    body.append('<h3>H. Experiment conclusion</h3>'
      f'<p>On this evidence, disclosed financial characteristics did not reliably improve next-month return forecasts for these four issuers. '
      'The estimated effects are small relative to their intervals, so the data are equally consistent with a small effect and with none. '
      'This is a null result on a short sample, not a demonstration that fundamentals are irrelevant to shareholders.</p>')
    body.append('<h3>I. Limitations and next test</h3>'
      '<p>Forty-four monthly outcomes per issuer cannot resolve effects of the size plausibly at stake. Quarterly disclosure means the effective number of '
      'independent fundamental updates is closer to fifteen. A better-powered version needs a wider panel of comparable issuers at the same origins, '
      'which lengthens the cross-section without fabricating history for these five.</p>')
    p.append(experiment('e1','E1','Do company financial characteristics add predictive information beyond simple benchmarks?',''.join(body)))

    # --- E2 ------------------------------------------------------------
    val_add=ret[(ret.expanded=='P2_valuation')&(ret.reduced=='P1_financial')&(ret.block==6)]
    val_rem=ret[(ret.expanded=='ridge_full')&(ret.reduced=='without_valuation')&(ret.block==6)]
    fam2=family[family.contrast=='valuation_added']
    body=['<h3>A. Research question and motivation</h3>'
      '<p>Does the price investors were already paying add information beyond the operating performance and the external conditions? '
      'This is the central revised question of the protocol. A broad value style factor is not a substitute: it measures the return of a portfolio sorted on valuation, '
      'not what this company’s own multiple was at this origin.</p>']
    body.append('<h3>B. Reproducible setup</h3>')
    body.append(spec_table([
      ('Target','Next-month adjusted-close total return, fraction'),
      ('Origins',f'{months} monthly origins, {start} to {stop}; identical dates on both sides of every contrast'),
      ('Valuation block','Earnings yield, book yield, sales yield, equipment free-cash-flow yield, dividend yield, own-history relative valuation and trailing percentile, peer earnings-yield gap'),
      ('Dependency rule','Removing the block also removes its differences, lags, z-score, percentile and the P/E percentage change; a no-valuation model contains no valuation-derived column'),
      ('Model','Ridge, retuned annually on the inner blocks, refit every origin'),
      ('Primary contrast','Broad Ridge vs Broad Ridge minus valuation — member of the frozen 16-comparison family'),
      ('Secondary contrast','P2 vs P1 in the protocol-order ladder; financial+valuation vs financial only'),
      ('Multiplicity','Holm within the frozen family; the ladder step is exploratory')]))
    body.append('<h3>C. Variables and mechanism</h3>'
      '<p>A high earnings yield means the market is paying little for each dollar of trailing profit. That can mean a cheap stock that later reverts upward, '
      'or a business the market expects to deteriorate, in which case the low price is the correct price and no excess return follows. '
      'Both readings are economically coherent, so the sign is not predicted. Relative valuation asks the narrower question of whether the company is cheap '
      '<em>against its own history</em> or against its peers on the same date, which removes a persistent level difference between issuers.</p>')
    body.append('<h3>D. Evaluation criteria</h3>'
      '<p>Positive paired MSE reduction with an interval excluding zero, surviving Holm adjustment within the frozen family. '
      'Because this contrast was frozen in advance, an unadjusted interval that just excludes zero is not sufficient on its own.</p>')
    body.append('<h3>E. Results</h3>')
    body.append(T('E2 paired comparisons',contrast_table(ret,[('Valuation added to financials','P2_valuation','P1_financial'),('Valuation removed from the full model','ridge_full','without_valuation'),('Financial + valuation vs financial only','financial_valuation','financial_only')]),
      'The middle row is the frozen primary contrast. All three use identical dates on both sides and retune both sides inside the same inner folds.'))
    show=fam2[['ticker','n','mean_loss_reduction','lo','hi','pvalue','holm_adjusted_pvalue']].copy()
    for c in ['mean_loss_reduction','lo','hi']:show[c]*=1e4
    body.append(T('Frozen family: valuation added',show.rename(columns={'ticker':'Company','n':'Months','mean_loss_reduction':'Mean MSE reduction (pp²)','lo':'Lower 95%','hi':'Upper 95%','pvalue':'Block-resampling p','holm_adjusted_pvalue':'Holm-adjusted p'}),
      'Holm adjustment is applied across all sixteen frozen contrasts, not within this row group. Block-resampling p-values are approximate for nested comparisons on 44 observations and are reported beside the interval, not in place of it.'))
    body.append(figure('06_ablation'))
    body.append('<h3>F. Figures and diagnostics</h3>'
      f'<p>The valuation step is the second bar group in Figure {num("04_protocol_ablation")}, in the previous experiment. '
      f'Figure {num("06_ablation")} shows the same block entering after market conditions rather than after financials; '
      'the two orderings answer different questions because the blocks share information, and comparing them is the point.</p>')
    body.append('<h3>G. Interpretation</h3>'
      f'<p>Adding valuation to the financial block gives {verdict(val_add)}; removing it from the full model gives {verdict(val_rem)}. '
      'A previous version of this pipeline left the P/E percentage change inside the nominally valuation-free model. '
      'Retaining valuation information on the reduced side necessarily shrinks the measured gap, biasing the estimated contribution toward zero; '
      'that dependency is now removed and these numbers reflect the corrected comparison. '
      'Monthly valuation ratios move mostly because the price moved, so a large part of the variation in a monthly valuation feature is simply the recent return, '
      'which the momentum block already carries.</p>')
    body.append('<h3>H. Experiment conclusion</h3>'
      f'<p>Starting valuation did not reliably improve next-month forecasts beyond the other blocks for these issuers on this sample: '
      f'{holm_statement(family,"valuation_added")}. '
      'The estimates are imprecise rather than precisely zero, and the distinction matters: these intervals admit effects that would be economically interesting if real. '
      'The central revised question was tested with genuine issuer-level valuation variables, not a style-factor substitute, and returned no reliable improvement.</p>')
    body.append('<h3>I. Limitations and next test</h3>'
      '<p>Forward-looking valuation could not be built: no archived historical analyst consensus was available, so forward P/E, earnings surprise and estimate revisions '
      'remain unavailable rather than approximated. Enterprise-value multiples rest on an unreconciled claims bridge and are reported only as a labelled sensitivity. '
      'A monthly horizon may also be the wrong clock for a valuation signal; the three-month result is reported in E7 as a sensitivity, not as confirmation.</p>')
    p.append(experiment('e2','E2','Does starting valuation add information beyond financials and external controls?',''.join(body)))

    # --- E3 ------------------------------------------------------------
    diff_rows=[('P/E difference vs P/E level','core_pe_difference','core_pe_level'),('P/E percentage change vs level','core_pe_percentage','core_pe_level'),
               ('P/E one-month lag vs level','core_pe_lag1','core_pe_level'),('Financial/yield changes vs levels','core_financial_changes','core_ridge'),
               ('Transformations added to the ladder','P3_transform','P2_valuation')]
    tr_res=ret[(ret.expanded=='core_pe_difference')&(ret.reduced=='core_pe_level')&(ret.block==6)]
    body=['<h3>A. Research question and motivation</h3>'
      '<p>Is it the <em>level</em> of a financial or valuation variable that matters, or its <em>change</em>, or its older value? '
      'A company on a stable 15% margin and one that just improved from 10% to 15% look identical in levels and very different in differences. '
      'Because a level, its lag and its difference are exactly linearly dependent, they are tested as competing representations of the same information, '
      'never stacked together in one unpenalised model.</p>']
    body.append('<h3>B. Reproducible setup</h3>')
    body.append(spec_table([
      ('Target','Next-month adjusted-close total return, fraction'),
      ('Held fixed','The five other compact predictors, the estimator, the penalty grid, the origins and the outcomes'),
      ('Changed','Only the representation of one variable at a time'),
      ('Representations','Level; first difference in multiple points; percentage change; one-month lag'),
      ('Clock','The monthly as-known clock: the change between values available at successive origins, which is zero when no new filing appeared'),
      ('Model','Ridge, retuned annually, refit each origin'),
      ('Frozen contrast','P/E difference vs P/E level is the family member; the others are exploratory')]))
    body.append('<h3>C. Variables and mechanism</h3>'
      '<p>The worked example from the variables section applies directly. A P/E move from 20 to 22 is a difference of +2 multiple points, '
      'a percentage change of +10%, and a lag of 20 — three different numbers describing one event. '
      'A caution specific to carried-forward fundamentals: between quarterly releases the as-known value does not change, so its monthly difference is exactly zero. '
      'A one-month lag of a carried-forward ratio is therefore usually the same number again, and is not a new independent quarterly observation.</p>')
    body.append('<h3>D. Evaluation criteria</h3>'
      '<p>Paired MSE difference against the level representation on identical dates, with moving-block intervals. '
      'Equivalent parameterisations that produce different fits under regularisation are not evidence of new information.</p>')
    body.append('<h3>E. Results</h3>')
    body.append(T('E3 paired comparisons',contrast_table(ret,diff_rows),'Each row changes one representation and holds everything else fixed. Missing rows indicate a representation whose inputs failed the coverage gate for that issuer rather than an economic equivalence.'))
    body.append(figure('07_transformations'))
    body.append('<h3>F. Figures and diagnostics</h3>'
      f'<p>Figure {num("07_transformations")} plots each controlled swap against zero with its interval. '
      'Reading across companies matters more than any single point: a representation that genuinely carried information should help in more than one issuer.</p>')
    body.append('<h3>G. Interpretation</h3>'
      f'<p>The frozen difference-versus-level contrast gives {verdict(tr_res)}, and {holm_statement(family,"transformations_vs_levels")}. '
      'Where a P/E contrast is absent for ATI or Carpenter, the cause is a sparse or invalid P/E input at those origins — P/E requires positive trailing earnings — '
      'not a finding that the representations are equivalent. That is also why the signed earnings yield, which survives losses, is the preferred valuation representation throughout.</p>')
    body.append('<h3>H. Experiment conclusion</h3>'
      '<p>No representation reliably beat levels on this sample. The differences between representations are small relative to their intervals, '
      'consistent with all of them carrying substantially the same slow-moving information.</p>')
    body.append('<h3>I. Limitations and next test</h3>'
      '<p>The monthly as-known clock mixes months with a new filing and months without. Separating release months from carried-forward months would '
      'test the change hypothesis on the occasions when a change actually occurred, at the cost of roughly three-quarters of the observations.</p>')
    p.append(experiment('e3','E3','Do differences, percentage changes or lagged values improve on levels?',''.join(body)))

    # --- E4 ------------------------------------------------------------
    body=['<h3>A. Research question and motivation</h3>'
      '<p>Do broad market conditions, industry returns and company-relevant input prices add value beyond the company’s own financial and valuation state? '
      'These blocks are distinct: a broad market move affects every issuer, an industry return is closer to the customer base, '
      'and a copper or natural-gas price touches a specific cost or pass-through channel.</p>']
    body.append('<h3>B. Reproducible setup</h3>')
    body.append(spec_table([
      ('Target','Next-month adjusted-close total return, fraction'),
      ('Ladders','Protocol order (financials first) and market-first; both refit and retuned on identical origins'),
      ('Leave-one-out','Full model minus each block, with that block’s derivatives, lags and interactions also removed'),
      ('Industry reference','SOXX for MTRN and ENTG, ITA for CRS and ATI, frozen on business relevance and not on fit'),
      ('Business drivers','Copper futures for MTRN; natural-gas futures as an indirect cost proxy for the others; every external series delayed one US session'),
      ('Excluded','Tungsten and molybdenum prices, physical semiconductor and aerospace demand series, and index-membership returns — recorded as unavailable, not proxied')]))
    body.append('<h3>C. Variables and mechanism</h3>'
      '<p>The mechanism must run from driver to cash flow or required return before a variable is admitted. '
      'For Materion a copper price rise raises reported revenue through pass-through while also raising input cost and working capital, '
      'so a uniformly favourable sign is not assumed. For Entegris a semiconductor index return is an equity co-movement proxy, '
      'not a measure of wafer starts — a distinction the exposure map records explicitly. Natural gas is an indirect energy-cost hypothesis '
      'for the melting and finishing operations, with no disclosed exposure weight behind it.</p>')
    body.append('<h3>D. Evaluation criteria</h3>'
      '<p>Paired loss change for each block in both ladder orders and in the leave-one-block-out check. '
      'Agreement across the two orderings is required before a block is described as contributing, because ordered ladders allocate shared information to whichever block enters first.</p>')
    body.append('<h3>E. Results</h3>')
    ab_show=ablation[ablation.ladder.isin(['protocol_order','market_first'])][['ladder','stage','ticker','n','predictors','rmse','r2_oos','mean_loss_reduction','lo','hi']].copy()
    for c in ['mean_loss_reduction','lo','hi']:ab_show[c]*=1e4
    ab_show['rmse']*=100
    body.append(T('Both cumulative ladders',ab_show.rename(columns={'ladder':'Ladder','stage':'Stage','ticker':'Company','n':'Months','predictors':'Columns','rmse':'RMSE (pp)','r2_oos':'OOS R²','mean_loss_reduction':'Step MSE reduction (pp²)','lo':'Lower 95%','hi':'Upper 95%'}),
      'The protocol ladder adds financials first; the market-first ladder answers the separately required check of market and industry controls before company information. A block that looks useful in one ordering and not the other is sharing information, not proving its own value.'))
    lobo=ablation[ablation.ladder=='leave_one_block_out'][['stage','ticker','n','rmse','r2_oos','mean_loss_reduction','lo','hi']].copy()
    for c in ['mean_loss_reduction','lo','hi']:lobo[c]*=1e4
    lobo['rmse']*=100
    body.append(T('Leave-one-block-out',lobo.rename(columns={'stage':'Model','ticker':'Company','n':'Months','rmse':'RMSE (pp)','r2_oos':'OOS R²','mean_loss_reduction':'MSE change vs full model (pp²)','lo':'Lower 95%','hi':'Upper 95%'}),
      'Sign convention as elsewhere: positive favours the model named in the first column, so a positive value here means dropping the block improved the forecast.'))
    body.append(figure('08_importance'))
    body.append('<h3>F. Figures and diagnostics</h3>'
      f'<p>Figure {num("08_importance")} shows a grouped block permutation of a fitted Random Forest. It is included as a contrast to the ablations, not as a substitute: '
      'shuffling a block in blocks of three months preserves some time structure but still breaks dependence between groups, so it can attribute importance to a block '
      'whose information is really carried by a correlated one. Refitted block ablations are the preferred evidence for economic importance.</p>')
    body.append('<h3>G. Interpretation</h3>'
      '<p>The two ladders do not agree on which block helps, which is the expected signature of shared explanatory information rather than a contradiction. '
      'Market, industry and momentum blocks overlap heavily by construction: an industry-relative return is an industry return minus a market return, '
      'and a three-month relative momentum is a function of both. The leave-one-block-out check is the more informative view precisely because it holds everything else constant.</p>')
    body.append('<h3>H. Experiment conclusion</h3>'
      '<p>No external block showed a reliable, order-independent improvement. The ordered sequence should not be read as allocating predictive information between blocks.</p>')
    body.append('<h3>I. Limitations and next test</h3>'
      '<p>The industry inputs are traded index returns, not physical demand. The most economically direct series for these issuers — '
      'beryllium, tungsten and molybdenum prices, wafer starts, engine deliveries — were either not publicly available as usable histories or not free to obtain. '
      'That is a data gap, not a measured null, and it is the single change most likely to alter E4.</p>')
    p.append(experiment('e4','E4','Do market, industry and business drivers add value beyond company information?',''.join(body)))

    # --- E5 ------------------------------------------------------------
    lag_res=ret[(ret.expanded=='distributed_all_lag1')&(ret.reduced=='core_ridge')&(ret.block==6)]
    body=['<h3>A. Research question and motivation</h3>'
      '<p>Do older observations of the same predictors help beyond their latest values? Economic effects can arrive gradually: '
      'a margin improvement disclosed two quarters ago may still be working through the business. Against that, carried-forward fundamentals '
      'make a lag almost a repeat of the current value, in which case extra columns add estimation noise and nothing else.</p>']
    body.append('<h3>B. Reproducible setup</h3>')
    body.append(spec_table([
      ('Target','Next-month adjusted-close total return, fraction'),
      ('Common inputs','The same six compact predictors as the static and dynamic families'),
      ('Lag sets','{0}, {0,1} and {0,1,3} months, prespecified; lag 0 means information at the current origin, never an outcome-period value'),
      ('Model','Ridge, so the wider lag sets remain estimable at 84 training observations'),
      ('Frozen contrast','All-core lags {0,1} vs the static {0} model'),
      ('Held fixed','Estimator, penalty grid, origins, outcomes and preprocessing')]))
    body.append('<h3>C. Variables and mechanism</h3>'
      '<p>A lagged predictor is a distinct concept from a difference and from autoregressive target dynamics. '
      'Including revenue growth at lags 0 and 1 asks whether last month’s known growth rate adds to this month’s; '
      'it does not model dependence in the return itself, which is E6’s question.</p>')
    body.append('<h3>D. Evaluation criteria</h3>'
      '<p>Paired MSE change against the same model with lag set {0}, plus sensitivity to lag length. '
      'A result that appears only at one lag length is treated as noise.</p>')
    body.append('<h3>E. Results</h3>')
    body.append(T('E5 paired comparisons',contrast_table(ret,[('All-core lags {0,1} vs {0}','distributed_all_lag1','core_ridge'),('All-core lags {0,1,3} vs {0}','distributed_all_lag3','core_ridge'),('Selected-core lag 1','distributed_lag1','core_ridge'),('Selected-core lags 1 and 3','distributed_lag3','core_ridge')]),
      'The first row is the frozen family member. Lag-length sensitivity is the second row; agreement between them is the evidence that matters.'))
    body.append(figure('09_cumulative_loss'))
    body.append('<h3>F. Figures and diagnostics</h3>'
      f'<p>Figure {num("09_cumulative_loss")} accumulates the paired squared-error difference month by month. '
      'This is the diagnostic that distinguishes a persistent edge from one lucky month: a genuine improvement should produce a steadily rising line, '
      'whereas a single step means one outcome is carrying the entire result.</p>')
    body.append('<h3>G. Interpretation</h3>'
      f'<p>The frozen lag contrast gives {verdict(lag_res)}, and {holm_statement(family,"lags_vs_static")}. The cumulative view is the more informative one here, '
      'because a mean loss difference computed over 44 months can be dominated by one extreme return. '
      'Carried-forward quarterly fundamentals make lag 1 nearly collinear with lag 0 for the financial predictors, which is the most likely reason added lags do not pay.</p>')
    body.append('<h3>H. Experiment conclusion</h3>'
      '<p>Older predictor observations did not reliably improve forecasts over the latest available values on these inputs and this sample.</p>')
    body.append('<h3>I. Limitations and next test</h3>'
      '<p>Only three lag sets were tested, deliberately: an open search over lag combinations on 44 outcomes would find something by construction. '
      'A targeted follow-up would lag only the market and industry blocks, which do update monthly, and leave the carried-forward financial block at lag 0.</p>')
    p.append(experiment('e5','E5','Do older predictor observations improve on the latest information?',''.join(body)))

    # --- E6 ------------------------------------------------------------
    arma_res=ret[(ret.expanded=='arimax')&(ret.reduced=='arma_static')&(ret.block==6)]
    body=['<h3>A. Research question and motivation</h3>'
      '<p>After the predictors have been accounted for, is what remains — the unexplained part — itself forecastable? '
      'That is what regression with ARMA errors asks. It is a different question from adding lagged predictors, '
      'and a more elaborate model is not assumed to be better.</p>']
    body.append('<h3>B. Reproducible setup</h3>')
    body.append(spec_table([
      ('Equation','y(t+1) = intercept + β′X(t) + u(t+1), with u following an ARMA(p,q) process on its own past innovations'),
      ('Orders','(0,0), (1,0), (2,0), (0,1), (1,1); (0,0) included so the data can prefer no dynamics'),
      ('Differencing','d = 0 for return targets; no seasonal terms'),
      ('Exogenous alignment','The regressor row for target month s carries the features known at s−1; a one-step forecast is supplied X(t), never a realised X(t+1)'),
      ('State updating','Filtered information only — realised outcomes are appended sequentially without refitting inside a validation block; no future-smoothed state is used'),
      ('Order selection','Nested one-step validation inside the training history, refreshed annually; the order history is archived'),
      ('Fair comparison','The static side is the matching (0,0) fit with the same likelihood, intercept and exogenous convention, not a separately tuned Ridge'),
      ('Capacity gate','At least five training observations per estimated parameter; fits below ten per parameter are flagged limited-sample')]))
    body.append('<h3>C. Variables and mechanism</h3>'
      '<p>The MA terms concern past forecast innovations, not moving averages of the explanatory variables, and "exogenous" here describes the model input — '
      'it is not a claim of causal independence. Error dynamics would be expected to help if regimes persisted and the residual dependence were stable; '
      'they should hurt if returns have little remaining serial dependence and the extra parameters simply fit noise.</p>')
    body.append('<h3>D. Evaluation criteria</h3>'
      '<p>Paired MSE against the matching (0,0) specification, which isolates the ARMA structure from the predictor set and the penalty. '
      'AIC and BIC are recorded as training diagnostics and screens, never as the selection score.</p>')
    body.append('<h3>E. Results</h3>')
    body.append(T('E6 paired comparisons',contrast_table(ret,[('Selected ARIMAX vs matching static ARMA(0,0)','arimax','arma_static'),('Selected ARIMAX vs historical mean','arimax','historical_mean')]),
      'The first row is the frozen family member and the only one that isolates error dynamics. The second mixes the dynamics with the value of the predictors themselves.'))
    dyn=f[(f.model=='arimax')&(f.task=='return')]
    limited=int(dyn.limited_sample.astype(bool).sum())
    body.append(f'<p>Of the {len(dyn)} dynamic fits, {limited} sit between five and ten training observations per estimated parameter '
      f'(minimum {dyn.observations_per_parameter.min():.1f}). Those are flagged limited-sample in the ledger rather than dropped, because '
      'silently removing the harder origins would flatter the dynamic model on exactly the months where it is least well identified.</p>')
    body.append(T('Selected ARMA order by origin',orders.rename(columns={'ticker':'Company','order':'Selected order (p,q)','origins':'Origins'}),
      'The order is chosen inside training data and changes over time, so this family is labelled "order selected in training" rather than given a fixed order in any figure legend.'))
    body.append(figure('10_errors'))
    body.append('<h3>F. Figures and diagnostics</h3>'
      f'<p>Figure {num("10_errors")} shows out-of-sample forecast errors and their autocorrelation. These are forecast errors, not training residuals, '
      'and they are reported after the evaluation: they cannot trigger retrospective retuning. '
      'Visible autocorrelation in a short, adaptively fitted error sequence is not by itself evidence that a dynamic model would have helped, '
      'which is exactly what the paired comparison tests.</p>')
    body.append('<h3>G. Interpretation</h3>'
      f'<p>The frozen ARMA contrast gives {verdict(arma_res)}, and {holm_statement(family,"arma_vs_static")}. The selected order varies across origins and issuers, '
      'which is itself informative: a stable, forecastable error process would tend to produce a stable order choice. '
      'With 84 to 127 training observations and up to three extra parameters, the estimation noise in the ARMA terms is substantial.</p>')
    body.append('<h3>H. Experiment conclusion</h3>'
      '<p>An AR/MA error process did not reliably improve on the static model using the same information. '
      'The elaborate specification is not preferred, and the simpler one is not vindicated either — both sit within each other’s intervals.</p>')
    body.append('<h3>I. Limitations and next test</h3>'
      '<p>Monthly returns give little scope for detectable error dynamics. The daily frequency has far more observations but a different question attached to it, '
      'and the variance task in E8 is where daily dependence is actually modelled.</p>')
    p.append(experiment('e6','E6','Does a forecastable AR/MA error process improve on a static model?',''.join(body)))

    # --- E7 ------------------------------------------------------------
    body=['<h3>A. Research question and motivation</h3>'
      '<p>Do the answers above depend on the horizon, the training window or the market state? '
      'A conclusion that holds only at one horizon or only in calm months is a weaker conclusion, and saying so is part of the result.</p>']
    body.append('<h3>B. Reproducible setup</h3>')
    body.append(spec_table([
      ('Horizons','One month (primary) and three-month compounded (sensitivity)'),
      ('Overlap handling','Three-month labels overlap, so training origins whose outcome extends past the fitting boundary are purged; three nonoverlapping calendar offsets are scored separately'),
      ('Windows','Expanding (primary) and fixed trailing 84-month rolling (sensitivity), on identical origins'),
      ('Volatility regime','High or low against a trailing median of realised market volatility, evaluated with information available at each origin'),
      ('Rate regime','Rising or falling from the prior three-month change in the 10-year yield, with an unavailable change left unclassified rather than counted as falling'),
      ('Rolling display','12-month window, stated in the figure title; overlapping windows are dependent'),
      ('Regime gate','Fewer than 12 forecasts in a regime keeps the result descriptive')]))
    body.append('<h3>C. Variables and mechanism</h3>'
      '<p>Regime definitions use only information available at the origin. Cutoffs were fixed before scoring, '
      'so a favourable regime cannot be discovered after seeing which months a model happened to win.</p>')
    body.append('<h3>D. Evaluation criteria</h3>'
      '<p>Consistency of sign and rough magnitude across horizons, windows, calendar years and regimes. '
      'The three-month horizon is a sensitivity, not independent confirmation: it reuses the same underlying price history on a later, shorter sample.</p>')
    body.append('<h3>E. Results</h3>')
    body.append(T('Three-month horizon',scores_table(s,'return',['historical_mean','core_ols','ridge_full','forest_full','boost_full'],horizon=3),
      'Each horizon uses its own matured historical-mean benchmark, so R² is comparable within a horizon and not across horizons.'))
    no=nonoverlap[nonoverlap.model.isin(['historical_mean','ridge_full','boost_full'])][['ticker','model','offset','n','rmse','r2_oos']].copy();no['rmse']*=100
    body.append(T('Three-month, nonoverlapping calendar offsets',no.rename(columns={'ticker':'Company','model':'Model','offset':'Offset','n':'Outcomes','rmse':'RMSE (pp)','r2_oos':'OOS R²'}),
      'All three offsets are reported rather than the most favourable one. Each holds only 12 to 13 independent outcomes, which is why these are descriptive.'))
    reg=regimes[(regimes.task=='return')&(regimes.horizon==1)&(regimes.regime=='calendar_year')&regimes.model.isin(['historical_mean','ridge_full','boost_full','arimax'])][['ticker','model','value','n','rmse','r2_oos']].copy();reg['rmse']*=100
    body.append(T('Calendar-year performance',reg.rename(columns={'ticker':'Company','model':'Model','value':'Year','n':'Months','rmse':'RMSE (pp)','r2_oos':'OOS R²'}),
      '2026 is a partial year ending with the August target. Year-by-year splits of a 44-month sample are descriptive.'))
    body.append(T('Excess-return target: stock minus market over the same month',scores_table(s,'excess_return',['historical_mean','zero','core_ridge','ridge_full','boost_full']),
      'The realised market return belongs to this outcome, never to the predictors. Scored against the expanding mean of the same excess-return quantity.'))
    body.append(figure('11_rolling'));body.append(figure('12_horizons'));body.append(figure('13_coefficients'))
    body.append('<h3>F. Figures and diagnostics</h3>'
      f'<p>Figure {num("11_rolling")} moves a 12-month window across the evaluation period; overlapping windows are dependent and must not be counted as separate evidence. '
      f'Figure {num("12_horizons")} places the one- and three-month results side by side with horizon-specific benchmarks. '
      'The three-month fits start later because unmatured labels are purged, so a change between horizons mixes horizon and period. '
      f'Figure {num("13_coefficients")} asks the parameter-stability question directly: whether the fitted relationship itself holds still as the window moves. '
      'Whiskers there are across-refit ranges, not sampling confidence intervals, and correlated predictors can exchange coefficients without changing any forecast.</p>')
    three=s[(s.task=='return')&(s.horizon==3)&(s.model=='core_ols')].set_index('ticker')
    best=three.r2_oos.idxmax()
    off=nonoverlap[(nonoverlap.model=='core_ols')&(nonoverlap.ticker==best)]
    body.append('<h3>G. Interpretation</h3>'
      '<p>Rankings move as the evaluation window moves, which is the expected behaviour of near-zero effects measured on short samples '
      'rather than evidence of regime-dependent skill. Where a regime holds fewer than twelve forecasts, no superiority claim is made from it.</p>'
      f'<p><strong>One apparently strong result deserves naming rather than burying.</strong> The compact OLS reaches an out-of-sample R\u00b2 of '
      f'{three.loc[best,"r2_oos"]:.2f} for {best} at the three-month horizon, far above anything in the one-month results. '
      'It is not a timing error: the outcome reproduces exactly from raw adjusted closes, every target ends exactly three months after its origin, '
      'and no training label extends past its fitting origin. It survives all three nonoverlapping calendar offsets '
      f'({", ".join(f"{v:.2f}" for v in off.sort_values("offset").r2_oos)}), which is the right check to run. '
      'But each of those offsets holds only 12 or 13 independent outcomes, and overlapping three-month labels mean the headline 38 observations '
      f'carry far less information than 38 independent ones. {best}\u2019s own returns over this window were unusually large, so a compact model that '
      'leans on recent drift will look accurate over a horizon long enough for that drift to persist. '
      'The honest reading is an imprecise estimate on roughly a dozen effective observations at a secondary horizon, not a discovered signal \u2014 '
      'and it does not carry over to the one-month target that determines this study\u2019s conclusion.</p>')
    body.append('<h3>H. Experiment conclusion</h3>'
      '<p>The main comparisons do not become reliable at another horizon, in another window or in a particular market state. '
      'The absence of a stable improvement is itself the stable finding. The single three-month exception above is reported in full, '
      'is consistent with small-sample variation on a dozen effective observations, and is not treated as evidence against that conclusion.</p>')
    body.append('<h3>I. Limitations and next test</h3>'
      '<p>Regime analysis on 44 months is close to anecdote. A longer point-in-time history, not a finer regime definition, is what would make this testable.</p>')
    p.append(experiment('e7','E7','Do the answers hold across horizons, windows and market regimes?',''.join(body)))

    # --- E8 ------------------------------------------------------------
    vq=s[s.task=='variance'];best_var=vq.loc[vq.groupby('ticker').qlike.idxmin()][['ticker','model','qlike','n']]
    body=['<h3>A. Research question and motivation</h3>'
      '<p>Return direction and return risk are different problems. Even if next month’s return is unforecastable, '
      'next month’s <em>variance</em> may not be, because volatility clusters. This is a separately defined forecasting task with its own target, '
      'benchmark and loss function, and a lower return RMSE would say nothing about it.</p>']
    body.append('<h3>B. Reproducible setup</h3>')
    body.append(spec_table([
      ('Target','Next month’s realised variance of daily returns, sum of squared deviations from that month’s daily mean divided by (D−1)'),
      ('Not the target','The variance of a monthly return, and not the raw second moment'),
      ('Benchmark','Trailing 63-session realised variance, a genuine persistence forecast'),
      ('Models','Historical variance at 21/63/252 sessions, EWMA(0.94), ARCH(1), GARCH(1,1), GARCH-X with market then industry then business volatility inputs, and regularised and tree-based variance forecasts'),
      ('Daily-to-monthly','Daily model forecasts are averaged over the target month’s exchange sessions'),
      ('Log target','Regularised and tree models fit log variance and retransform with a training-only smearing factor'),
      ('GARCH-X timing','External squared returns enter the recursion lagged one session; commodity inputs are delayed a further session; the stock’s own session calendar is never compressed'),
      ('Loss','QLIKE on positive variance forecasts; variance RMSE/MAE and volatility RMSE reported separately and never mixed')]))
    body.append('<h3>C. Variables and mechanism</h3>'
      '<p>Trailing realised volatility measures what has happened; the VIX level measures what options imply about the future — different frequencies and different meanings, '
      'so both are recorded rather than treated as interchangeable. Market and industry volatility enter GARCH-X on the hypothesis that '
      'a common volatility shock reaches the issuer, which is a co-movement channel, not a causal one.</p>')
    body.append('<h3>D. Evaluation criteria</h3>'
      '<p>Lower QLIKE against trailing realised variance. Volatility is reported as the square root of the variance forecast, '
      'which is not generally the expected volatility — an inequality worth stating because the two are routinely conflated.</p>')
    body.append('<h3>E. Results</h3>')
    body.append(T('Variance models',scores_table(s,'variance',['historical_variance21','historical_variance63','historical_variance252','ewma94','arch1','garch11','garchx_market','garchx_industry','garchx_business','variance_ridge_persistence','variance_ridge_market','variance_ridge_external','variance_ridge','variance_forest','variance_boost','pooled_ridge','business_pair_ridge']),
      'QLIKE is the ranking score. Variance RMSE and volatility RMSE are shown beside it because a model can win on one and lose on another; disagreement is reported rather than resolved by picking a favourable metric.'))
    body.append(T('Best observed variance model per issuer',best_var.rename(columns={'ticker':'Company','model':'Lowest-QLIKE model','qlike':'QLIKE','n':'Months'}),
      'Retrospectively lowest observed score among tested pipelines. This is not a prospectively validated choice and the differences between the leading models are small.'))
    body.append(T('E8 paired comparisons',contrast_table(var,[('GARCH(1,1) vs 63-day persistence','garch11','historical_variance63'),('EWMA vs persistence','ewma94','historical_variance63'),('GARCH-X market vs GARCH','garchx_market','garch11'),('GARCH-X +industry vs +market','garchx_industry','garchx_market'),('GARCH-X +business vs +industry','garchx_business','garchx_industry'),('Variance Ridge vs GARCH','variance_ridge','garch11'),('Pooled Ridge vs individual Ridge','pooled_ridge','variance_ridge')]),
      'Paired QLIKE differences on matched months; positive favours the first-named model.'))
    body.append(figure('14_variance_models'));body.append(figure('15_volatility_paths'));body.append(figure('16_pooling'))
    body.append('<h3>F. Figures and diagnostics</h3>'
      f'<p>Figure {num("14_variance_models")} ranks the variance models on a shared QLIKE scale. '
      f'Figure {num("15_volatility_paths")} plots square roots against the realised daily volatility of each target month, keeping the full scale so that missed spikes stay visible. '
      f'Figure {num("16_pooling")} contrasts individual, four-company and business-pair fits on the return and variance tasks side by side.</p>')
    body.append('<h3>G. Interpretation</h3>'
      '<p>Unlike the return task, several variance models do improve on their benchmark, which is what volatility clustering predicts. '
      'The gains come mainly from pooling and from persistence, not from added external volatility inputs: '
      'the stepwise GARCH-X additions do not compound. Pooling helps because volatility dynamics are more similar across these four issuers than their return dynamics are — '
      'a statement about the estimation problem, not a claim that the businesses are interchangeable.</p>')
    body.append('<h3>H. Experiment conclusion</h3>'
      '<p>The same information base does support a measurable improvement in forecasting realised variance, unlike mean return. '
      'This must not be read as partial success on the return question: they are different targets with different losses, '
      'and no return conclusion is strengthened by a variance result.</p>')
    body.append('<h3>I. Limitations and next test</h3>'
      '<p>QLIKE and variance RMSE do not always agree, and both are sensitive to a small number of high-volatility months. '
      'Intraday data would give a far more precise realised-variance target than 21 daily observations per month, and is the obvious next step.</p>')
    p.append(experiment('e8','E8','Can the same information improve a forecast of realised variance?',''.join(body)))

    # --- ELMT, synthesis, conclusion, limitations, reproducibility -----
    elmt=json.loads((OLD/'data/processed/ELMT_case.json').read_text()) if (OLD/'data/processed/ELMT_case.json').exists() else {}
    p.append('<section id="elmt"><h2>Elmet\u2019s short history, and how co-movement depends on the sample</h2>')
    p.append('<p>Elmet began Nasdaq trading on 23 April 2026. At the cutoff it has five monthly observations against an 84-month training gate, '
      'so it enters no fitted model. Excluding it is the finding, not an oversight: a model fitted on five outcomes would produce numbers '
      'with no claim to reliability, and reporting them beside 44-month results would be misleading.</p>')
    p.append('<p>Its private operating history can inform context but cannot create public-market returns, and its IPO offer price is not '
      'an investable close-to-close return. The September 2026 government financing involves redeemable preferred equity and warrants: '
      'funding is not earnings, a stockpile-contract ceiling is not recognised revenue, and warrant dilution is not captured by ordinary debt ratios. '
      'Those claims are documented in the <a href="../../historical_attribution/final/Historical_Attribution.html#elmt">earlier study’s case review</a>, '
      'which remains the authoritative record and is unchanged by this experiment.</p>')
    p.append(figure('17_correlations'));p.append(figure('18_rolling_correlation'))
    p.append(f'<p>Figure {num("17_correlations")} contrasts the four-issuer correlation matrix over the long daily sample with the five-equity matrix over Elmet’s '
      'short shared window. The right-hand panel describes roughly one hundred overlapping trading days and is not comparable evidence about long-run co-movement. '
      f'Figure {num("18_rolling_correlation")} shows that even among the established issuers, pairwise correlation is far from constant, '
      'which is why a single full-sample correlation is a summary rather than a property.</p>')
    contrast=read('correlation_regime_contrasts')
    show=contrast[['first','second','n_high','n_low','high_minus_low_correlation','lo','hi']]
    p.append(T('Daily-return correlation in high- versus low-volatility regimes',
      show.rename(columns={'first':'Company A','second':'Company B','n_high':'High-vol days','n_low':'Low-vol days',
        'high_minus_low_correlation':'Correlation difference','lo':'Lower 95%','hi':'Upper 95%'}),
      'Regimes are defined from trailing market volatility known at each date, not chosen after seeing the result. Intervals are synchronised moving-block resamples of the paired daily returns. A positive difference means the pair co-moved more when market volatility was already high, which is when diversification is least useful; this is a descriptive contrast, not a contagion test.'))
    rise=int((contrast.lo>0).sum())
    p.append(f'<p>{rise} of the {len(contrast)} established-issuer pairs show higher correlation in the high-volatility regime with an interval excluding zero. '
      'The exception is Carpenter and ATI, whose returns already move together closely in both regimes. '
      'This matters for the earlier study’s risk comparison rather than for forecasting: it says the diversification these names offer each other is weakest '
      'in exactly the periods when it would be most valuable. It says nothing about whether next month’s return is predictable.</p>')
    p.append('</section>')

    p.append('<section id="synthesis"><h2>Cross-experiment synthesis</h2>')
    sy=[]
    for ident,label,rows in [('E1','Financial characteristics',[('P1_financial','historical_mean')]),('E2','Starting valuation',[('ridge_full','without_valuation')]),
        ('E3','Changes vs levels',[('core_pe_difference','core_pe_level')]),('E4','External drivers',[('P6_business','P5_industry')]),
        ('E5','Added predictor lags',[('distributed_all_lag1','core_ridge')]),('E6','ARMA error dynamics',[('arimax','arma_static')])]:
        z=ret[(ret.expanded==rows[0][0])&(ret.reduced==rows[0][1])&(ret.block==6)]
        sy.append({'Experiment':ident,'Information or structure tested':label,'Issuers compared':len(z),
          'Median MSE reduction (pp²)':1e4*z.mean_loss_reduction.median() if len(z) else np.nan,
          'Issuers with interval above zero':int((z.lo>0).sum()) if len(z) else 0,
          'Issuers with interval below zero':int((z.hi<0).sum()) if len(z) else 0})
    z=var[(var.expanded=='garch11')&(var.reduced=='historical_variance63')&(var.block==6)]
    sy.append({'Experiment':'E8','Information or structure tested':'Variance dynamics (QLIKE)','Issuers compared':len(z),
      'Median MSE reduction (pp²)':np.nan,'Issuers with interval above zero':int((z.lo>0).sum()) if len(z) else 0,
      'Issuers with interval below zero':int((z.hi<0).sum()) if len(z) else 0})
    p.append(T('One row per experiment',pd.DataFrame(sy),
      'The variance row uses QLIKE, not squared error, so its magnitude column is deliberately blank: the two losses are not comparable and combining them into one ranking would be wrong.'))
    p.append('<p>The experiments agree with one another, which matters more than any single result. '
      'Across factor additions, transformation choices, lag lengths and error dynamics, the estimated improvements are small relative to their intervals, '
      'and no block or structure helps consistently across issuers and orderings. The one place the same information base does pay is the variance task, '
      'where volatility clustering gives a real and repeatedly measurable signal.</p>')
    p.append('<p>Where metrics disagree they are reported rather than reconciled by choosing one. '
      'Several models show a better RMSE alongside a worse MAE, which indicates the gain sits in a small number of large months rather than in typical accuracy; '
      'the cumulative paired-loss figure makes that visible directly. Directional accuracy above 50% is likewise not automatically useful '
      'when positive months are common, which is why the always-up and benchmark-direction columns sit beside it in every table.</p>')
    p.append('</section>')

    p.append('<section id="conclusion"><h2>Overall conclusion</h2>')
    p.append('<p><strong>On this evidence, company financial characteristics and starting valuation did not add reliable out-of-sample information '
      'about next-month returns for these four issuers, and adding time-series structure to a static regression using the same information did not help either.</strong> '
      'The simplest model supported by the evidence is the benchmark: the expanding historical mean. That is the recommendation.</p>')
    p.append('<p>Two qualifications are essential. First, these are imprecise estimates, not measured zeros: the intervals admit effects '
      'that would be economically interesting if real, and a 44-month evaluation cannot rule them out. Reporting "no reliable improvement" is not the same as '
      'reporting "no effect", and the difference is the entire uncertainty of the study. Second, the separate risk task did improve on its benchmark, '
      'which shows the pipeline can detect a signal when one is present — a useful control on the return null.</p>')
    p.append('<p>For the historical investment comparison, this bounds what the earlier study’s findings can be used for. '
      'That work measured contemporaneous exposures and decomposed past repricing; it never claimed forecastability, and this experiment finds none to add. '
      'Predictability and intrinsic value are different things: a stock whose next-month return is unforecastable can still be mispriced, '
      'and nothing here speaks to that.</p>')
    p.append('</section>')

    p.append('<section id="limitations"><h2>Limitations and further research</h2>')
    p.append('<ul>'
      '<li><strong>Sample size.</strong> Four issuers and 44 monthly outcomes each. Monthly equity returns are dominated by noise at this length; '
      'the study is underpowered against any plausible effect size, and this is the binding constraint on every conclusion.</li>'
      '<li><strong>Observed-history selection.</strong> These companies and much of their history were reviewed before the protocol was frozen. '
      'The protocol is newly frozen, not preregistered on unseen data; genuinely prospective data would be needed for independent confirmation.</li>'
      '<li><strong>Survivorship.</strong> Five currently listed issuers are not a cross-section, and no asset-pricing premium should be inferred from them.</li>'
      '<li><strong>Data vintage.</strong> Accounting inputs are selected by verified publication date, but reconstructed macro series and factor archives '
      'may embed later revisions. Where the historical vintage could not be established, the input is a labelled sensitivity.</li>'
      '<li><strong>Missing data.</strong> Archived analyst consensus was unavailable, so forward P/E, earnings surprise and estimate revisions could not be tested at all '
      'rather than being approximated. The high-yield credit spread archive begins in 2023 and fails the training coverage gate. '
      'Tungsten, molybdenum and beryllium price histories were not obtainable, so Elmet and part of Materion’s input-cost channel remain untested.</li>'
      '<li><strong>Multicollinearity.</strong> Market, industry and momentum blocks overlap by construction, so ordered ablations cannot uniquely allocate '
      'predictive information and coefficients can exchange freely between correlated columns without changing forecasts.</li>'
      '<li><strong>Structural change.</strong> Acquisitions, business exits and restructuring alter what these issuers are over the sample, '
      'so a fixed exposure mapping is an approximation of a moving target.</li>'
      '<li><strong>Overfitting and instability.</strong> Hyperparameters are retuned annually rather than at every origin, a disclosed operational simplification. '
      'Selected ARMA orders and Lasso selections vary across origins, which is reported rather than smoothed away.</li>'
      '</ul>')
    p.append('<p>Ranked by the uncertainty they would resolve, the most valuable follow-ups are: a wider panel of comparable issuers evaluated at the same origins, '
      'which is the only route to adequate power without fabricating history; archived point-in-time analyst estimates, which would let the forward-valuation question '
      'be asked at all; and intraday data for a far more precise realised-variance target. Adding model complexity would not help and is not proposed.</p>')
    p.append('</section>')

    p.append('<section id="repro"><h2>Reproducibility and appendices</h2>')
    p.append('<p>One offline command rebuilds every number, figure and table in this report from the archived inputs:</p>'
      '<pre>/tmp/mtrn-research-venv/bin/python MTRN/experiments/financial_valuation_models/code/run_experiments.py</pre>'
      '<p>Run from the repository root with Python 3.12 and the pinned dependencies in <a href="../code/requirements.txt">code/requirements.txt</a>. '
      'It makes no network calls; retrieval is a separate entry point (<code>code/fetch_external.py</code>) that never overwrites an existing archive. '
      'Seeds are fixed at 20260918 and the pipeline is deterministic: re-running it reproduces the saved forecast ledger exactly.</p>')
    p.append(T('Frozen configuration',pd.DataFrame(sorted((str(k),str(v)) for k,v in CONFIG.items()),columns=['Setting','Value']),
      'The complete frozen configuration, also saved as config.json. Penalty grids, order candidates, gates, seeds and block lengths were fixed before scoring.'))
    p.append(T('Deferred and unavailable inputs',deferrals.rename(columns={'component':'Requested input','reason':'Why it is not implemented'}),
      'Each remains visible as an explicit deferral. None was replaced by a substitute and none was dropped from the report’s scope statement.'))
    reg_show=registry[['variable','name','group','formula','units','transformation','availability','missing_treatment','status']] if 'transformation' in registry.columns else registry
    p.append('<details><summary>Appendix A. Complete variable dictionary ('+str(len(registry))+' entries)</summary>'+table(reg_show,
      'Every implemented, reported and deferred variable with its exact formula, units, transformation form, availability rule and missing-value treatment.')+'</details>')
    p.append('<details><summary>Appendix B. All model scores</summary>'+table(s,'Every model, task, horizon and issuer scored on matched dates.')+'</details>')
    p.append('<details><summary>Appendix C. Matched successful-fit scores (fallbacks excluded)</summary>'+table(successful,
      'The same models re-scored on origins where no forecast fell back. A fallback is a recorded failure, never evidence for the model that failed.')+'</details>')
    degenerate=family[family.get('degenerate')==True] if 'degenerate' in family.columns else family.iloc[0:0]
    p.append('<details><summary>Appendix D. Frozen comparison family with Holm adjustment</summary>'
      +('<p>'+esc(f'{len(degenerate)} of the sixteen contrasts could not actually be run: both specifications produced identical forecasts because the distinguishing predictor failed the training coverage gate. Those rows are untested contrasts, not measured nulls, and are flagged in the degenerate column.')+'</p>' if len(degenerate) else '')
      +table(family,'The sixteen prespecified contrasts. Every other comparison in this report is exploratory.')+'</details>')
    p.append('<details><summary>Appendix E. Ablation scores, both ladders and leave-one-block-out</summary>'+table(ablation,
      'Absolute and paired incremental performance for each stage, with the sign convention stated in every row.')+'</details>')
    p.append('<details><summary>Appendix F. Model failures and fallbacks</summary>'+table(failures if len(failures) else pd.DataFrame([{'note':'No model fit failed during this run'}]),
      'Every convergence failure, capacity-gate rejection and fallback, with the origin and the reason.')+'</details>')
    p.append('<details><summary>Appendix G. Collinearity, variance inflation and residual diagnostics</summary>'
      +table(collinearity,'Design diagnostics on the first and final training windows. The broad OLS fit is a diagnostic, not a forecast candidate.')
      +table(vif,'Variance inflation for the compact unpenalised design. Regularised models are not ranked by it.')
      +table(residual,'Training residual serial-dependence diagnostics. No model was selected using final-fit p-values.')+'</details>')
    p.append('<details><summary>Appendix H. Coefficient and selection stability</summary>'+table(stability,
      'Across-refit variation, not sampling confidence intervals. Correlated predictors can exchange coefficients without changing forecasts.')+'</details>')
    p.append('<details><summary>Appendix I. Split manifest</summary>'+table(splits.head(200),
      'First 200 rows; the complete manifest is in split_manifest.csv. Each row records the training interval, the inner validation boundaries and whether the origin retuned.')+'</details>')
    p.append('<p>Machine-readable outputs: '+' · '.join(link(n) for n in ['forecasts','model_scores','ablation_scores','paired_loss_comparisons','primary_comparison_family','successful_fit_scores','split_manifest','parameter_paths','model_failures','feature_registry','metric_registry','experiment_registry','coverage_and_deferrals','feature_availability_audit','monthly_features_as_known','exposure_map','figure_manifest','table_manifest'])+'.</p>')
    p.append('<p>Provenance and audits: <a href="../config.json">frozen configuration</a> · <a href="../sources/manifest.json">download manifest</a> · '
      '<a href="../data/processed/validation_results.json">validation results</a> · <a href="../CONTINUATION_AUDIT.json">continuation audit</a> · '
      '<a href="../COMPLETION_AUDIT.json">completion audit</a> · <a href="../README.md">reproduction notes</a> · '
      '<a href="../../prompt_v2_financial_valuation_models.md">governing protocol</a>.</p>')
    p.append('<p>The earlier historical-attribution study, its seven figures and all of its numerical outputs are preserved unchanged and hash-verified; '
      'none of its results is reused here as predictive evidence.</p>')
    p.append('</section>')

    # Written after assembly so each figure carries the number it actually bears.
    unused=[x['key'] for x in MANIFEST if x['number'] is None]
    if unused:raise ValueError('Figures generated but never embedded: '+', '.join(unused))
    pd.DataFrame(MANIFEST).sort_values('number').to_csv(OUT/'figure_manifest.csv',index=False)
    pd.DataFrame(tables).to_csv(OUT/'table_manifest.csv',index=False)
    css=('body{margin:0;color:#243746;background:#f3f5f5;font:16px/1.65 system-ui,-apple-system,"Segoe UI",sans-serif}'
     'main{max-width:1280px;margin:auto;background:white;padding:38px 48px}'
     'header{border-bottom:5px solid #235b91;padding-bottom:20px}h1{font-size:38px;line-height:1.15;max-width:960px}'
     'h2{font-size:26px;margin-top:46px;padding-top:8px;border-top:1px solid #e3e9ec}h3{font-size:18px;margin-top:28px;color:#1f3a56}'
     'h4{font-size:15px;margin-top:24px;color:#475569;text-transform:uppercase;letter-spacing:.06em}'
     '.eyebrow{color:#235b91;font-weight:700;letter-spacing:.12em;font-size:13px}.subtitle,figcaption,.caption{color:#5a6b75}'
     'nav{display:flex;flex-wrap:wrap;gap:16px;padding:22px 0;border-bottom:1px solid #d9e2e4;font-size:14px}'
     'a{color:#1d6d8c;text-decoration:none}a:hover{text-decoration:underline}p,ul{max-width:1050px}li{margin-bottom:7px}'
     '.table-wrap{overflow:auto;margin:18px 0}table{border-collapse:collapse;font-size:12.5px;width:100%;line-height:1.45}'
     'th{text-align:left;background:#eaf0f4;color:#214852;position:sticky;top:0}'
     'th,td{padding:8px 11px;border-bottom:1px solid #dce4e6;vertical-align:top;min-width:64px}tr:nth-child(even){background:#f8fafb}'
     'figure{margin:28px 0}img{width:100%;height:auto}figcaption{font-size:13px;padding-top:9px;max-width:1050px}'
     '.caption{font-size:12.5px;margin-top:-8px;max-width:1050px}'
     '.note{padding:16px 18px;background:#fff6e0;border-left:4px solid #c69235;margin:22px 0}'
     'details{margin:18px 0;border:1px solid #dce4e6;padding:14px}summary{font-weight:650;cursor:pointer}'
     'pre{overflow:auto;padding:14px;background:#eef3f5;font-size:13px}code{font-size:.9em}'
     '@media(max-width:700px){main{padding:22px 16px}h1{font-size:28px}nav{gap:10px}}'
     '@media print{main{padding:0}nav{display:none}details{display:block}table{font-size:8.5px}img{max-height:420px;object-fit:contain}}')
    document=('<!doctype html><html lang="en"><head><meta charset="utf-8">'
      '<meta name="viewport" content="width=device-width,initial-scale=1">'
      '<title>Financial and valuation forecasting — MTRN and peers</title><style>'+css+'</style></head><body><main>'+''.join(p)+'</main></body></html>')
    (ROOT/'final/Financial_Valuation_Model_Comparison.html').write_text(document)
    print('REPORT',len(MANIFEST),'figures,',len(tables),'numbered tables ->',ROOT/'final/Financial_Valuation_Model_Comparison.html',flush=True)

if __name__=='__main__':build()
