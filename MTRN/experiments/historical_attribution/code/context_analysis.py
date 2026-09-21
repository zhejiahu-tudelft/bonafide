"""Disclosure-based context, ELMT claim review, source and security coverage."""
import json,hashlib,re
import numpy as np,pandas as pd
from bs4 import BeautifulSoup
from settings import *
from market_analysis import load_prices

def build():
    prices=load_prices();returns=pd.read_csv(OUT/'daily_returns.csv',index_col=0,parse_dates=True)
    filings=json.loads((RAW/'filing_index.json').read_text());manifest=json.loads((SOURCES/'manifest.json').read_text())
    exposure=[
      dict(ticker='MTRN',exchange='NYSE',exposure='Semiconductor materials; beryllium and other critical materials; industrial and aerospace/defense',comparability='Metal pass-through makes revenue margins unlike value-added margins; HCS acquisition changes mix in 2021'),
      dict(ticker='ENTG',exchange='Nasdaq',exposure='Semiconductor process materials, filtration, contamination control and wafer-fab spending',comparability='CMC acquisition in 2022, subsequent disposals, debt and acquired-intangible amortization affect comparisons'),
      dict(ticker='CRS',exchange='NYSE',exposure='Specialty alloys; aerospace engines, defense, medical and industrial customers',comparability='June fiscal year end; surcharge sales differ from sales excluding surcharge; no equivalence to MTRN VA sales'),
      dict(ticker='ATI',exchange='NYSE',exposure='Aerospace/defense specialty alloys, titanium and advanced materials; industrial demand',comparability='Exit from standard stainless products and impairments alter historical mix; consolidated profit includes minority interests'),
      dict(ticker='ELMT',exchange='Nasdaq',exposure='Tungsten and molybdenum; defense, industrial and semiconductor applications',comparability='April 2026 IPO/reorganization; SBC, grant-funded investment, and Sept preferred/warrants change common-equity claims'),
    ]
    for x in exposure:
        tk=x['ticker'];x['cik']=CIKS[tk];x['currency']='USD';x['weights']='Qualitative; no present-day weights backfilled into history'
        sub=json.loads((RAW/f'submissions_{tk}.json').read_text());x['legal_name']=sub.get('name');x['source_url']=f'https://data.sec.gov/submissions/CIK{CIKS[tk]:010d}.json'
    pd.DataFrame(exposure).to_csv(OUT/'business_exposure.csv',index=False)
    coverage=[];jumps=[]
    for tk,p in prices.items():
        if tk in TICKERS:
            ep=REPO/f'MTRN/data/market_data/{tk}_events.json'
            if not ep.exists():ep=RAW/f'{tk}_events.json'
            actions=json.loads(ep.read_text()) if ep.exists() else {};splits=actions.get('splits',{})
            studied=[x for x in splits.values() if START<=pd.to_datetime(x['date'],unit='s').strftime('%Y-%m-%d')<=CUTOFF]
            coverage.append(dict(ticker=tk,first_close=str(p.index[0].date()),last_close=str(p.index[-1].date()),
                                 study_closes=len(p.loc[START:]),splits_in_study=len(studied),price_source='Yahoo chart adjusted close; total-return proxy',
                                 financial_source='SEC original accessions; next-session date-only filing availability'))
            for date,r in returns[tk].loc[START:].abs().nlargest(3).items():
                jumps.append(dict(ticker=tk,date=str(date.date()),return_value=returns.loc[date,tk],
                                  corporate_action='No study-period split recorded',verification='Retained; second-provider price verification incomplete'))
    pd.DataFrame(coverage).to_csv(OUT/'coverage.csv',index=False)
    # Check the archived second-provider table for ELMT without altering price history.
    soup=BeautifulSoup((SOURCES/'ELMT_history.html').read_text(),'html.parser');checks=[]
    for tr in soup.select('tr'):
        cells=[x.get_text(' ',strip=True) for x in tr.select('td')]
        if len(cells)<6:continue
        try:date=pd.to_datetime(cells[0],format='%b %d, %Y');close=float(cells[4].replace(',',''))
        except (ValueError,TypeError):continue
        if date in prices['ELMT'].index and date<=pd.Timestamp(CUTOFF):
            checks.append(dict(ticker='ELMT',date=str(date.date()),primary_close=prices['ELMT'].loc[date,'close'],secondary_close=close,
                               difference=prices['ELMT'].loc[date,'close']-close,source='https://stockanalysis.com/stocks/elmt/history/'))
    pd.DataFrame(checks).to_csv(OUT/'secondary_price_checks.csv',index=False)
    for row in jumps:
        if row['ticker']=='ELMT' and row['date'] in {x['date'] for x in checks}:row['verification']='Close reconciled to archived Stock Analysis table'
        if row['ticker']=='MTRN' and row['date']=='2026-08-05':row['verification']='Earnings release and original study secondary price-source review; genuine jump retained'
    pd.DataFrame(jumps).to_csv(OUT/'large_move_audit.csv',index=False)
    e=pd.read_csv(OUT/'earnings_announcements.csv');strategic=[]
    for tk,date,description in [('MTRN','2021-11-02','Completed HCS-Electronic Materials acquisition discussed with results; greater semiconductor exposure'),
            ('MTRN','2026-02-12','$65m customer investment to support defense initiatives disclosed with results; funding is not current earnings'),
            ('ENTG','2022-02-01','Pending CMC Materials acquisition discussed with results; subsequent acquisition changes debt and business comparability'),
            ('ATI','2021-01-28','Exit from standard stainless sheet products; restructuring and impairments discussed with results'),
            ('CRS','2026-07-30','Fiscal 2027 outlook, fiscal 2029 targets and quarterly share repurchases disclosed with results')]:
        row=e[(e.ticker==tk)&(e.release_date==date)].iloc[0]
        strategic.append(dict(ticker=tk,date=date,event=description,source_url=row.source_url,archive=row.release_path,overlap='Earnings and guidance; event cannot isolate this mechanism',date_kind='Verified disclosure date; not necessarily transaction date'))
    for date,name,desc in [('2026-04-23','ELMT_IPO.html','First Nasdaq trading close; IPO offer $14, 9.9m shares; IPO closing release published Apr24'),
             ('2026-09-14','ELMT_financing_8K.html','Government preferred-equity and warrant financing, conditional additional tranches and stockpile contract')]:
        src=next(x['url'] for x in manifest if x.get('path','').endswith(name) and x.get('sha256'))
        strategic.append(dict(ticker='ELMT',date=date,event=desc,source_url=src,archive='sources/'+name,overlap='IPO/reorganization' if 'IPO' in name else 'Financing + procurement + upcoming Sep16 FOMC',date_kind='Public trading/disclosure date'))
    pd.DataFrame(strategic).to_csv(OUT/'strategic_events.csv',index=False)
    # Manually reconciled H1 GAAP cash-flow and balance-sheet lines, $m.
    elmt=dict(period='2026 H1; Jan1–Jul3 (not TTM)',release='2026-08-13',available='2026-08-14',
              revenue=122.408,revenue_prior=95.517,operating_income=-5.765,operating_income_prior=6.104,net_income=-4.826,
              cfo=-7.572,capex_net_grants=3.141,fcf_net_grants=-10.713,da=3.779,sbc=10.735,
              cash_q2=66.122,debt_carrying_q2=10.478,equity_q2=187.543,actual_shares=30.459498,
              common_capitalization=30.459498*prices['ELMT'].iloc[-1].close,
              preferred_initial_claim=200.,conditional_additional_financing=250.,preferred_pik_rate=.055,
              penny_warrants=5675506,regular_warrants=1891835,regular_strike=15.92,
              contract_ceiling=2000.,funded_commitment=150.,
              source_q2='sources/ELMT_2026-08-13_10-Q.html',source_terms='sources/ELMT_financing_8K.html',
              limitation='Q2 cash/debt are stale relative to financing. Preferred claim partly reduces on penny warrant exercise; do not add full preferred plus full dilution mechanically. Capex is net of grants, unlike peers.')
    (OUT/'ELMT_case.json').write_text(json.dumps(elmt,indent=2))
    case=[]
    for label,begin,end in [('announcement day','2026-09-11','2026-09-14'),('through next close','2026-09-11','2026-09-15'),('through cutoff','2026-09-11',CUTOFF)]:
        r={tk:prices[tk].loc[end,'adj_close']/prices[tk].loc[begin,'adj_close']-1 for tk in ['ELMT','SPY','ITA']}
        case.append(dict(window=label,start_close=begin,end_close=end,elmt_return=r['ELMT'],spy_return=r['SPY'],ita_return=r['ITA'],
                         relative_spy=r['ELMT']-r['SPY'],relative_ita=r['ELMT']-r['ITA']))
    pd.DataFrame(case).to_csv(OUT/'ELMT_event_returns.csv',index=False)
    deferred('ELMT long-history, full monthly and formal event-study models','103 public closes / 102 close-to-close returns from Apr23; fewer than 160 pre-event sessions. Only common daily market model and descriptive benchmark-relative event returns.')
    deferred('Consensus, historical guidance/backlog revision regressions','Recoverable historical expectations were not assembled. Primary disclosure covariates are original GAAP EPS changes and margin changes, not consensus surprises.')
    deferred('Comprehensive strategic-event census and real-economy time-series regressions','Selected source-established events and archived industry context are reported separately; not a complete policy, contract, quality, acquisition or lockup history. No claimed statistical attribution from this selected register.')
    deferred('Historical ETF holdings and own-stock contamination','Saved issuer descriptions establish SOXX/ITA relevance. Historical constituent weights were not recovered; any issuer overlap is unquantified, so ETF co-movement is descriptive.')
    deferred('Factor vintage available exactly at cutoff','French July 2026 data were retrieved Sept20. No economic observations after cutoff are used, but exact Sept18-vintage equivalence cannot be established. All factor regressions are explicitly retrospective-vintage estimates, not a point-in-time backtest.')
    print('Business context, ELMT case and source checks completed')

if __name__=='__main__':build()
