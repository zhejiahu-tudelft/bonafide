"""Offline audit of the saved Cboe snapshot; liquidity gates strategy construction."""
from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from common.code.options_tools import normalize_cboe,validate_chain
from common.code.options_summary_tools import summarize
ROOT=Path(__file__).resolve().parents[1]
def build():
 raw=json.loads((ROOT/'data/options_data/cboe_raw.json').read_text())
 c=validate_chain(normalize_cboe(raw),'2026-09-18')
 c['liquidity_screen']=c.usable
 c['usable']=c.usable & c.trade_age_days.between(0,5) & (c.volume>=1)
 c.to_csv(ROOT/'data/processed_data/options_audit.csv',index=False)
 s=summarize(c);s.to_csv(ROOT/'data/processed_data/options_summary.csv',index=False)
 c[(c.strike.between(230,280))&(c.days_to_expiration>0)].to_csv(ROOT/'data/processed_data/options_near_spot.csv',index=False)
 summary={'file_timestamp':raw['timestamp'],'file_timezone':'unspecified by vendor',
  'underlying_last_trade':raw['data']['last_trade_time'],'spot':raw['data']['current_price'],
  'vendor_iv30_pct':raw['data']['iv30'],'total_contracts':len(c),
  'unexpired_contracts':int((c.days_to_expiration>0).sum()),
  'usable_contracts':int(c.usable.sum()),'liquidity_only_pass':int(c.liquidity_screen.sum()),
  'unexpired_volume':float(c.loc[c.days_to_expiration>0,'volume'].sum()),
  'unexpired_oi':float(c.loc[c.days_to_expiration>0,'open_interest'].sum()),
  'conclusion':'Reliable options analysis could not be performed because the available option-chain data was insufficient or illiquid.',
  'screen':'Positive bid; ask >= bid; spread <= 30% of midpoint; OI >= 20; nonexpired; IV > 0 and < 500%; underlying session date aligned; most recent trade <= 5 calendar days old; at least one contract traded in snapshot.'}
 (ROOT/'data/processed_data/options_conclusion.json').write_text(json.dumps(summary,indent=2))
 print(json.dumps(summary,indent=2))
if __name__=='__main__': build()
