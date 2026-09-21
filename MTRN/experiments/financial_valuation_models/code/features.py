"""As-known monthly characteristics and independently defined future targets."""
import json, warnings
import numpy as np
import pandas as pd
from settings import *
from common.code.point_in_time import PointInTimeFacts

FLOW = {
 'revenue':['RevenueFromContractWithCustomerExcludingAssessedTax','SalesRevenueNet','SalesRevenueGoodsNet'],
 'operating_income':['OperatingIncomeLoss'], 'net_income':['NetIncomeLoss'],
 'common_income':['NetIncomeLossAvailableToCommonStockholdersBasic','NetIncomeLoss'],
 'gross_profit':['GrossProfit'], 'cfo':['NetCashProvidedByUsedInOperatingActivities'],
 'capex':['PaymentsToAcquirePropertyPlantAndEquipment','PaymentsToAcquireOtherPropertyPlantAndEquipment','PaymentsToAcquireProductiveAssets'],
 'da':['DepreciationDepletionAndAmortization','DepreciationDepletionAndAmortizationPropertyPlantAndEquipment','DepreciationAndAmortization'],
 # Gross reported interest expense only. MTRN's InterestIncomeExpenseNet is a net,
 # sign-reversed concept and InterestAndDebtExpense is absent, so neither is a valid
 # fallback; coverage stays sparse for MTRN and ATI rather than mixing definitions.
 'interest':['InterestExpenseNonoperating','InterestExpense','InterestExpenseDebt'],
 'dividends':['PaymentsOfDividendsCommonStock','PaymentsOfDividends','PaymentsOfOrdinaryDividends'],
}
# Parent-only common equity is preferred. The consolidated tag is an issuer-specific
# fallback, permitted only where the issuer's own earlier filings show an immaterial
# noncontrolling interest at a period end reporting both tags.
EQUITY_PARENT='StockholdersEquity'
EQUITY_TOTAL='StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'
NCI_TOLERANCE=.01
STOCK={
 'assets':['Assets'], 'equity':['StockholdersEquity'], 'total_equity':['StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'],
 'cash':['CashAndCashEquivalentsAtCarryingValue'], 'current_assets':['AssetsCurrent'],
 'current_liabilities':['LiabilitiesCurrent'], 'inventory':['InventoryNet'],
 'debt_noncurrent':['LongTermDebtNoncurrent','LongTermDebt'],
 'debt_current':['LongTermDebtCurrent','DebtCurrent','LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths'],
}
META={}
def register(name,group,formula,units='ratio',reason='',frequency='quarterly filings sampled monthly',status='candidate'):
    META[name]=dict(variable=name,name=name.replace('_',' ').title(),group=group,formula=formula,units=units,
        frequency=frequency,availability='next US session after date-only filing; market data by origin',
        rationale=reason or 'Tests incremental conditional information; no causal sign imposed.',status=status)

def divide(a,b,positive=True):
    return a/b if np.isfinite(a) and np.isfinite(b) and (b>1e-10 if positive else abs(b)>1e-10) else np.nan

def trailing_percentile(series,window=60,minimum=36):
    """Share of the preceding window's valid values below the current one."""
    values=series.to_numpy(float);out=np.full(len(values),np.nan)
    for i,current in enumerate(values):
        if not np.isfinite(current):continue
        past=values[max(0,i-window):i];past=past[np.isfinite(past)]
        if len(past)>=minimum:out[i]=float(np.mean(past<current))
    return pd.Series(out,index=series.index)

def same(ends,*keys):
    """The period end shared by every named flow, or None when the clocks differ."""
    found={ends.get(k) for k in keys}
    return found.pop() if len(found)==1 and None not in found else None

def equity_at(sel,asof,end):
    """Common book equity with a materiality-gated consolidated-tag fallback."""
    parent=sel.select(EQUITY_PARENT,asof,end=end,label='equity')
    if parent:return parent['val'],'parent-only StockholdersEquity'
    total=sel.select(EQUITY_TOTAL,asof,end=end,label='equity')
    if not total:return np.nan,'unavailable'
    # Latest earlier period end, known by asof, that reported both conventions.
    pairs={}
    for e in sel.entries(EQUITY_PARENT)+sel.entries(EQUITY_TOTAL):
        if e['available']<=asof and e['end']<=end:pairs.setdefault(e['end'],{})[e['tag']]=e['val']
    both=[(k,v) for k,v in sorted(pairs.items()) if EQUITY_PARENT in v and EQUITY_TOTAL in v and v[EQUITY_PARENT]]
    if not both:return np.nan,'consolidated tag only; no earlier period reports both conventions'
    k,v=both[-1];share=abs(v[EQUITY_TOTAL]-v[EQUITY_PARENT])/abs(v[EQUITY_PARENT])
    if share>NCI_TOLERANCE:
        return np.nan,f'consolidated tag only; noncontrolling interest {share:.1%} at {k} exceeds tolerance'
    return total['val'],f'consolidated tag; noncontrolling interest {share:.2%} at {k} within tolerance'

def balances(sel,asof,end,cache):
    """Balance-sheet items reported at one specific period end."""
    if end in cache:return cache[end]
    out={k:np.nan for k in STOCK}
    out['debt']=np.nan;out['equity_basis']='unavailable'
    if end:
        for key,tags in STOCK.items():
            out[key]=sel.value(tags,asof,end=end,label=key)/1e6
        value,basis=equity_at(sel,asof,end)
        out['equity']=value/1e6 if np.isfinite(value) else np.nan;out['equity_basis']=basis
        if sel.ticker=='ATI':
            out['debt']=sel.value(['DebtAndCapitalLeaseObligations','LongTermDebtAndCapitalLeaseObligations'],asof,end=end,label='debt')/1e6
        else:out['debt']=out['debt_noncurrent']+out['debt_current']
    cache[end]=out
    return out

def average_stock(sel,asof,end,key,current,cache):
    """Average of the end balance and the latest comparable balance a year earlier."""
    if not end or not np.isfinite(current):return np.nan
    tags=[EQUITY_PARENT,EQUITY_TOTAL] if key=='equity' else STOCK[key]
    eligible=[x for x in sel.entries(tags) if x['available']<=asof and x['days']==0
              and abs((pd.Timestamp(end)-pd.Timestamp(x['end'])).days-365)<=15]
    if key=='equity':
        basis=cache.get(end,{}).get('equity_basis','')
        want=EQUITY_TOTAL if basis.startswith('consolidated') else EQUITY_PARENT
        eligible=[x for x in eligible if x['tag']==want]
    prior=max(eligible,key=lambda x:(-x['priority'],x['filed'])) if eligible else None
    if not prior:return np.nan
    sel._record(prior,asof,'beginning_'+key)
    return (current+prior['val']/1e6)/2

def financial_snapshot(sel,asof,close):
    # Each disclosed flow keeps its own as-known trailing period. Requiring every
    # line item to share the revenue clock silently voided whole issuers whenever
    # one tag lagged; the shared-period rule now applies only where a ratio
    # actually combines two flows.
    row={};ends={};cache={};tags_used={}
    for key,tags in FLOW.items():
        mark=len(sel.audit)
        v,end=sel.ttm(tags,asof,label=key);row[key]=v/1e6;ends[key]=end
        tags_used[key]=sel.audit[mark]['tag'] if len(sel.audit)>mark else 'unavailable'
    if sel.ticker=='ENTG':
        parts=[sel.ttm(tag,asof,label='da_component') for tag in ['Depreciation','AmortizationOfIntangibleAssets']]
        shared={e for _,e in parts}
        row['da']=sum(v/1e6 for v,_ in parts) if len(shared)==1 and None not in shared else np.nan
        ends['da']=shared.pop() if len(shared)==1 else None
    end=ends['revenue'];row['financial_period_end']=end
    for key in FLOW:row[key+'_period_end']=ends[key]
    stock=balances(sel,asof,end,cache)
    for key in list(STOCK)+['debt']:row[key]=stock[key]
    row['equity_basis']=stock['equity_basis']
    row['interest_basis']=tags_used['interest'] if np.isfinite(row['interest']) else 'unavailable'
    mine=0.;mine_basis='no separately reported mine development'
    if sel.ticker=='MTRN':
        v,e=sel.ttm('PaymentsToAcquireMiningAssets',asof,label='mine_capex');mine=v/1e6
        mine_basis=('trailing mine development aligned to equipment capex' if e and e==ends['capex']
                    else f'latest annual mine-development disclosure ends {e}; not aligned to equipment capex {ends["capex"]}' if e
                    else 'no mine-development disclosure available at this date')
        if e!=ends['capex']:mine=np.nan
    row['mine_capex']=mine;row['mine_capex_basis']=mine_basis
    row['total_capex']=row['capex']+mine;ends['total_capex']=ends['capex'] if np.isfinite(row['total_capex']) else None
    row['fcf']=row['cfo']-row['total_capex'] if same(ends,'cfo','total_capex') else np.nan
    ends['fcf']=same(ends,'cfo','total_capex')
    # Equipment-capex free cash flow: the modelled representation, available on the
    # ordinary quarterly clock. Mine-inclusive FCF stays as an MTRN sensitivity.
    row['fcf_equipment']=row['cfo']-row['capex'] if same(ends,'cfo','capex') else np.nan
    ends['fcf_equipment']=same(ends,'cfo','capex')
    row['ebitda']=row['operating_income']+row['da'] if same(ends,'operating_income','da') else np.nan
    ends['ebitda']=same(ends,'operating_income','da')
    shares=sel.select('EntityCommonStockSharesOutstanding',asof,unit='shares',namespace='dei',label='actual_shares')
    row['shares']=shares['val']/1e6 if shares else np.nan
    row['market_cap']=row['shares']*close
    # Quarter comparison selected from the information set at the forecast date.
    for metric,tags,unit in [('revenue',FLOW['revenue'],'USD'),('eps',['EarningsPerShareDiluted'],'USD/shares')]:
        cur=sel.select(tags,asof,min_days=60,max_days=110,unit=unit,label=metric+'_quarter')
        prev=[] if cur is None else [x for x in sel.entries(tags,unit) if x['available']<=asof and 60<=x['days']<=110 and abs((pd.Timestamp(cur['end'])-pd.Timestamp(x['end'])).days-365)<=10 and abs(x['days']-cur['days'])<=10]
        old=max(prev,key=lambda x:(-x['priority'],x['filed'])) if prev else None
        if old:sel._record(old,asof,metric+'_prior_quarter')
        row[metric+'_growth']=divide(cur['val'],old['val'])-1 if cur and old and cur['val']>0 else np.nan
        if metric=='eps':
            # A loss or a move through zero makes percentage growth meaningless; the
            # price-scaled per-share change and a transition flag keep the information.
            row['eps_change_price']=(cur['val']-old['val'])/close if cur and old and close>0 else np.nan
            row['loss_transition']=float(min(cur['val'],old['val'])<=0) if cur and old else np.nan
    # Scale each flow by the balance sheet reported at that flow's own period end.
    for name,flow,stockkey in [('roa','net_income','assets'),('roe','common_income','equity')]:
        b=balances(sel,asof,ends[flow],cache)
        row[name]=divide(row[flow],average_stock(sel,asof,ends[flow],stockkey,b[stockkey],cache))
    for name,flow in [('cfo_assets','cfo'),('fcf_assets','fcf'),('fcf_equipment_assets','fcf_equipment'),('capex_assets','total_capex')]:
        row[name]=divide(row[flow],balances(sel,asof,ends[flow],cache)['assets'])
    for name,num,den in [('gross_margin','gross_profit','revenue'),('operating_margin','operating_income','revenue'),('net_margin','common_income','revenue'),('ebitda_margin','ebitda','revenue'),('interest_coverage','operating_income','interest'),('payout','dividends','common_income')]:
        row[name]=divide(row[num],row[den]) if same(ends,num,den) else np.nan
    for name,num,den in [('cash_assets','cash','assets'),('debt_assets','debt','assets'),('debt_equity','debt','equity'),('current_ratio','current_assets','current_liabilities')]:
        row[name]=divide(row[num],row[den])
    # Valuation divides a flow by the market's own contemporaneous price; it needs no
    # agreement with an unrelated line item's reporting clock.
    for name,num in [('earnings_yield','common_income'),('sales_yield','revenue'),('fcf_yield','fcf'),('fcf_equipment_yield','fcf_equipment'),('dividend_yield','dividends')]:
        row[name]=divide(row[num],row['market_cap'])
    row['book_yield']=divide(row['equity'],row['market_cap'])
    for name,den in [('pe','common_income'),('pb','equity'),('ps','revenue')]:row[name]=divide(row['market_cap'],row[den])
    row['quick_ratio']=divide(row['current_assets']-row['inventory'],row['current_liabilities'])
    # Explicit limited-claims sensitivity. Never presented as fully reconciled EV/ROIC.
    total_equity=row['total_equity'] if np.isfinite(row['total_equity']) else row['equity']
    nci=max(total_equity-row['equity'],0) if np.isfinite(total_equity) and np.isfinite(row['equity']) else 0
    row['ev_proxy']=row['market_cap']+row['debt']-row['cash']+nci
    row['ev_ebitda_proxy']=divide(row['ev_proxy'],row['ebitda']);row['ev_sales_proxy']=divide(row['ev_proxy'],row['revenue'])
    row['roic_proxy']=divide(.75*row['operating_income'],total_equity+row['debt']-row['cash'])
    row['claims_note']='Debt carrying value; NCI from equity difference where reported, otherwise assumed zero; preferred/pension/lease/warrant claims not fully reconciled. EV/ROIC proxy sensitivity only.'
    row['financial_age_days']=(pd.Timestamp(asof)-pd.Timestamp(end)).days if end else np.nan
    row['earnings_age_days']=(pd.Timestamp(asof)-pd.Timestamp(ends['common_income'])).days if ends['common_income'] else np.nan
    return row

SEGMENTS={
 'MTRN':[('Performance Materials: beryllium, precious and non-ferrous alloys','2013-12-31','semiconductor production and equipment demand','SOXX total return','index return, fraction','Customer capital spending and materials consumption drive volume','revenue','ambiguous: demand up, input cost up','Partial metal pass-through under customer contracts','same-session index close','traded proxy; not physical chip output','industry','implemented',''),
      ('Performance Materials: copper beryllium and precious metals','2013-12-31','copper and precious-metal input prices','HG=F copper futures settlement','USD/lb, monthly change','Metal cost is largely passed through, but changes working capital and reported revenue','both revenue and cost','ambiguous','Pass-through contracts; hedging disclosed qualitatively','one US session delay applied','futures series carries roll and construction effects','business','implemented',''),
      ('Electronic Materials and Precision Optics','2013-12-31','aerospace and defense activity','ITA total return','index return, fraction','Defence and aerospace programme spending supports specialty demand','revenue','ambiguous','Long programme cycles blunt short-horizon transmission','same-session index close','traded proxy; not procurement data','industry','redundant-with-tested-representation','Semiconductor reference retained as the primary MTRN industry proxy'),
      ('Beryllium mining and Utah operations','2021-01-01','beryllium ore supply and demand','beryllium price series','USD/unit','Input scarcity affects cost and pricing power','both revenue and cost','ambiguous','n/a','n/a','no accessible historical series established','business','unavailable','No liquid public beryllium price history; no series invented')],
 'ENTG':[('Materials Solutions and Microcontamination Control','2013-12-31','semiconductor production and wafer-fab equipment demand','SOXX total return','index return, fraction','Wafer starts and fab capex drive consumable and filtration volume','revenue','ambiguous','Consumable mix is less cyclical than equipment','same-session index close','traded proxy; not wafer-start data','industry','implemented',''),
      ('Advanced Materials Handling','2013-12-31','energy and manufacturing input costs','NG=F natural gas futures settlement','USD/MMBtu, monthly change','Process energy and resin feedstock costs affect gross margin','cost','ambiguous','No quantified hedge disclosure used','one US session delay applied','indirect cost hypothesis, no disclosed weight','business','implemented','Economic hypothesis only; not a disclosed exposure weight'),
      ('CMC Materials acquisition (2022) and subsequent disposals','2022-07-06','acquisition and disposal accounting','segment revenue weights','fraction','Mix and intangible amortisation shift the comparable history','both revenue and cost','ambiguous','n/a','filing date','disclosed qualitatively only','financial','incomparable','Current segment weights must not be projected backward')],
 'CRS':[('Specialty Alloys Operations','2013-12-31','aerospace engine demand and deliveries','ITA total return','index return, fraction','Engine build rates drive alloy volume and mix','revenue','ambiguous','Long-term agreements smooth transmission','same-session index close','traded proxy; not delivery counts','industry','implemented',''),
      ('Specialty Alloys Operations: raw material surcharges','2013-12-31','nickel, cobalt and titanium input prices','no accessible historical alloy input index','USD/lb','Surcharge mechanisms recover input cost with a lag','both revenue and cost','ambiguous','Surcharge recovery lag is disclosed qualitatively','n/a','no comparable free series established','business','unavailable','Surcharge-inclusive and surcharge-excluded sales are not separable from XBRL alone'),
      ('Performance Engineered Products','2013-12-31','energy and industrial activity','NG=F natural gas futures settlement','USD/MMBtu, monthly change','Melting and forging energy intensity affects cost','cost','ambiguous','No quantified hedge disclosure used','one US session delay applied','indirect cost hypothesis','business','implemented','')],
 'ATI':[('High Performance Materials & Components','2013-12-31','aerospace and defense demand','ITA total return','index return, fraction','Airframe and engine programmes drive titanium and nickel volume','revenue','ambiguous','Long-term agreements and mix changes','same-session index close','traded proxy; not procurement data','industry','implemented',''),
      ('Advanced Alloys & Solutions','2013-12-31','industrial activity and energy cost','NG=F natural gas futures settlement','USD/MMBtu, monthly change','Melt and finishing energy intensity affects cost','cost','ambiguous','No quantified hedge disclosure used','one US session delay applied','indirect cost hypothesis','business','implemented',''),
      ('Standard stainless exits and restructuring','2020-01-01','business exits and impairment accounting','segment revenue weights','fraction','Historical exposure is time-dependent, so one fixed mapping misstates early years','both revenue and cost','ambiguous','n/a','filing date','disclosed qualitatively only','financial','incomparable','Exposure changes over the sample; no backward projection of current weights')],
 'ELMT':[('Tungsten and molybdenum products','2026-04-23','tungsten and molybdenum prices and supply','no accessible historical series','USD/unit','Input scarcity and defence stockpiling affect price and volume','both revenue and cost','ambiguous','Government contracts and grants alter economics','n/a','thin and partly proprietary pricing data','business','unavailable','No comparable accessible history; ELMT is excluded from formal models'),
      ('Defense and semiconductor end markets','2026-04-23','defense procurement and semiconductor demand','ITA and SOXX total returns','index return, fraction','Programme funding and chip demand drive volume','revenue','ambiguous','Contract ceilings are not recognised revenue','same-session index close','traded proxies only','industry','sample-gated','Five public months; descriptive case study only')]}

def exposure_rows(ticker,industry,driver):
    """Economic mapping recorded before any statistical selection."""
    base=pd.read_csv(OLD/'data/processed/business_exposure.csv').set_index('ticker')
    columns=['business_segment','exposure_start','candidate_driver','exact_series','unit_currency','transmission_channel','revenue_or_cost_exposure','possible_sign','pass_through_hedging','release_lag','vintage_quality','feature_block','inclusion_status','omission_reason']
    rows=[]
    for values in SEGMENTS[ticker]:
        row=dict(zip(columns,values))
        rows.append(dict(issuer=ticker,**row,exposure_end=CUTOFF,
            evidence_date=CUTOFF,source=str(base.loc[ticker,'source_url']),
            modelled_industry_reference=industry,modelled_driver_series=driver if ticker!='ELMT' else 'none',
            comparability=str(base.loc[ticker,'comparability']),
            weights='Qualitative classification; no present-day segment weight backfilled into history'))
    return rows

def build():
    initialize(); warnings.filterwarnings('ignore',category=RuntimeWarning)
    allpx={t:prices(t) for t in TICKERS+['SPY','SOXX','ITA','XLB','IWM','TNX','IRX'] if price_path(t).exists()}
    for t in ['^VIX','HG=F','GC=F','SI=F','CL=F','NG=F','EURUSD=X','DX-Y.NYB']:
        if price_path(t).exists():allpx[t]=prices(t)
    sessions=allpx['SPY'].index
    returns=pd.concat({t:p.adj_close.pct_change(fill_method=None) for t,p in allpx.items()},axis=1).sort_index()
    returns.to_csv(OUT/'daily_returns.csv',index_label='date')
    monthly=(1+returns).resample('ME').prod(min_count=1)-1
    variance=returns.resample('ME').var(ddof=1)
    rows=[];audits=[];exposure=[]
    for tk in TICKERS:
        sel=PointInTimeFacts(fact_path(tk),sessions,tk)
        if tk=='MTRN':
            manual=json.loads((OLD/'data/processed/manual_mine_disclosures.json').read_text())
            units=sel.data['facts']['us-gaap'].setdefault('PaymentsToAcquireMiningAssets',{'units':{'USD':[]}})['units']['USD']
            units.extend(manual)
        px=allpx[tk]; r=returns[tk].dropna();industry='SOXX' if tk in ['MTRN','ENTG'] else 'ITA'
        driver='HG=F' if tk=='MTRN' else 'NG=F'
        exposure.extend(exposure_rows(tk,industry,driver))
        for label in pd.date_range('2013-12-31',LAST_MONTH,freq='ME'):
            avail=px.loc[:label]
            if avail.empty:continue
            date=avail.index[-1]
            if tk=='ELMT' and date<pd.Timestamp('2026-04-23'):continue
            row=dict(ticker=tk,date=str(label.date()),origin=str(date.date()),**financial_snapshot(sel,str(date.date()),float(avail.close.iloc[-1])))
            hist=r.loc[:date];m=returns.SPY.loc[hist.index].dropna();h=hist.reindex(m.index)
            row['monthly_return']=monthly.at[label,tk] if label in monthly.index else np.nan
            row['realized_variance']=variance.at[label,tk] if label in variance.index else np.nan
            row['market_return']=monthly.at[label,'SPY'];row['market_vol']=np.sqrt(variance.at[label,'SPY'])
            row['industry_return']=monthly.at[label,industry];row['industry_relative']=row['industry_return']-row['market_return']
            row['industry_vol']=np.sqrt(variance.at[label,industry]);row['sector_return']=monthly.at[label,'XLB']
            row['semis_return']=monthly.at[label,'SOXX'];row['defense_return']=monthly.at[label,'ITA']
            row['smallcap_return']=monthly.at[label,'IWM']
            for n in [1,3,6,12]:
                mr=monthly[tk].loc[:label].tail(n);sr=monthly.SPY.loc[:label].tail(n)
                row[f'momentum_{n}']=(1+mr).prod()-1 if len(mr)==n and mr.notna().all() else np.nan
                if n==3:row['relative_momentum']=row['momentum_3']-((1+sr).prod()-1)
            row['industry_momentum_relative']=row['momentum_3']-((1+monthly[industry].loc[:label].tail(3)).prod()-1)
            for n in [21,63,252]:row[f'vol_{n}']=hist.tail(n).std() if len(hist)>=n else np.nan
            tail=hist.tail(252);mt=m.reindex(tail.index)
            row['beta_252']=tail.cov(mt)/mt.var() if len(tail)>=252 and mt.var()>0 else np.nan
            row['idio_vol']=np.sqrt(max(tail.var()-row['beta_252']**2*mt.var(),0)) if np.isfinite(row['beta_252']) else np.nan
            row['downside_deviation']=np.sqrt(np.mean(np.minimum(hist.tail(63),0)**2)) if len(hist)>=63 else np.nan
            wealth=(1+hist.tail(252)).cumprod();row['drawdown_252']=(wealth/wealth.cummax().clip(lower=1)-1).min() if len(hist)>=252 else np.nan
            recent=avail.tail(21);row['dollar_volume']=float((recent.close*recent.volume).mean())
            row['log_dollar_volume']=np.log(row['dollar_volume']) if row['dollar_volume']>0 else np.nan
            row['turnover']=divide(float(recent.volume.mean()),row['shares']*1e6)
            dv=(px.close*px.volume).reindex(hist.index).replace(0,np.nan)
            row['amihud']=float((hist.abs()/dv).tail(21).mean())*1e6
            # External closing timestamps are ambiguous: lag every observation one US session.
            for ticker,name in [('TNX','yield_10y'),('IRX','yield_short'),('^VIX','vix'),('HG=F','copper'),('GC=F','gold'),('SI=F','silver'),('CL=F','oil'),('NG=F','gas'),('EURUSD=X','eurusd'),('DX-Y.NYB','dollar')]:
                if ticker not in allpx:continue
                series=allpx[ticker].close.reindex(sessions).ffill().shift(1).loc[:date]
                observed=series.resample('ME').last();levels=observed.dropna()
                if levels.empty:continue
                if name.startswith('yield_'):row[name]=levels.iloc[-1]/100;row[name+'_change']=(levels.iloc[-1]-levels.iloc[-2])/100 if len(levels)>1 else np.nan
                elif name=='vix':row[name]=levels.iloc[-1]/100
                else:
                    row[name+'_return']=levels.iloc[-1]/levels.iloc[-2]-1 if len(levels)>1 and levels.iloc[-2]>0 else np.nan
                    row[name+'_vol']=series.pct_change(fill_method=None).tail(21).std()
            row['term_spread']=row['yield_10y']-row['yield_short']
            row['driver_return']=row.get('copper_return' if driver=='HG=F' else 'gas_return',np.nan)
            row['driver_vol']=row.get('copper_vol' if driver=='HG=F' else 'gas_vol',np.nan)
            for series,name in [('BAMLH0A0HYM2','credit_spread'),('DFII10','real_yield')]:
                path=RAW/f'{series}.csv'
                if not path.exists():continue
                z=pd.read_csv(path,index_col=0,parse_dates=True).iloc[:,0];z=pd.to_numeric(z,errors='coerce')
                z=z.reindex(sessions).ffill().shift(1).loc[:date].resample('ME').last().dropna()
                if len(z):row[name]=z.iloc[-1]/100
                if len(z)>1:row[name+'_change']=(z.iloc[-1]-z.iloc[-2])/100
            # Outcomes do not enter any feature computation.
            next_label=label+pd.offsets.MonthEnd(1)
            row['target_end']=str(next_label.date())
            row['return_target']=monthly.at[next_label,tk] if next_label<=pd.Timestamp(LAST_MONTH) and next_label in monthly.index else np.nan
            row['variance_target']=variance.at[next_label,tk] if next_label<=pd.Timestamp(LAST_MONTH) and next_label in variance.index else np.nan
            row['market_target']=monthly.at[next_label,'SPY'] if next_label<=pd.Timestamp(LAST_MONTH) and next_label in monthly.index else np.nan
            next3=monthly[tk].reindex(pd.date_range(next_label,periods=3,freq='ME'))
            row['return_target_3m']=(1+next3).prod()-1 if next3.notna().all() and next3.index[-1]<=pd.Timestamp(LAST_MONTH) else np.nan
            rows.append(row)
        audits.extend(sel.audit)
        print('FEATURES',tk,'months',sum(x['ticker']==tk for x in rows),flush=True)
    d=pd.DataFrame(rows).sort_values(['ticker','date'])
    for name in ['revenue_growth','operating_margin','roe','earnings_yield','pe','yield_10y','driver_return']:
        d[name+'_diff']=d.groupby('ticker')[name].diff()
        d[name+'_lag1']=d.groupby('ticker')[name].shift(1)
    for name in ['revenue_growth','operating_margin','earnings_yield','market_return','industry_relative','driver_return']:
        d[name+'_lag3']=d.groupby('ticker')[name].shift(3)
    d['ebitda_growth']=d.groupby('ticker').ebitda.pct_change(12,fill_method=None)
    d.loc[d.groupby('ticker').ebitda.shift(12)<=0,'ebitda_growth']=np.nan
    for name in ['earnings_yield','pe','fcf_equipment_yield']:
        d[name+'_relative']=d.groupby('ticker')[name].transform(lambda s:s-s.shift(1).rolling(60,min_periods=36).median())
        # Trailing percentile of the current value inside its own preceding window,
        # which excludes the current observation and never looks at later years.
        d[name+'_percentile']=d.groupby('ticker')[name].transform(trailing_percentile)
    d['pe_pct_change']=d.groupby('ticker').pe.pct_change(fill_method=None)
    d['earnings_yield_z']=d.groupby('ticker').earnings_yield.transform(lambda s:(s-s.shift(1).rolling(36,min_periods=24).mean())/s.shift(1).rolling(36,min_periods=24).std())
    d['revenue_valuation_interaction']=d.revenue_growth*d.earnings_yield
    d['margin_valuation_interaction']=d.operating_margin*d.earnings_yield
    # Other selected firms are reference peers only, not an assertion of economic equivalence.
    d['peer_earnings_yield_gap']=np.nan
    for date,g in d[d.ticker.isin(CORE)].groupby('date'):
        for idx,row in g.iterrows():
            peers=g.loc[g.ticker!=row.ticker,'earnings_yield'].dropna()
            if len(peers)>=3:d.loc[idx,'peer_earnings_yield_gap']=row.earnings_yield-peers.median()
    for tk,g in d.groupby('ticker'):
        median=g.market_vol.shift(1).rolling(60,min_periods=36).median()
        d.loc[g.index,'high_vol_regime']=(g.market_vol>median).astype(float).where(median.notna())
    # An unavailable three-month yield change is not a falling-rate regime.
    change=d.groupby('ticker').yield_10y.diff(3)
    d['rate_rising_regime']=(change>0).astype(float).where(change.notna())
    # Registry covers tested representations plus explicitly deferred requests.
    groups={
      'market':['market_return','market_vol','smallcap_return','yield_10y','yield_short','yield_10y_change','term_spread','vix','credit_spread','credit_spread_change','real_yield','real_yield_change','eurusd_return','dollar_return'],
      'financial':['revenue_growth','eps_growth','eps_change_price','loss_transition','ebitda_growth','gross_margin','operating_margin','net_margin','ebitda_margin','roa','roe','cfo_assets','fcf_equipment_assets','capex_assets','cash_assets','debt_assets','debt_equity','interest_coverage','current_ratio','quick_ratio','payout','earnings_age_days'],
      'valuation':['earnings_yield','book_yield','sales_yield','fcf_equipment_yield','dividend_yield','earnings_yield_relative','earnings_yield_percentile','fcf_equipment_yield_relative','pe_percentile','peer_earnings_yield_gap'],
      'momentum':['momentum_1','momentum_3','momentum_6','momentum_12','relative_momentum','industry_momentum_relative'],
      'risk':['vol_21','vol_63','vol_252','beta_252','idio_vol','downside_deviation','drawdown_252','log_dollar_volume','turnover','amihud'],
      'industry':['industry_vol','sector_return','semis_return','defense_return'],
      'business':['driver_vol','copper_return','gold_return','silver_return','gas_return','oil_return'],
      'transform':['revenue_growth_diff','operating_margin_diff','roe_diff','earnings_yield_diff','revenue_growth_lag1','earnings_yield_lag1','pe_pct_change','earnings_yield_z'],
      'interaction':['revenue_valuation_interaction','margin_valuation_interaction'],
      'claims_proxy':['roic_proxy','ev_ebitda_proxy','ev_sales_proxy'],
      'mine_inclusive_fcf':['fcf_yield','fcf_assets']}
    for group,names in groups.items():
        for name in names:
            if name not in d:d[name]=np.nan
            register(name,group,formula_for(name),status='implemented' if d[name].notna().any() else 'unavailable')
    for name in ['pe','pb','ps','pe_relative']:
        register(name,'valuation',formula_for(name),status='reported; reciprocal/related representation tested instead where redundant')
    for name,why in [('forward_pe','No archived historical analyst consensus'),('earnings_surprise','Consensus with matching original EPS basis unavailable'),('analyst_revisions','No point-in-time estimate archive'),('bid_ask_spread','Historical contemporaneous quotes unavailable'),('roic','Claims/tax/invested-capital reconciliation incomplete; explicitly labeled proxy sensitivity available'),('ev_ebitda','Full preferred/pension/lease/other claims unreconciled; proxy sensitivity only'),('ev_sales','Full claims bridge unavailable; proxy sensitivity only'),('index_membership_return','Historical constituent membership unavailable; index/sector proxies used'),('tungsten_molybdenum_prices','Comparable accessible historical price series not established')]:
        register(name,'deferred',why,status='deferred');defer(name,why)
    d.to_csv(OUT/'monthly_features_as_known.csv',index=False)
    pd.DataFrame(audits).to_csv(OUT/'feature_availability_audit.csv',index=False)
    pd.DataFrame(META.values()).to_csv(OUT/'feature_registry.csv',index=False)
    pd.DataFrame(exposure).to_csv(OUT/'exposure_map.csv',index=False)
    coverage=[]
    for tk,g in d.groupby('ticker'):
        use=g[g.date>='2015-12-31']
        for name,v in META.items():coverage.append(dict(ticker=tk,variable=name,group=v['group'],observations=len(use),available=int(use[name].notna().sum()) if name in use else 0,status=v['status']))
    pd.DataFrame(coverage).to_csv(OUT/'feature_coverage.csv',index=False)
    (OUT/'feature_groups.json').write_text(json.dumps(groups,indent=2)+'\n')
    d[['ticker','date','origin','target_end','return_target','variance_target','market_target','return_target_3m']].to_csv(OUT/'targets.csv',index=False)

def formula_for(name):
    exact={'revenue_growth':'Latest quarterly revenue / corresponding prior-year quarter revenue - 1',
    'eps_growth':'Quarterly diluted EPS / positive prior-year quarterly EPS - 1; positive current EPS required',
    'roa':'TTM net income / average beginning/end assets','roe':'TTM common income / average beginning/end parent equity',
    'earnings_yield':'TTM common earnings / (latest filed actual shares × origin close)',
    'book_yield':'Parent equity / common market cap','sales_yield':'TTM revenue / common market cap',
    'fcf_yield':'(TTM CFO - equipment capex - MTRN mine development) / common market cap; MTRN mine-inclusive sensitivity only',
    'fcf_equipment':'TTM CFO - TTM equipment capex, on the shared CFO/capex reporting period; excludes separately reported mine development',
    'fcf_equipment_yield':'(TTM CFO - equipment capex) / common market cap; the modelled free-cash-flow yield',
    'fcf_equipment_assets':'(TTM CFO - equipment capex) / total assets at that flow period end',
    'eps_change_price':'(Latest quarterly diluted EPS - prior-year quarterly EPS) / origin close; retains losses and zero crossings that percentage growth cannot express',
    'loss_transition':'1 when the current or prior-year comparable quarterly EPS is not positive, else 0',
    'earnings_age_days':'Origin date minus the period end of the trailing common-earnings measure',
    'earnings_yield_percentile':'Share of the preceding 60 monthly earnings yields below the current one; at least 36 prior observations; current value excluded from the reference window',
    'pe_percentile':'Share of the preceding 60 monthly P/E observations below the current one; at least 36 prior observations',
    'fcf_equipment_yield_percentile':'Share of the preceding 60 monthly equipment free-cash-flow yields below the current one',
    'pe':'Common market cap / positive TTM common income','pb':'Common market cap / positive parent equity','ps':'Common market cap / TTM revenue',
    'roic_proxy':'0.75 × TTM operating income / (latest total equity + debt - cash); end balance, limited claims proxy',
    'ev_ebitda_proxy':'(market cap + debt - cash + reported NCI proxy) / positive operating EBITDA',
    'ev_sales_proxy':'Same limited-claims enterprise-value proxy / TTM revenue',
    'quick_ratio':'(current assets - inventories) / current liabilities; excludes inventories but includes other current noncash assets',
    'amihud':'Mean over prior 21 sessions of abs(daily return)/(close × volume), multiplied by 1e6',
    'downside_deviation':'sqrt(mean(min(daily return,0)^2)) over past 63 sessions; downside deviation, not central variance',
    'financial_age_days':'Origin date minus latest revenue reporting-period end',
    'driver_return':'Prior-known monthly copper-futures price change for MTRN; natural-gas-futures change for other established firms; indirect cost hypothesis',
    'peer_earnings_yield_gap':'Own earnings yield minus median of the other three established issuers; heterogeneous-reference sensitivity',
    'dividend_yield':'Trailing reported common dividend cash outflow / current market cap',
    'interest_coverage':'TTM operating income / positive reported interest expense',
    'current_ratio':'Current assets / current liabilities',
    'payout':'Trailing common dividend cash outflow / positive common income'}
    if name in exact:return exact[name]
    if name.endswith('_diff'):return name[:-5]+' at origin minus its preceding monthly as-known value'
    if '_lag' in name:return 'Value of '+name.split('_lag')[0]+' '+name.split('_lag')[1]+' months before origin'
    if name.endswith('_relative'):return 'Origin value minus preceding 60-month median, at least 36 prior observations; except industry-relative return = industry minus market'
    if name.endswith('_assets'):return 'TTM '+name.replace('_assets','')+' / latest available total assets (end balance, not average)'
    if name.endswith('_margin'):return 'TTM '+name.replace('_margin','')+' income/profit / TTM revenue'
    if name.startswith('momentum_'):return 'Compounded adjusted-close return over preceding '+name.split('_')[1]+' months'
    if name.startswith('vol_'):return 'Sample daily-return standard deviation over preceding '+name.split('_')[1]+' sessions'
    if name.endswith('_return'):return 'Completed monthly arithmetic price/adjusted-close change; external prices shifted one US session'
    return name.replace('_',' ')+'; see features.py for the exact saved transformation'

if __name__=='__main__':build()
