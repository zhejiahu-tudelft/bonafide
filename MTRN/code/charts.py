"""Charts derived only from the saved, reconciled analytical tables."""
from pathlib import Path
import sys
import pandas as pd,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from common.code.chart_tools import *
from config import price_history
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'data/processed_data';OUT=D/'charts'
def build():
 configure();h=pd.read_csv(D/'financial_history.csv',index_col='period').loc[['2021','2022','2023','2024','2025','TTM']]
 fig,ax=plt.subplots(1,2,figsize=(11,4));x=np.arange(len(h))
 ax[0].bar(x-.18,h.revenue,width=.36,label='GAAP revenue',color=NAVY);ax[0].bar(x+.18,h.va_sales,width=.36,label='Value-added sales',color=TEAL)
 ax[0].set_xticks(x,h.index);ax[0].set_title('Metal pass-through distorts revenue growth');ax[0].set_ylabel('USD millions');ax[0].legend(frameon=False)
 ax[1].plot(x,h.adjusted_ebitda,'o-',label='Adjusted EBITDA',color=TEAL);ax[1].plot(x,h.fcf,'o-',label='FCF after PPE and mine development',color=RED)
 ax[1].set_xticks(x,h.index);ax[1].axhline(0,color=NAVY,lw=.6);ax[1].set_title('Cash conversion is the central valuation test');ax[1].legend(frameon=False,fontsize=8)
 save(fig,OUT/'financial_trends.png')
 fig,ax=plt.subplots(figsize=(10,4.3))
 for tk,color in [('MTRN',TEAL),('SPY',NAVY),('IWM',GOLD),('ENTG',RED)]:
  p=price_history(tk).loc['2021-09-20':,'adj_close'];ax.plot(p.index,p/p.iloc[0]*100,label=tk,color=color)
 ax.set_title('Five-year total-return proxy: $100 at September 20, 2021');ax.set_ylabel('Dividend-adjusted index');ax.legend(frameon=False,ncol=4)
 save(fig,OUT/'relative_returns.png')
 p=pd.read_csv(D/'technicals.csv',index_col='date',parse_dates=True).loc['2025-09-18':]
 fig,ax=plt.subplots(2,1,figsize=(10,6),sharex=True,gridspec_kw={'height_ratios':[3,1]})
 for c,label,color in [('close','Close',NAVY),('sma50','50-day average',TEAL),('sma200','200-day average',GOLD)]: ax[0].plot(p.index,p[c],label=label,color=color)
 ax[0].fill_between(p.index,p.bb_lower,p.bb_upper,alpha=.08,color=TEAL);ax[0].set_title('Strong long-term trend; retreat from the August earnings peak');ax[0].set_ylabel('USD/share');ax[0].legend(frameon=False,ncol=3,fontsize=9)
 ax[1].plot(p.index,p.rsi14,color=TEAL);ax[1].axhline(70,color=RED,ls='--',lw=.8);ax[1].axhline(30,color=GOLD,ls='--',lw=.8);ax[1].set_ylabel('RSI 14');ax[1].set_ylim(0,100)
 save(fig,OUT/'price_action.png')
 fig,ax=plt.subplots(figsize=(10,3.5));vals=[190.001,87.446,30.741];labels=['Performance Materials','Electronic Materials','Precision Optics']
 ax.barh(labels[::-1],vals[::-1],color=[GOLD,TEAL,NAVY]);ax.set_xlabel('Q2 2026 value-added sales, USD millions');ax.set_title('Operating exposure differs from headline sales')
 for i,(v,m) in enumerate(zip(vals[::-1],[21.4,32.0,25.4])):ax.text(v+2,i,f'${v:.1f}m  |  adjusted EBITDA margin {m:.1f}%',va='center',fontsize=9)
 ax.set_xlim(0,330);save(fig,OUT/'segment_mix.png')
 a=pd.read_csv(D/'dcf_summary.csv');b=pd.read_csv(D/'fundamental_scenarios.csv')
 fig,ax=plt.subplots(figsize=(9,4));x=np.arange(3);ax.bar(x-.18,a.per_share,.36,label='DCF: intrinsic-value scenarios',color=TEAL);ax.bar(x+.18,b.price,.36,label='12-month earnings-multiple scenarios',color=GOLD)
 ax.axhline(251.53,color=RED,ls='--',label='September 18 price: $251.53');ax.set_xticks(x,a.scenario);ax.set_ylabel('USD/share');ax.set_title('Valuation depends heavily on continued premium multiples');ax.legend(frameon=False,fontsize=8)
 save(fig,OUT/'valuation_scenarios.png')
 fig,ax=plt.subplots(figsize=(9,3.5));data=pd.read_csv(D/'dcf_sensitivity.csv',index_col=0);im=ax.imshow(data.values,cmap='YlGnBu',aspect='auto')
 ax.set_xticks(range(5),[f'{float(x):.1%}' for x in data.columns]);ax.set_yticks(range(5),[f'{x:.1%}' for x in data.index]);ax.set_xlabel('Terminal growth');ax.set_ylabel('WACC');ax.set_title('Base DCF sensitivity, USD/share')
 for i in range(5):
  for j in range(5):ax.text(j,i,f'${data.iloc[i,j]:.0f}',ha='center',va='center',color='white' if data.iloc[i,j]>130 else NAVY)
 ax.grid(False);save(fig,OUT/'dcf_sensitivity.png')
if __name__=='__main__':build()
