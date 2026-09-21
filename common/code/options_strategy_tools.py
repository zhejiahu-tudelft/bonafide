"""Position-weighted Greeks and expiration payoff in dollars per strategy.

Legs use quantity >0 for bought options, <0 for sold options, and multiplier 100
unless the actual contract specifies otherwise. Price input is per share.
"""
import numpy as np
GREEKS=('delta','gamma','theta','vega','vanna','vomma')

def aggregate(legs):
    result={g:sum(x['quantity']*x.get('multiplier',100)*x[g] for x in legs) for g in GREEKS}
    result['premium_paid']=sum(x['quantity']*x.get('multiplier',100)*x['price'] for x in legs)
    return result

def expiry_payoff(legs,spots,stock_shares=0,stock_cost=0):
    s=np.asarray(spots,dtype=float); value=stock_shares*(s-stock_cost)
    for x in legs:
        intrinsic=np.maximum(s-x['strike'],0) if x['type']=='call' else np.maximum(x['strike']-s,0)
        value=value+x['quantity']*x.get('multiplier',100)*(intrinsic-x['price'])
    return value

def execution_price(bid,ask,quantity):
    """Conservative executable-side estimate before commissions/slippage."""
    if not (ask>=bid>0): raise ValueError('Invalid two-sided quote')
    return ask if quantity>0 else bid
