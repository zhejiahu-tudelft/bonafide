"""Build the standalone research artifact from computed outputs only."""
import base64,html,json,os,tempfile
from settings import *
os.environ.setdefault('MPLCONFIGDIR',str(Path(tempfile.gettempdir())/'mtrn-attribution-matplotlib'))
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from market_analysis import load_prices

COLORS={'MTRN':'#087e8b','ENTG':'#c44e52','CRS':'#b88713','ATI':'#7562ad','ELMT':'#34495e'}
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','figure.facecolor':'white'})
def read(name):return pd.read_csv(OUT/(name+'.csv'))
def pct(x,n=2):return '—' if pd.isna(x) else f'{100*x:,.{n}f}%'
def num(x,n=2):return '—' if pd.isna(x) else f'{x:,.{n}f}'
def ci(x,lo,hi,percent=True):
    f=pct if percent else num
    return f'{f(x)} [{f(lo)}, {f(hi)}]'
def table(d):return '<div class="table-wrap">'+d.to_html(index=False,escape=True,border=0,na_rep='—',float_format=lambda x:f'{x:,.4f}')+'</div>'
def link(name,label=None):return f'<a href="../data/processed/{name}.csv">{html.escape(label or name)}</a>'
def figure(fig,name,caption):
    fig.tight_layout();p=ROOT/'figures'/f'{name}.png';fig.savefig(p,dpi=150,bbox_inches='tight');plt.close(fig)
    encoded=base64.b64encode(p.read_bytes()).decode()
    return f'<figure><img alt="{html.escape(caption)}" src="data:image/png;base64,{encoded}"><figcaption>{html.escape(caption)}</figcaption></figure>'

def coverage_table(moments,models,announcements,holding):
    rows=[]
    for panel,label in [('long','Long raw-return panel'),('recent','Recent raw-return panel'),('matched','Matched five-company panel')]:
        d=moments[(moments.panel==panel)&(moments.frequency=='daily')&(moments.basis=='total')].iloc[0]
        base=holding[holding.panel==panel].iloc[0].start_close
        rows.append([label,f'{d.start}–{d.end}',f'{d.n:,} daily returns',f'Common base close {base}'])
    for panel in ['long','recent']:
        d=models[models.panel==panel].iloc[0]
        rows.append([panel.title()+' factor models',f'{d.start}–{d.end}',f'{d.n:,} complete months','Fixed sample gates; see model exclusions'])
    for panel in ['long','matched']:
        d=moments[(moments.panel==panel)&(moments.frequency=='daily')&(moments.basis=='excess')].iloc[0]
        rows.append([panel.title()+' risk-free-adjusted daily moments',f'{d.start}–{d.end}',f'{d.n:,} daily returns','No unavailable RF observations extrapolated'])
    counts=announcements.groupby('ticker').size()
    complete=announcements[['earnings_change_scaled','operating_margin_change']].notna().all(axis=1).sum()
    quarters=pd.to_datetime(announcements.release_date).dt.to_period('Q').nunique()
    rows.append(['Quarterly earnings study',f'{announcements.release_date.min()}–{announcements.release_date.max()}',
                 '; '.join(f'{tk}: {n}' for tk,n in counts.items()),f'{complete} complete update pairs; {quarters} calendar quarters'])
    return pd.DataFrame(rows,columns=['Component','Dates','Observations','Treatment'])

def build():
    prices=load_prices();r=pd.read_csv(OUT/'daily_returns.csv',index_col=0,parse_dates=True)
    moments=read('moments');pairs=read('paired_comparisons');models=read('models');coefs=read('coefficients');bridges=read('accounting_bridges')
    snapshots=read('financial_snapshots');financial=snapshots[snapshots['asof']==CUTOFF].set_index('ticker');history=read('annual_operating_history')
    event=read('event_summary').set_index('ticker');cars=read('event_cars');pool=read('event_regression');holding=read('holding_returns')
    announcements=read('earnings_announcements')
    primary=models[(models.panel=='long')&(models.model=='M2')].set_index('ticker');alpha_family=read('primary_alpha_family').set_index('ticker')
    annual_mtrn=pd.read_csv(REPO/'MTRN/data/processed_data/financial_history.csv')
    monthlymom=moments.query('panel=="long" and frequency=="monthly" and basis=="excess"').set_index('ticker')
    matched=moments.query('panel=="matched" and frequency=="daily" and basis=="total"').set_index('ticker')
    p=[]
    p.append('<header><div class="eyebrow">MTRN · ENTG · CRS · ATI · ELMT</div><h1>Historical returns, operating change and uncertainty</h1><p class="subtitle">A retrospective first- and second-moment experiment · information cutoff: September 18, 2026</p></header>')
    p.append('<nav><a href="#findings">Findings</a><a href="#coverage">Coverage</a><a href="#financials">Operating performance</a><a href="#bridge">Repricing</a><a href="#moments">Return moments</a><a href="#factors">Common exposures</a><a href="#events">Announcements</a><a href="#elmt">Elmet</a><a href="#methods">Methods & reproducibility</a></nav>')
    p.append('<section id="findings"><h2>What this experiment establishes</h2>')
    p.append('<p><strong>The companies have materially different histories of operating performance, repricing and return variance. Their historical average returns are much harder to distinguish statistically.</strong> These are three separate comparisons. The accounting identity does not measure causal fundamental value, and a factor model’s unexplained component does not identify why investors traded.</p>')
    p.append(f'<p>MTRN’s long-sample monthly mean excess return is {pct(primary.loc["MTRN","mean_excess"])}. After market, size, value, momentum and two industry exposures, its estimated monthly alpha is {ci(primary.loc["MTRN","alpha"],primary.loc["MTRN","alpha_lo"],primary.loc["MTRN","alpha_hi"])}. The model explains {pct(primary.loc["MTRN","r2"],1)} of monthly variance, leaving {pct(primary.loc["MTRN","residual_share"],1)} unexplained. The interval permits a substantial range of average performance.</p>')
    p.append('<p>On matched long-sample daily excess returns, all three MTRN-minus-peer mean-difference intervals include zero. MTRN’s variance-ratio intervals lie below one against ENTG, CRS and ATI. After the monthly M2 exposures are removed and models are refitted in synchronized resamples, only the MTRN/ATI residual-variance ratio has an interval entirely below one. This is stronger evidence about historical dispersion than about a stable ranking of returns.</p>')
    p.append('<p>The 92 quarterly earnings announcements support event descriptions, but the pooled price-scaled earnings-change and operating-margin-change slopes both have wide intervals spanning zero. The simple financial updates do not provide a precise explanation of announcement returns. This does not show that financial information was irrelevant: prior expectations, guidance, capital allocation and other simultaneous disclosures are not fully observed.</p>')
    synthesis=[]
    for tk in TICKERS:
        if tk in CORE:
            f=financial.loc[tk];m=primary.loc[tk];ev=event.loc[tk];br=bridges[(bridges.ticker==tk)&(bridges.panel=='long')].iloc[0]
            bridge=f'EPS {num(br.eps_start)} → {num(br.eps_end)}; P/E {num(br.pe_start,1)} → {num(br.pe_end,1)}' if br.valid else 'Long bridge invalid: starting EPS negative'
            synthesis.append({'Company':tk,'Operating change / latest level':f'TTM sales ${num(f.revenue,0)}m; operating margin {pct(f.operating_margin,1)}; FCF ${num(f.fcf,1)}m',
              'Earnings / multiple bridge':bridge,'Mean excess / alpha, monthly':f'{pct(m.mean_excess)} / {ci(m.alpha,m.alpha_lo,m.alpha_hi)}',
              'Explained / residual variance; residual volatility':f'{pct(m.r2,1)} / {pct(m.residual_share,1)}; {pct(m.residual_volatility)} monthly',
              'Disclosure association':f'{int(ev.n)} events; mean CAR {ci(ev.mean_car,ev.mean_lo,ev.mean_hi)}','Confidence / limitations':'Model conditional; pointwise intervals; accounting/business changes; approximate rolling EPS'})
        else:synthesis.append({'Company':tk,'Operating change / latest level':'H1 sales +28.2%; GAAP operating loss $5.8m; IPO and financing discontinuities',
              'Earnings / multiple bridge':'Not meaningful across IPO/share reorganization','Mean excess / alpha, monthly':'No full monthly model; short daily panel below',
              'Explained / residual variance; residual volatility':'Common exploratory daily market-only model; 102 returns',
              'Disclosure association':'Sept14 observed return +32.80%; no qualifying pre-event estimation history','Confidence / limitations':'Short history; preferred/warrants; conditional financing; no headline CAGR'})
    p.append(table(pd.DataFrame(synthesis)));p.append('</section>')
    p.append('<section id="coverage"><h2>Coverage and information sets</h2>')
    coverage=coverage_table(moments,models,announcements,holding)
    coverage.to_csv(OUT/'report_coverage.csv',index=False)
    p.append(table(coverage))
    p.append('<p class="note">The French files contain observations through July 2026 and were retrieved on September 20. Exact equivalence to the version available September 18 could not be established. All factor regressions are therefore <strong>retrospective-vintage estimates</strong>, not a historical information-set backtest. They contain no post-cutoff economic observations. Raw-price comparisons are the main directly observed return results.</p>')
    p.append('<p>As-known financial snapshots use accession-specific SEC facts available by each endpoint. Date-only filings become usable on the next trading session. Original earnings exhibits supply announcement updates directly; later 10-Q numbers are not backdated. Separate annual/quarterly operating tables use the latest eligible comparable/recast figures at the cutoff. All companies report in USD. No studied issuer has a recorded stock split during the analysis window. Adjusted closes are a vendor total-return proxy; dividends are not added again.</p>')
    p.append(table(read('business_exposure')[['ticker','legal_name','exchange','cik','exposure','comparability']]))
    p.append('<p>SOXX represents semiconductor-cycle exposure; ITA represents aerospace/defense exposure. Historical ETF constituent weights were not recovered, so own-stock contamination is unquantified. These overlapping traded proxies describe co-movement rather than exogenous demand shocks. The archived <a href="https://www.ishares.com/us/products/239705/ishares-phlx-semiconductor-etf">SOXX</a> and <a href="https://www.ishares.com/us/products/239502/ishares-us-aerospace-defense-etf">ITA</a> issuer pages document their intended exposure.</p>')
    fig,axes=plt.subplots(1,2,figsize=(12,4.3))
    for ax,start,tks,title in [(axes[0],'2016-01-01',CORE,'Established firms: $100 at Dec 31, 2015'),(axes[1],'2026-04-24',TICKERS,'All five: $100 at Apr 23, 2026')]:
        d=r[tks].loc[start:].dropna();w=(1+d).cumprod()*100
        for tk in tks:ax.plot(w.index,w[tk],label=tk,color=COLORS[tk],lw=1.5)
        ax.set_title(title);ax.set_ylabel('Total-return wealth proxy ($)');ax.legend(fontsize=8);ax.grid(alpha=.15)
        if tks==CORE:ax.set_yscale('log')
    p.append(figure(fig,'return_paths','Compounded adjusted-close returns. Left axis is logarithmic. ELMT starts at its first public close; its $14 offer price is excluded.'))
    hd=holding.copy();hd['Total return']=hd.total_return.map(pct);hd['CAGR']=hd.cagr.map(pct);hd['Maximum drawdown']=hd.max_drawdown.map(pct)
    p.append(table(hd[['panel','ticker','start_close','end','n','Total return','CAGR','Maximum drawdown']]))
    p.append('</section><section id="financials"><h2>Disclosed operating performance</h2>')
    fd=[]
    for tk in CORE:
        f=financial.loc[tk];fd.append({'Company':tk,'TTM end':f.period_end,'Revenue $m':num(f.revenue,1),'GAAP op. margin':pct(f.operating_margin),
          'Operating EBITDA $m':num(f.operating_ebitda,1),'CFO $m':num(f.cfo,1),'Total capex $m':num(f.total_capex,1),'FCF $m':num(f.fcf,1),
          'Approx. trailing P/E':num(f.pe,1),'FCF / common cap':pct(f.fcf_yield),'Carrying net debt $m':num(f.net_debt,1)})
    p.append(table(pd.DataFrame(fd)))
    p.append('<p>Operating EBITDA is GAAP operating income plus cash-flow D&amp;A, including acquired-intangible amortization for ENTG. It is not company-adjusted EBITDA. FCF is CFO minus investment capex; MTRN includes separately disclosed mine development. Net debt uses carrying debt less cash, with company-specific debt tags reconciled to the statement. EV multiples and ROIC are deferred because lease, minority, pension and preferred claims and invested-capital definitions are not uniformly reconciled. Common capitalization uses filed actual outstanding shares, never weighted-average diluted shares.</p>')
    p.append('<p>MTRN illustrates why revenue growth alone is inadequate. Latest trailing gross sales are $2,098.3m, versus value-added sales of $1,087.9m. Its adjusted EBITDA/VA margin of approximately 21.8% has a different denominator and numerator from the GAAP operating margins above. The latest quarter shows value-added sales rising from $269.0m to $308.2m while gross sales rose from $431.7m to $613.9m. Metal pass-through amplifies the gross-sales comparison. Trailing FCF is $32.4m after $75.9m total capex, including $17.8m mine development. The 2024 impairment also depresses the earnings base used in some 2026 bridges. <a href="https://www.sec.gov/Archives/edgar/data/1104657/000110465726000044/mtrn-20260703.htm">MTRN Q2 filing</a>; <a href="https://www.sec.gov/Archives/edgar/data/1104657/000110465726000042/">Q2 earnings exhibit</a>.</p>')
    p.append('<p>CRS’s June fiscal year and surcharge treatment, ATI’s restructuring and changing aerospace mix, and ENTG’s acquisition financing and amortization prevent a clean ranking by one ratio. ELMT’s H1 operating and cash figures are shown separately below, because an IPO-period half year is not interchangeable with these trailing years. The business map is qualitative: current business weights are not imposed on 2016 exposures.</p>')
    fig,ax=plt.subplots(figsize=(10,4))
    for tk in CORE:
        d=history[history.ticker==tk].dropna(subset=['operating_margin']).sort_values('period_end');ax.plot(pd.to_datetime(d.period_end),d.operating_margin*100,marker='o',ms=3,label=tk,color=COLORS[tk])
    ax.axhline(0,color='gray',lw=.7);ax.set_ylabel('GAAP operating margin (%)');ax.set_title('Annual operating margins: latest eligible recast history');ax.legend(ncol=4);ax.grid(alpha=.15)
    p.append(figure(fig,'operating_margins','Fiscal year-end dates are preserved. Disposals, acquisitions and impairments affect comparability; these recast operating figures are not historical information-set inputs.'))
    p.append('<p>Real-economy context remains evidence, rather than an extra fitted factor search. The archived September 4 SIA release reports a sharp rise in July semiconductor sales; this provides demand-cycle context for ENTG and MTRN but cannot identify their stock-return response. Company releases document aerospace demand and procurement exposure. No monthly release has been forward-filled into hundreds of independent daily observations. <a href="https://www.semiconductors.org/global-semiconductor-sales-increase-6-4-month-to-month-in-july/">SIA release</a>. Comprehensive production, metal-price and procurement series were not assembled.</p>')
    p.append('<p>Data: '+link('financial_snapshots','As-known snapshots')+' · '+link('financial_fact_audit','Accession and availability audit')+' · '+link('annual_operating_history','Recast annual history')+' · '+link('quarterly_operating_history','Directly disclosed quarters')+'. Discrete quarterly cash flows require compatible same-filing YTD components; otherwise the cell remains missing.</p>')
    p.append('</section><section id="bridge"><h2>Earnings and multiple repricing</h2>')
    p.append('<p><code>log(P₁/P₀) = log(EPS₁/EPS₀) + log[(P/E)₁/(P/E)₀]</code>. The identity reconciles exactly for the stated earnings measure. Rolling diluted EPS is annual disclosed EPS plus current YTD less prior YTD. That common rolling approximation is not exactly additive when weighted shares change. The bridge is therefore an exact <em>price identity using an approximate rolling EPS measure</em>, not a claim that earnings caused the corresponding share of appreciation. Values are log points, not additive simple-return percentages.</p>')
    bt=[]
    for b in bridges.itertuples():
        bt.append({'Panel':b.panel,'Company':b.ticker,'Price start → end':f'{num(b.price_start)} → {num(b.price_end)}',
          'Rolling EPS start → end':f'{num(b.eps_start)} → {num(b.eps_end)}','P/E start → end':f'{num(b.pe_start,1)} → {num(b.pe_end,1)}',
          'EPS log points':num(b.log_eps*100,1),'Multiple log points':num(b.log_multiple*100,1),'Price return':pct(b.price_return),
          'TR less price return, pp':num(100*b.dividend_reinvestment_gap),'Status':'Valid proxy identity' if b.valid else 'Not meaningful'})
    p.append(table(pd.DataFrame(bt)))
    p.append('<p>From end-2015, MTRN’s price increase combines approximately 85.7 earnings log points and 133.8 multiple log points. From end-2020, its bridge instead has 127.4 earnings log points and only 9.9 multiple log points. The 2026 YTD EPS base still contains the loss-making fourth quarter of 2024, so rolling that quarter out mechanically produces strong EPS recovery and multiple compression. CRS and ATI start the recent window with negative EPS; forcing logarithmic earnings attribution would be misleading. ELMT’s reorganization/share basis prevents a meaningful comparable bridge.</p>')
    fig,ax=plt.subplots(figsize=(10,3.8));d=bridges[(bridges.panel=='matched')&bridges.valid]
    y=np.arange(len(d));ax.barh(y-.17,d.log_eps*100,height=.32,label='Earnings log points',color='#087e8b');ax.barh(y+.17,d.log_multiple*100,height=.32,label='Multiple log points',color='#c69235')
    ax.scatter(d.log_price*100,y,marker='D',color='#253746',label='Total price log points');ax.set_yticks(y,d.ticker);ax.axvline(0,color='gray',lw=.7);ax.set_xlabel('Log points (100 × log ratio)');ax.set_title('Same dates, different earnings and repricing paths: Apr23–Sep18');ax.legend(fontsize=8)
    p.append(figure(fig,'accounting_bridge','Contributions add in log space. The chart is an endpoint accounting identity, not an independent explanatory regression or an intrinsic-value estimate.'))
    p.append('</section><section id="moments"><h2>First and second return moments</h2>')
    p.append('<p>Native-frequency arithmetic means and sample central variances are primary. Intervals use synchronized moving-block resampling with 2,000 replications, seed 20260918: ten trading days, five weeks or three months. Variance below is expressed in squared percentage points; volatility is its square root. Mean intervals are not forecasts of future expected returns. All intervals are pointwise, approximate and conditional on these selected histories.</p>')
    def moment_table(d):
        rows=[]
        for a in d.itertuples():rows.append({'Company':a.ticker,'Panel':a.panel,'Frequency / basis':a.frequency+' / '+a.basis,'N':a.n,'Last date':a.end,
          'Mean [95% CI]':ci(a.mean,a.mean_lo,a.mean_hi),'Mean SE':pct(a.mean_se),
          'Variance, pp² [95% CI]':ci(a.variance*10000,a.var_lo*10000,a.var_hi*10000,False),
          'Volatility [95% CI]':ci(a.volatility,a.vol_lo,a.vol_hi),'Lag-1 correlation':num(a.lag1_autocorrelation,3)})
        return table(pd.DataFrame(rows))
    p.append('<h3>Long panel, daily excess returns</h3>'+moment_table(moments.query('panel=="long" and frequency=="daily" and basis=="excess"')))
    p.append('<h3>Five-company panel, daily total returns</h3>'+moment_table(moments.query('panel=="matched" and frequency=="daily" and basis=="total"')))
    p.append('<details><summary>All daily, weekly and monthly moment estimates</summary>'+moment_table(moments)+'</details>')
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for ax,metric,lo,hi,title in [(axes[0],'mean','mean_lo','mean_hi','Daily mean return (%)'),(axes[1],'volatility','vol_lo','vol_hi','Daily volatility (%)')]:
        for i,tk in enumerate(TICKERS):
            a=matched.loc[tk];ax.errorbar(a[metric]*100,i,xerr=np.array([[a[metric]-a[lo]],[a[hi]-a[metric]]])*100,fmt='o',color=COLORS[tk],capsize=3)
        ax.set_yticks(range(5),TICKERS);ax.set_title(title);ax.axvline(0,color='gray',lw=.7);ax.grid(axis='x',alpha=.15)
    p.append(figure(fig,'matched_moment_intervals','Matched Apr24–Sep18 daily total returns, 102 observations. Short-history block intervals are wide; none of these mean intervals excludes zero. No annualized ELMT mean or CAGR is reported.'))
    def pair_table(d):
        rows=[]
        for a in d.itertuples():rows.append({'MTRN vs':a.peer,'Panel / frequency':a.panel+' / '+a.frequency,'Basis':a.basis,'N':a.n,
          'Mean difference [95% CI]':ci(a.mean_difference,a.mean_diff_lo,a.mean_diff_hi),
          'Variance ratio [95% CI]':ci(a.variance_ratio,a.variance_ratio_lo,a.variance_ratio_hi,False),
          'Volatility ratio [95% CI]':ci(a.volatility_ratio,a.vol_ratio_lo,a.vol_ratio_hi,False)})
        return table(pd.DataFrame(rows))
    p.append('<h3>Paired MTRN comparisons</h3>'+pair_table(pairs.query('frequency=="daily" and basis=="excess" and panel=="long"')))
    p.append('<p>The risk-free series cancels algebraically from synchronized mean differences, but its coverage ends in July. A variance ratio of 0.60 is not 40% lower volatility: its volatility ratio is √0.60 ≈ 0.775. Paired intervals preserve cross-company dependence and do not compare overlapping separate-company error bars.</p>')
    p.append('<details><summary>All paired raw / excess comparisons</summary>'+pair_table(pairs)+'</details>')
    p.append('<p>Annualized arithmetic means in the CSV are 252×daily means or 52×weekly means, not CAGR. The √frequency volatility conversion assumes negligible serial covariance and is secondary. Native weekly returns are compounded directly from daily returns, so the weekly tables provide a dependence-sensitive comparison without treating annualization as exact. Weekly bins exclude the first partial week; full-month factor returns omit September. Largest one/five moves remain in the primary sample; exclusion diagnostics are available in '+link('influence_checks')+' and '+link('announcement_influence')+'.</p>')
    p.append('</section><section id="factors"><h2>Common exposures and remaining variation</h2>')
    p.append('<p>M0 uses market excess returns. M1 adds size, value and momentum. M2 adds semiconductor and aerospace/defense ETF excess returns. FF5 plus momentum is a separate alternative. Real-yield and credit-spread downloads failed, so M3 is not estimated. Nominal Treasury yield changes are a labeled sensitivity; their units are percentage points. M1+nominal and M2+nominal permit a limited industry/nominal block-order check, without substituting nominal yields for missing real yields and credit spreads.</p>')
    mt=[]
    for a in models.itertuples():mt.append({'Panel':a.panel,'Company':a.ticker,'Model':a.model,'N':a.n,'Monthly excess mean':pct(a.mean_excess),
      'Alpha [HAC 95% CI]':ci(a.alpha,a.alpha_lo,a.alpha_hi),'Adjusted R²':num(a.adjusted_r2,3),
      'Total / fitted / residual variance, pp²':f'{num(a.total_variance*10000)} / {num(a.fitted_variance*10000)} / {num(a.residual_variance*10000)}',
      'Residual vol. [block CI]':ci(a.residual_volatility,a.residual_vol_boot_lo,a.residual_vol_boot_hi),'Scaled condition':num(a.condition_scaled,2)})
    modeltable=pd.DataFrame(mt);p.append(table(modeltable.query('Panel=="long" and Model=="M2"')))
    p.append('<details><summary>All eligible model specifications</summary>'+table(modeltable)+'</details>')
    p.append('<p>The four-firm primary long M2 alpha family uses Benjamini–Hochberg adjustment of the HAC p-values. ATI’s pointwise alpha interval excludes zero, but its adjusted q-value is '+num(alpha_family.loc['ATI','alpha_bh_q'],3)+'. None of the four alpha tests passes 5% after this adjustment. Other robustness intervals are estimation diagnostics, not a search for the smallest p-value. Long M2 has 127 months; the recent panel has 67 and fails the seven-parameter M2 gate of 70. Recent M1 is eligible. '+link('model_exclusions','Model exclusions')+'.</p>')
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for i,tk in enumerate(CORE):
        m=primary.loc[tk];axes[0].barh(i,m.r2*100,color=COLORS[tk]);axes[0].barh(i,m.residual_share*100,left=m.r2*100,color='#dfe5e8');axes[1].errorbar(m.alpha*100,i,xerr=np.array([[m.alpha-m.alpha_lo],[m.alpha_hi-m.alpha]])*100,fmt='o',color=COLORS[tk],capsize=3)
    for ax in axes:ax.set_yticks(range(4),CORE)
    axes[0].set_xlim(0,100);axes[0].set_title('Monthly variance: explained (color) / residual (gray)');axes[0].set_xlabel('Share of total variance (%)')
    axes[1].axvline(0,color='gray',lw=.7);axes[1].set_title('Monthly alpha with HAC 95% interval');axes[1].set_xlabel('Percentage points per month')
    p.append(figure(fig,'factor_decomposition','Long M2, Jan2016–Jul2026. Fitted and residual variances use N−1 and reconcile exactly to total variance, including factor covariances.'))
    contrib=read('refitted_contributions').query('frequency=="monthly" and panel=="long"');ct=[]
    for a in contrib.itertuples():
        ct.append({'Company':a.ticker,'Factor':a.factor,'Beta [refit block CI]':ci(a.beta,a.beta_boot_lo,a.beta_boot_hi,False),
                   'Monthly mean contribution [block CI]':ci(a.contribution,a.contribution_lo,a.contribution_hi)})
    p.append('<details><summary>Primary factor loadings and mean contributions, with uncertainty</summary>'+table(pd.DataFrame(ct))+'</details>')
    p.append('<p><code>mean(excess return) = alpha + Σ(beta × mean factor)</code>. Alpha is separate from the fitted residual mean, which is zero by OLS construction. The variance identity is <code>Var(y) = Var(fitted) + Var(residual)</code> with the same observations and N−1 denominator. The residual error estimate SSE/(N−p) is stored separately. Neither identity is a decomposition of compounded shareholder wealth. R² is not the percentage of value justified by financial performance.</p>')
    ref=read('refitted_model_moments');pc=read('paired_model_comparisons');pcrows=[]
    for a in pc.itertuples():pcrows.append({'Panel / frequency':a.panel+' / '+a.frequency,'MTRN vs':a.peer,'Basis':a.basis,
      'Alpha/intercept difference [block CI]':ci(a.intercept_difference,a.intercept_diff_lo,a.intercept_diff_hi),
      'Residual variance ratio [block CI]':ci(a.residual_variance_ratio,a.variance_ratio_lo,a.variance_ratio_hi,False)})
    p.append('<details><summary>Paired model comparisons, refitting inside every resample</summary>'+table(pd.DataFrame(pcrows))+'</details>')
    p.append('<p>Daily diagnostics estimate their own market-plus-industry coefficients; monthly betas are not reused. The five-company short panel uses the same market-only daily model for every firm. These daily models use raw returns because full-cutoff RF data are unavailable; their intercepts are not excess-return alphas. All daily-model intervals refit coefficients inside synchronized ten-day blocks. '+link('refitted_model_moments','Daily and monthly residual moments with refit intervals')+' · '+link('refitted_contributions','All refitted loadings/contributions')+'.</p>')
    p.append('<details><summary>Correlation and model stability diagnostics</summary><h3>Daily raw-return correlations: long panel</h3>'+table(pd.read_csv(OUT/'correlation_long.csv').rename(columns={'Unnamed: 0':'Company'}))+'<h3>Daily residual correlations: long panel</h3>'+table(pd.read_csv(OUT/'residual_correlation_long.csv').rename(columns={'Unnamed: 0':'Company'}))+'<p>'+link('factor_correlations')+' · '+link('daily_model_stability','Market-only and first/second-half diagnostics')+' · '+link('hac_sensitivity','HAC lag 0 / 6 sensitivity')+'. Covariance matrices and all block-length sensitivity files accompany the report. Correlated factors share explanatory variation; block-entry increments do not identify unique causes.</p></details>')
    p.append('</section><section id="events"><h2>Quarterly financial announcements</h2>')
    p.append('<p>The census contains all 23 quarterly results announcements for each established firm from January 2021 through the cutoff. Presentations duplicating the same results, metric recasts and unrelated preliminary updates are excluded with a log. GAAP EPS and operating-income/sales pairs are extracted from the original quarterly statement table, including losses and prior-year comparatives. EPS changes are scaled by the close before the release date. They are earnings changes, not analyst-consensus surprises.</p>')
    er=[]
    for tk,a in event.iterrows():er.append({'Company':tk,'Events':int(a.n),'Mean CAR [quarter-block CI]':ci(a.mean_car,a.mean_lo,a.mean_hi),
      'Event-to-event variance, pp² [CI]':ci(a.car_variance*10000,a.var_lo*10000,a.var_hi*10000,False)})
    p.append(table(pd.DataFrame(er)))
    p.append('<p>CAR is the arithmetic sum of abnormal daily returns over [−1,+1] sessions. Each market model is estimated strictly on [−252,−21], with 232 usable sessions here and a minimum of 160. Date-only announcements use the next session; an explicit release timestamp, when present, determines the session. The alternative same-date mapping and [0,+1]/[−1,+5] windows are retained. SEC API acceptance timezone suffixes are not assumed to be a verified release time. Timing uncertainty and concurrent guidance/strategic news limit interpretation.</p>')
    slopes=pool[pool.term.isin(['earnings_change_scaled','operating_margin_change'])];p.append(table(slopes[['term','estimate','lo','hi','n','calendar_quarters','valid_bootstrap']]))
    p.append('<p>The pooled model has four company intercepts and two common slopes. Two consecutive calendar-quarter blocks are resampled jointly across firms. A one-percentage-point price-scaled EPS change means multiplying the reported slope and interval by 0.01 to obtain a decimal CAR effect; equivalently the numerical slope is the CAR percentage-point effect. Both slope intervals span zero, including economically different effects. Common slopes are an assumption, not a structural relation. There are 23 calendar quarters, not 92 independent macro environments.</p>')
    primarycars=cars[(cars.window=='primary')&(cars.mapping=='conservative')&(cars.benchmark=='market')]
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for tk in CORE:
        d=primarycars[primarycars.ticker==tk]
        axes[0].scatter(d.earnings_change_scaled*100,d.car*100,label=tk,color=COLORS[tk],alpha=.75,s=25)
        axes[1].scatter(d.operating_margin_change*100,d.car*100,label=tk,color=COLORS[tk],alpha=.75,s=25)
    for ax in axes:ax.axhline(0,color='gray',lw=.7);ax.axvline(0,color='gray',lw=.7);ax.set_ylabel('Three-session CAR (%)');ax.legend(fontsize=8)
    axes[0].set_xlabel('YoY quarterly GAAP EPS change / pre-release price (%)');axes[1].set_xlabel('YoY operating-margin change (percentage points)')
    axes[0].set_title('All 92 announcements: earnings updates');axes[1].set_title('All 92 announcements: margin updates')
    p.append(figure(fig,'announcement_scatter','No announcements or large losses are removed to improve fit. The common-slope bootstrap intervals span zero; these scatterplots do not identify causation.'))
    sensitivity=read('event_sensitivity');p.append('<details><summary>Event windows, timing and industry-benchmark sensitivity</summary>'+table(sensitivity)+'</details>')
    p.append('<p>MTRN’s mean primary CAR is positive with a pointwise interval just above zero; the same-date mapping raises the point estimate from 4.08% to 4.61%. This is exploratory evidence from 23 events, with large event-to-event dispersion and multiple comparisons. It does not show that a particular earnings metric explains those gains. '+link('earnings_announcements','Full announcement register')+' · '+link('event_cars','All event estimates')+' · '+link('event_exclusions','Excluded duplicate/non-quarterly filings')+'.</p>')
    p.append('<h3>Separate strategic-disclosure register</h3>'+table(read('strategic_events')[['ticker','date','event','overlap','date_kind']]))
    p.append('<p>This is a selected, source-established register, not a complete strategic-event census or a sample selected by return direction. In particular, an acquisition update reported on an earnings date cannot be separated from the earnings and guidance using that event window alone.</p>')
    p.append('</section><section id="elmt"><h2>ELMT: short history and changing common-shareholder claims</h2>')
    p.append('<p>ELMT began Nasdaq trading April 23, 2026. Its first close was $17.91, versus the $14 IPO offer price; offer-to-first-close appreciation of 27.93% is separate from the close-to-close return series. The Apr23–Sep18 public-close return is 28.31%, based on 102 returns. Daily mean return is '+ci(matched.loc['ELMT','mean'],matched.loc['ELMT','mean_lo'],matched.loc['ELMT','mean_hi'])+'; volatility is '+ci(matched.loc['ELMT','volatility'],matched.loc['ELMT','vol_lo'],matched.loc['ELMT','vol_hi'])+'. This sample is too short for stable expected-return or long-run risk claims. <a href="https://investors.theelmetgroup.com/news-events/press-releases/detail/157/the-elmet-group-co-announces-closing-of-upsized-initial-public-offering-and-full-exercise-of-underwriters-option-to-purchase-additional-shares">IPO closing announcement</a>.</p>')
    p.append('<p>The H1 filing reports $122.4m revenue versus $95.5m, a $5.8m operating loss, $10.7m stock-based compensation and $7.6m operating cash outflow. Investment capex is $3.1m <em>net of government grants</em>, making the $10.7m cash-flow deficit after capex unlike an unfunded gross-investment measure. Q2 cash was $66.1m, debt carrying value approximately $10.5m and common equity $187.5m. Those balance-sheet figures predate the September financing. <a href="https://investors.theelmetgroup.com/sec-filings">Original Q2 filing, August 13</a>; archived values and definitions: <a href="../data/processed/ELMT_case.json">ELMT case data</a>.</p>')
    p.append('<p>The September 14 government transaction provides an initial $200m redeemable preferred investment and up to $250m of conditional additional financing. Preferred dividends accrue at 5.5% in kind. Warrants cover 7,567,341 shares: 5,675,506 penny warrants and 1,891,835 warrants at $15.92. The preferred liquidation claim partly reduces on penny-warrant exercise, so full preferred value plus full warrant dilution cannot simply be added as independent claims. The stockpile contract has a $2bn ceiling and a $150m funded commitment. Neither is recognized revenue merely because the agreement was announced. <a href="https://investors.theelmetgroup.com/sec-filings/content/0001213900-26-099734/ea0304682-8k_elmet.htm">Financing 8-K</a>; <a href="https://investors.theelmetgroup.com/news-events/press-releases/detail/168/department-of-war-makes-landmark-450-million-committed-investment-in-the-elmet-group-to-secure-americas-tungsten-supply-chain">company announcement</a>.</p>')
    el=read('ELMT_event_returns');evtable=el.copy()
    for col in ['elmt_return','spy_return','ita_return','relative_spy','relative_ita']:evtable[col]=evtable[col].map(pct)
    p.append(table(evtable));p.append('<p>The announcement-day return is observed as +32.80%, not presumed from the financing headline. Relative return is the difference between two compounded holding-period returns, not a formal CAR. The prescribed 160-session estimation history is unavailable. The Sep16 policy announcement overlaps the through-cutoff window. No event-study standard error is fabricated.</p>')
    fig,ax=plt.subplots(figsize=(10,3.8));p_el=prices['ELMT'];ax.plot(p_el.index,p_el.close,color=COLORS['ELMT']);ax.axvline(pd.Timestamp('2026-09-14'),color='#c69235',ls='--');ax.set_title('ELMT observed public closes');ax.set_ylabel('USD per common share');ax.annotate('Sept14 preferred / warrant financing',xy=(pd.Timestamp('2026-09-14'),21.5),xytext=(pd.Timestamp('2026-06-10'),26),arrowprops={'arrowstyle':'->','color':'#c69235'},fontsize=9);ax.grid(alpha=.15)
    p.append(figure(fig,'elmt_case','Actual public closes only. Financing changes funding capacity and common-shareholder claims; the observed move does not isolate one mechanism.'))
    p.append('</section><section id="methods"><h2>Limitations, validation and reproduction</h2>')
    p.append('<p>The selected current issuers are not a representative cross-section of firms. Structural changes, imperfect disclosure timing, short samples and historical data revisions limit inference. Bootstrap intervals assume that resampled local blocks remain informative; they do not remove structural breaks. Full-sample factor fits are descriptive. No forecast, price target, trading backtest or investor-motive attribution is produced.</p>')
    deferrals=json.loads((OUT/'deferrals.json').read_text());p.append(table(pd.DataFrame(deferrals)))
    p.append('<p>Finite checks cover long/recent/matched windows; FF5+momentum; nominal-rate and market-only alternatives; HAC 0/3/6 lags; daily block lengths 5/10/20 and monthly 2/3/6; daily versus directly aggregated weekly moments; first/second-half beta diagnostics; largest-move and announcement-window exclusions; and alternative event windows, timing and industry models. No specification is discarded because it is insignificant.</p>')
    p.append('<p>Validation checks source preservation, filing availability, mining capex, loss signs and prior-year columns, model gates, cutoff/window bounds, exact mean/variance/price identities, secondary ELMT prices and report links. Independent tests cover dependent resampling, covariance accounting, later restatements, stale-tag rejection and event-estimation exclusion. See <a href="../data/processed/validation_results.json">validation results</a>, '+link('input_hashes','input hashes')+', <a href="../sources/manifest.json">download manifest</a>, <a href="../data_dictionary.md">data dictionary</a>, <a href="../config.json">frozen configuration</a> and <a href="../README.md">reproduction notes</a>.</p>')
    p.append('<pre>python MTRN/experiments/historical_attribution/code/run_analysis.py</pre><p>Run from the repository root using Python 3.12 and the pinned dependencies in <code>code/requirements.txt</code>. This rebuild reads cached inputs and makes no network calls. Retrieval is separate. The original MTRN investment report and protocol are preserved.</p>')
    p.append('<p>Method/source references: <a href="https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html">French factor definitions and return-construction changes</a> (2025 FIZ-to-CIZ change; saved July2026 vintage), <a href="https://www.sec.gov/search-filings/edgar-application-programming-interfaces">SEC EDGAR data</a>, <a href="https://fred.stlouisfed.org/series/DFII10">10-year real-yield definition</a>, <a href="https://fred.stlouisfed.org/series/BAMLH0A0HYM2">high-yield spread definition</a>, and <a href="https://www.bu.edu/econ/files/2011/01/MacKinlay-1996-Event-Studies-in-Economics-and-Finance.pdf">event-study methodology</a>. Proxy/source archives and original accession URLs accompany the numerical audit tables.</p></section>')
    css='''body{margin:0;color:#243746;background:#f3f5f5;font:16px/1.6 system-ui,sans-serif}main{max-width:1280px;margin:auto;background:white;padding:38px 48px}header{border-bottom:5px solid #087e8b;padding-bottom:20px}h1{font-size:38px;line-height:1.15;max-width:950px}h2{font-size:25px;margin-top:42px}h3{font-size:19px}.eyebrow{color:#087e8b;font-weight:700;letter-spacing:.12em}.subtitle,figcaption{color:#5a6b75}nav{display:flex;flex-wrap:wrap;gap:18px;padding:22px 0;border-bottom:1px solid #d9e2e4}a{color:#007682;text-decoration:none}a:hover{text-decoration:underline}p{max-width:1050px}.table-wrap{overflow:auto;margin:20px 0}table{border-collapse:collapse;font-size:13px;width:100%;line-height:1.45}th{text-align:left;background:#e9f2f3;color:#214852;position:sticky;top:0}th,td{padding:10px 12px;border-bottom:1px solid #dce4e6;vertical-align:top;min-width:70px}tr:nth-child(even){background:#f8fafb}figure{margin:26px 0}img{width:100%;height:auto}figcaption{font-size:13px;padding-top:8px}.note{padding:18px;background:#fff4db;border-left:4px solid #c69235}details{margin:20px 0;border:1px solid #dce4e6;padding:14px}summary{font-weight:650;cursor:pointer}pre{overflow:auto;padding:16px;background:#ecf2f4}code{font-size:.9em}@media(max-width:700px){main{padding:22px 18px}h1{font-size:29px}}@media print{main{padding:0}nav{display:none}details{display:block}table{font-size:9px}section{break-inside:auto}img{max-height:420px;object-fit:contain}}'''
    document='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Historical Attribution — MTRN and peers</title><style>'+css+'</style></head><body><main>'+''.join(p)+'</main></body></html>'
    (ROOT/'final/Historical_Attribution.html').write_text(document)
    (OUT/'synthesis.csv').write_text(pd.DataFrame(synthesis).to_csv(index=False))
    print('Standalone report written:',ROOT/'final/Historical_Attribution.html')

if __name__=='__main__':build()
