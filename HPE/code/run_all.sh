#!/usr/bin/env bash
# Reproduce the HPE analysis from the cached raw data in data/ and report/.
#   bash code/run_all.sh              # analysis only (no network)
#   FETCH=1 bash code/run_all.sh      # first refresh raw data with the reusable fetcher
# Requires the venv at HPE/.venv (see code/requirements.txt). For SEC requests set
# SEC_USER_AGENT="Name email@domain".
set -euo pipefail
cd "$(dirname "$0")"
PY=../.venv/bin/python

if [[ "${FETCH:-0}" == "1" ]]; then
  echo "== 0. Retrieval (reusable, ticker-agnostic)"
  $PY fetch_company_data.py --ticker HPE --peers DELL,SMCI,CSCO,ANET,NTAP,P,DLR,KEEL,IREN,CRWV,NBIS,NVDA --benchmarks SPY,XLK,BTC-USD \
      --xbrl-extra MSFT,GOOGL,AMZN,META,ORCL,MU --since 2015-10-01 --end 2026-09-11 --all
fi

echo "== 1. Financial statements";      $PY parse_statements.py
echo "== 2. Financial analysis";        $PY financial_analysis.py
echo "== 3. Segments";                  $PY segment_analysis.py
echo "== 4. Capital structure";         $PY capital_structure.py
echo "== 5. Stock and technicals";      $PY stock_analysis.py
echo "== 6. Event reactions";           $PY event_analysis.py
echo "== 7. Insider transactions";      $PY insider_ownership.py
echo "== 8. Peers";                     $PY peers.py
echo "== 9. Macro and industry";        $PY macro_industry_analysis.py
echo "== 10. Statistics";               $PY statistical_analysis.py
echo "== 11. Valuation";                $PY valuation.py
echo "== 12. Practitioner Q&A 1";       $PY security_exposure_analysis.py
echo "== 13. Practitioner Q&A 2";       $PY business_model_analysis.py
echo "done: outputs in data/processed_data"
