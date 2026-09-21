"""Accession-audited historical snapshots and retrospective operating history."""
import json
import numpy as np,pandas as pd
from settings import *
from market_analysis import load_prices
from common.code.point_in_time import PointInTimeFacts

def add_mine_disclosures(selector):
    """Restore company-specific annual mining-capex tags from archived 10-Ks."""
    index=json.loads((RAW/'filing_index.json').read_text());manual=[]
    for year,value,filed in [(2021,0.,'2022-02-17'),(2022,0.,'2023-02-16'),(2023,9.326,'2024-02-15'),(2024,12.159,'2025-02-19'),(2025,26.288,'2026-02-12')]:
        record=next(x for x in index if x['ticker']=='MTRN' and x['form']=='10-K' and x['filingDate']==filed)
        e=dict(start=f'{year}-01-01',end=f'{year}-12-31',val=round(value*1e6),filed=filed,form='10-K',accn=record['accessionNumber'],
               source_note='Cash-flow statement: Payments for mine development; dash is explicit zero',manual_verified=True)
        selector.data['facts']['us-gaap']['PaymentsToAcquireMiningAssets']['units']['USD'].append(e);manual.append(e)
    (OUT/'manual_mine_disclosures.json').write_text(json.dumps(manual,indent=2))

TAGS={
 'revenue':['RevenueFromContractWithCustomerExcludingAssessedTax','SalesRevenueNet','SalesRevenueGoodsNet'],
 'operating_income':['OperatingIncomeLoss'], 'net_income':['NetIncomeLoss'],
 'cfo':['NetCashProvidedByUsedInOperatingActivities'],
 'equipment_capex':['PaymentsToAcquireOtherPropertyPlantAndEquipment','PaymentsToAcquirePropertyPlantAndEquipment','PaymentsToAcquireProductiveAssets'],
 'da':['DepreciationDepletionAndAmortization','DepreciationDepletionAndAmortizationPropertyPlantAndEquipment','DepreciationAndAmortization','DepreciationAmortizationAndAccretionNet'],
}

def metrics(selector,asof,end=None,annual=False):
    out={};ends={}
    for metric,tags in TAGS.items():
        if annual:
            x=selector.select(tags,asof,end=end,min_days=330,max_days=400,label=metric)
            val=x['val'] if x else np.nan;period=x['end'] if x else None
        else:val,period=selector.ttm(tags,asof,label=metric)
        out[metric]=val/1e6;ends[metric]=period
    out['period_end']=ends['revenue']
    # A metric with an older reporting end cannot silently enter this snapshot.
    for key in TAGS:
        if ends[key]!=out['period_end']:out[key]=np.nan
    if selector.ticker=='ENTG':
        values=[]
        for tag in ['Depreciation','AmortizationOfIntangibleAssets']:
            if annual:
                e=selector.select(tag,asof,end=end,min_days=330,max_days=400,label='DA_component')
                v=e['val'] if e else np.nan;dt=e['end'] if e else None
            else:v,dt=selector.ttm(tag,asof,label='DA_component')
            values.append(v/1e6 if dt==out['period_end'] else np.nan)
        out['da']=sum(values)
    out['mine_capex']=0. if selector.ticker!='MTRN' else np.nan
    if selector.ticker=='MTRN':
        if annual:
            x=selector.select('PaymentsToAcquireMiningAssets',asof,end=end,min_days=330,max_days=400,label='mine_capex')
            v=x['val']/1e6 if x else np.nan;dt=x['end'] if x else None
            # FY23 annual report cash-flow line, separately archived in the base study.
            if end=='2023-12-31' and asof>='2024-02-16':v=9.326;dt=end
        else:
            v,dt=selector.ttm('PaymentsToAcquireMiningAssets',asof,label='mine_capex');v/=1e6
        if dt==out['period_end']:out['mine_capex']=v
    out['total_capex']=out['equipment_capex']+out['mine_capex']
    out['fcf']=out['cfo']-out['total_capex']
    out['operating_ebitda']=out['operating_income']+out['da']
    out['operating_margin']=out['operating_income']/out['revenue'] if out['revenue']>0 else np.nan
    out['fcf_net_income']=out['fcf']/out['net_income'] if out['net_income']>0 else np.nan
    return out

def build():
    initialize();prices=load_prices();sessions=prices['SPY'].index
    snapshots=[];history=[];quarters=[];audits=[]
    endpoints=['2015-12-31','2020-12-31','2025-12-31','2026-04-23',CUTOFF]
    for tk in TICKERS:
        selector=PointInTimeFacts(facts_path(tk),sessions,tk)
        if tk=='MTRN':add_mine_disclosures(selector)
        for asof in endpoints:
            if tk=='ELMT' and asof<'2026-04-23':continue
            row=dict(ticker=tk,asof=asof,**metrics(selector,asof))
            eps,eps_end=selector.ttm('EarningsPerShareDiluted',asof,unit='USD/shares',label='rolling_disclosed_diluted_eps')
            row.update(eps=eps,eps_period_end=eps_end,eps_basis='annual + current YTD - prior YTD diluted EPS; approximate rolling EPS due to share-weight changes')
            p=prices[tk].loc[:asof].iloc[-1];row.update(price=p.close,adj_close=p.adj_close)
            row['pe']=p.close/eps if eps>.10 else np.nan
            actual=selector.select('EntityCommonStockSharesOutstanding',asof,unit='shares',namespace='dei',label='actual_shares')
            row['actual_shares']=actual['val']/1e6 if actual else np.nan
            row['share_date']=actual['end'] if actual else None
            row['market_cap']=row['actual_shares']*row['price']
            end=row['period_end']
            for name,tags in [('cash',['CashAndCashEquivalentsAtCarryingValue']),('assets',['Assets']),('equity',['StockholdersEquity'])]:
                row[name]=selector.value(tags,asof,end=end,label=name)/1e6 if end else np.nan
            if end:
                if tk=='ATI':debt=selector.value(['DebtAndCapitalLeaseObligations'],asof,end=end,label='debt_total')
                elif tk=='ELMT':debt=selector.value(['LongTermDebt'],asof,end=end,label='debt_total')
                else:
                    noncur=selector.value(['LongTermDebtNoncurrent','LongTermDebt'],asof,end=end,label='debt_noncurrent')
                    cur=selector.value(['DebtCurrent','LongTermDebtCurrent','LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths'],asof,end=end,label='debt_current')
                    debt=noncur+cur
                row['debt']=debt/1e6
            else:row['debt']=np.nan
            row['net_debt']=row['debt']-row['cash']
            row['fcf_yield']=row['fcf']/row['market_cap']
            row['price_sales']=row['market_cap']/row['revenue']
            row['price_book']=row['market_cap']/row['equity'] if row['equity']>0 else np.nan
            row['claims_note']='Debt at carrying value; latest filed actual common shares; leases/preferred/minority not fully reconciled. No EV multiple published.'
            if tk=='ELMT':
                row['pe']=np.nan;row['fcf_yield']=np.nan
                row['claims_note']='Pre-IPO EPS/share restructuring incomparable. Q2 balance sheet predates Sept14 preferred financing; not a cutoff pro-forma enterprise value.'
            snapshots.append(row)
        annual_ends=sorted({x['end'] for x in selector.entries(TAGS['revenue']) if 330<=x['days']<=400 and x['available']<=CUTOFF and x['end']>='2015-01-01'})
        for end in annual_ends:history.append(dict(ticker=tk,vintage='latest eligible filing at cutoff; recasts retained',**metrics(selector,CUTOFF,end,True)))
        qends=sorted({x['end'] for x in selector.entries(TAGS['revenue']) if 60<=x['days']<=110 and x['available']<=CUTOFF and x['end']>='2020-01-01'})
        for end in qends:
            row=dict(ticker=tk,period_end=end,vintage='cutoff recast; directly disclosed quarters only')
            for metric in ['revenue','operating_income','net_income']:
                row[metric]=selector.value(TAGS[metric],CUTOFF,end=end,min_days=60,max_days=110,label='quarter_'+metric)/1e6
            row['eps']=selector.value('EarningsPerShareDiluted',CUTOFF,end=end,min_days=60,max_days=110,unit='USD/shares',label='quarter_eps')
            # Discrete cash flow is derived only from same-filing YTD and prior YTD.
            for metric in ['cfo','equipment_capex']:
                candidates=[x for x in selector.entries(TAGS[metric]) if x['end']==end and 60<=x['days']<=310 and x['available']<=CUTOFF]
                if not candidates:row[metric]=np.nan;continue
                cur=max(candidates,key=lambda x:(x['days'],-x['priority'],x['filed']))
                prior=[x for x in selector.entries(TAGS[metric]) if x.get('start')==cur.get('start') and x['accn']==cur['accn'] and 60<=cur['days']-x['days']<=110]
                row[metric]=(cur['val']-(max(prior,key=lambda x:x['days'])['val'] if prior else 0))/1e6 if cur['days']<=110 or prior else np.nan
            quarters.append(row)
        audits+=selector.audit
    s=pd.DataFrame(snapshots);s.to_csv(OUT/'financial_snapshots.csv',index=False)
    pd.DataFrame(history).to_csv(OUT/'annual_operating_history.csv',index=False)
    pd.DataFrame(quarters).to_csv(OUT/'quarterly_operating_history.csv',index=False)
    a=pd.DataFrame(audits);a['source_url']=[f'https://www.sec.gov/Archives/edgar/data/{CIKS[tk]}/{acc.replace("-","")}/' for tk,acc in zip(a.ticker,a.accn)]
    a.to_csv(OUT/'financial_fact_audit.csv',index=False)
    bridges=[]
    for panel,date in [('long','2015-12-31'),('recent','2020-12-31'),('ytd','2025-12-31'),('matched','2026-04-23')]:
        for tk in TICKERS:
            start=s[(s.ticker==tk)&(s['asof']==date)];finish=s[(s.ticker==tk)&(s['asof']==CUTOFF)]
            if start.empty:continue
            a=start.iloc[0];b=finish.iloc[0];valid=tk!='ELMT' and np.isfinite(a.pe) and np.isfinite(b.pe)
            row=dict(panel=panel,ticker=tk,start=date,end=CUTOFF,price_start=a.price,price_end=b.price,eps_start=a.eps,eps_end=b.eps,
                     pe_start=a.pe,pe_end=b.pe,price_return=b.price/a.price-1,total_return=b.adj_close/a.adj_close-1,
                     dividend_reinvestment_gap=b.adj_close/a.adj_close-b.price/a.price,valid=valid)
            if valid:
                lp=np.log(b.price/a.price);le=np.log(b.eps/a.eps);lm=np.log(b.pe/a.pe)
                row.update(log_price=lp,log_eps=le,log_multiple=lm,identity_error=abs(lp-le-lm),limitation=a.eps_basis)
            else:row['limitation']='Nonpositive/near-zero EPS or ELMT share-basis discontinuity; no earnings/multiple log bridge.'
            bridges.append(row)
    pd.DataFrame(bridges).to_csv(OUT/'accounting_bridges.csv',index=False)
    deferred('Fully reconciled EV/EBITDA, EV bridges and ROIC','Lease, minority, pension and preferred claims and historical invested-capital definitions are not uniformly reconciled. Report operating EBITDA and common-equity multiples where valid; no false cross-company EV precision.')
    deferred('Complete discrete quarterly cash-flow history','Same-accession YTD subtraction only. Missing same-vintage components and undisclosed Q4 data remain missing; annual and TTM cash flows are available.')
    deferred('Exact rolling diluted EPS denominator','Annual + YTD - prior YTD disclosed diluted EPS is a transparent approximation because EPS is not additive under changing share weights. Price/log bridge reconciles exactly for this explicitly defined earnings proxy; no causal earnings attribution.')
    print('Financials:',len(s),'snapshots;',len(history),'annual rows;',len(audits),'audited selections')

if __name__=='__main__':build()
