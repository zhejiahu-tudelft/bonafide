"""SEC company-facts selection with explicit periods and a source audit trail."""
import datetime as dt
import math

class Facts:
    def __init__(self,data,cutoff):
        self.data=data['facts']; self.cutoff=cutoff; self.audit=[]
    def get(self,tags,end,start=None,unit='USD',namespace='us-gaap',label=''):
        if isinstance(tags,str): tags=[tags]
        for tag in tags:
            entries=self.data.get(namespace,{}).get(tag,{}).get('units',{}).get(unit,[])
            rows=[x for x in entries if x['end']==end and x.get('start')==start and x.get('filed','')<=self.cutoff and x.get('form') in ('10-K','10-Q')]
            if not rows: continue
            x=max(rows,key=lambda v:(v.get('filed',''),v.get('accn','')))
            self.audit.append(dict(metric=label or tag,tag=tag,namespace=namespace,unit=unit,**x))
            return x['val']
        self.audit.append(dict(metric=label or '|'.join(tags),tag='MISSING',start=start,end=end,unit=unit))
        return float('nan')

def cagr(first,last,years):
    return (last/first)**(1/years)-1 if first>0 and last>0 and years>0 else float('nan')

def fcff(ebit,tax,da,capex,change_nwc):
    return ebit*(1-tax)+da-capex-change_nwc

def dcf(cashflows,wacc,g,net_claims,shares,first_time=1,terminal_cashflow=None):
    if wacc<=g or shares<=0: raise ValueError('DCF requires WACC > g and positive shares')
    pv=sum(cf/(1+wacc)**(first_time+i) for i,cf in enumerate(cashflows))
    terminal=(cashflows[-1]*(1+g) if terminal_cashflow is None else terminal_cashflow)/(wacc-g)
    pv_terminal=terminal/(1+wacc)**(first_time+len(cashflows)-1)
    enterprise=pv+pv_terminal; equity=enterprise-net_claims
    return dict(pv_explicit=pv,pv_terminal=pv_terminal,enterprise=enterprise,equity=equity,per_share=equity/shares,terminal_share=pv_terminal/enterprise)
