#!/usr/bin/env bash
# Annotated experiment and valuation pipeline.
#
# Runs every numbered experiment in report order and, for each one, prints what it tests, the
# variables by role, the data sources, the specification, the results, whether the main result
# clears its predefined significance threshold, and what it means for the valuation. Ends with a
# summary of which stages completed and which results were statistically significant.
#
#   bash code/run_experiments.sh                 # run the full pipeline from cached raw data
#   bash code/run_experiments.sh --cached        # narrate existing outputs without re-running
#   bash code/run_experiments.sh --only 1,5,V    # a subset (ids 1-11, V valuation, E evaluation)
#   bash code/run_experiments.sh --from 8        # from experiment 8 onwards
#   bash code/run_experiments.sh --fail-fast     # stop at the first failing stage
#   bash code/run_experiments.sh --verbose       # also show each analysis script's own output
#   bash code/run_experiments.sh --skip-prerequisites
#
# Requires the venv at HPE/.venv (see code/requirements.txt) and the cached data in data/ and
# report/. No network access. Override the interpreter with PY=/path/to/python.
set -uo pipefail
SELF=$(readlink -f "$0")          # resolved before the cd below, so --help can read this header
cd "$(dirname "$0")"

PY=${PY:-../.venv/bin/python}
REPORTER=experiment_report.py
ALL_IDS=(1 2 3 4 5 6 7 8 9 10 11 V E)
PREREQS=(parse_statements.py financial_analysis.py segment_analysis.py capital_structure.py stock_analysis.py
         event_analysis.py insider_ownership.py peers.py macro_industry_analysis.py)

usage() { awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$SELF"; }

script_for() {
  case "$1" in
    1|2|3|4|5|6) echo statistical_analysis.py ;;
    7)           echo security_exposure_analysis.py ;;
    8|9|10)      echo business_model_analysis.py ;;
    11)          echo greenlake_analysis.py ;;
    V)           echo valuation.py ;;
    E)           echo earnings_analysis.py ;;
  esac
}

# ------------------------------------------------------------------------------------ arguments
CACHED=0; FAIL_FAST=0; VERBOSE=0; SKIP_PREREQ=0; SELECTED=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --cached)              CACHED=1; SKIP_PREREQ=1 ;;
    --skip-prerequisites)  SKIP_PREREQ=1 ;;
    --fail-fast)           FAIL_FAST=1 ;;
    --verbose)             VERBOSE=1 ;;
    --only)                IFS=',' read -r -a SELECTED <<< "${2:?--only needs a comma-separated list of ids}"; shift ;;
    --from)                from_id="${2:?--from needs an id}"; shift
                           start=-1
                           for i in "${!ALL_IDS[@]}"; do [[ "${ALL_IDS[$i]}" == "${from_id^^}" ]] && start=$i; done
                           [[ $start -lt 0 ]] && { echo "unknown id for --from: $from_id" >&2; exit 2; }
                           SELECTED=("${ALL_IDS[@]:$start}") ;;
    -h|--help)             usage; exit 0 ;;
    *)                     echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done
[[ ${#SELECTED[@]} -eq 0 ]] && SELECTED=("${ALL_IDS[@]}")

RUN_IDS=()
for id in "${SELECTED[@]}"; do
  up="${id^^}"; known=0
  for known_id in "${ALL_IDS[@]}"; do [[ "$known_id" == "$up" ]] && known=1; done
  [[ $known -eq 1 ]] || { echo "unknown experiment id: $id (expected one of ${ALL_IDS[*]})" >&2; exit 2; }
  RUN_IDS+=("$up")
done

# ---------------------------------------------------------------------------- environment checks
[[ -x "$PY" ]] || { echo "python not found at $PY — create the venv with: uv venv .venv && uv pip install --python .venv/bin/python -r code/requirements.txt" >&2; exit 2; }
[[ -f "$REPORTER" ]] || { echo "missing code/$REPORTER" >&2; exit 2; }
[[ -d ../data/financial_data ]] || { echo "missing data/financial_data — fetch the raw data first: FETCH=1 bash code/run_all.sh" >&2; exit 2; }

TS=$(date -u +%Y%m%d_%H%M%S)
RUN_DIR=../data/processed_data/experiments/run_$TS
mkdir -p "$RUN_DIR/scripts" || exit 2
LOG=$RUN_DIR/pipeline.log
STATUS=$RUN_DIR/status.tsv
PREREQ_FAILED=$RUN_DIR/prerequisite_failures
: > "$STATUS"

declare -A SCRIPT_STATUS SCRIPT_SECONDS SCRIPT_REPORTED
RUN_STATUS=""; NOTE=""

hr() { printf '%.0s─' {1..98}; echo; }

# Runs one analysis script at most once per invocation; sets RUN_STATUS to ok, failed or cached.
run_script() {
  local script=$1 t0 t1 rc
  if [[ -n "${SCRIPT_STATUS[$script]:-}" ]]; then RUN_STATUS=${SCRIPT_STATUS[$script]}; return; fi
  if [[ $CACHED -eq 1 ]]; then
    SCRIPT_STATUS[$script]=cached; SCRIPT_SECONDS[$script]=0; RUN_STATUS=cached; return
  fi
  t0=$(date +%s%N)
  if [[ $VERBOSE -eq 1 ]]; then
    "$PY" "$script" 2>&1 | tee "$RUN_DIR/scripts/${script%.py}.log" | sed 's/^/    | /'
    rc=${PIPESTATUS[0]}
  else
    "$PY" "$script" > "$RUN_DIR/scripts/${script%.py}.log" 2>&1
    rc=$?
  fi
  t1=$(date +%s%N)
  SCRIPT_SECONDS[$script]=$(awk -v a="$t0" -v b="$t1" 'BEGIN{printf "%.1f", (b-a)/1e9}')
  [[ $rc -eq 0 ]] && SCRIPT_STATUS[$script]=ok || SCRIPT_STATUS[$script]=failed
  RUN_STATUS=${SCRIPT_STATUS[$script]}
}

# Sets NOTE to "ok · 48.3s", or adds "already run in this pipeline" when an earlier experiment ran it.
# Assigns rather than echoes: a command substitution would run in a subshell and lose SCRIPT_REPORTED.
run_note() {
  local script=$1
  if [[ $CACHED -eq 1 ]]; then NOTE="cached, existing outputs"; return; fi
  NOTE="${SCRIPT_STATUS[$script]} · ${SCRIPT_SECONDS[$script]}s"
  if [[ -n "${SCRIPT_REPORTED[$script]:-}" ]]; then
    NOTE="$NOTE, already run in this pipeline"
  else
    SCRIPT_REPORTED[$script]=1
  fi
}

print_failure() {
  local script=$1
  echo "  FAILED · $script exited non-zero after ${SCRIPT_SECONDS[$script]}s. Last lines of its output:"
  tail -n 20 "$RUN_DIR/scripts/${script%.py}.log" | sed 's/^/    | /'
  echo "  full output: ${RUN_DIR#../}/scripts/${script%.py}.log"
}

main() {
  echo "HPE EXPERIMENT AND VALUATION PIPELINE"
  hr
  printf '  %-16s%s\n' "Started" "$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
  printf '  %-16s%s\n' "Interpreter" "$("$PY" -V 2>&1) at $PY"
  printf '  %-16s%s\n' "Mode" "$([[ $CACHED -eq 1 ]] && echo 'cached — narrating existing outputs' || echo 'full — every analysis re-run from cached raw data')"
  printf '  %-16s%s\n' "Stages" "${RUN_IDS[*]}"
  printf '  %-16s%s\n' "Threshold" "alpha = 0.05 unless an experiment states another rule; descriptive and deterministic stages print their decision rule instead"
  printf '  %-16s%s\n' "Run directory" "${RUN_DIR#../}"
  echo

  if [[ $SKIP_PREREQ -eq 0 ]]; then
    echo "PREREQUISITES · shared inputs the experiments below read"
    hr
    for script in "${PREREQS[@]}"; do
      run_script "$script"
      printf '  %-34s[%s · %ss]\n' "$script" "$RUN_STATUS" "${SCRIPT_SECONDS[$script]}"
      if [[ $RUN_STATUS == failed ]]; then
        echo "$script" >> "$PREREQ_FAILED"
        print_failure "$script"
        if [[ $FAIL_FAST -eq 1 ]]; then echo; echo "stopping: --fail-fast"; return; fi
      fi
    done
    echo
  fi

  for id in "${RUN_IDS[@]}"; do
    script=$(script_for "$id")
    "$PY" "$REPORTER" describe "$id"
    echo "RUN"
    run_script "$script"
    run_note "$script"
    printf '  %-44s [%s]\n' "$PY $script" "$NOTE"
    printf 'STAGE\t%s\t%s\t%s\n' "$id" "$RUN_STATUS" "${SCRIPT_SECONDS[$script]}" >> "$STATUS"
    if [[ $RUN_STATUS == failed ]]; then
      print_failure "$script"
      "$PY" "$REPORTER" report "$id" --status-file "$STATUS" --unavailable "$script exited non-zero"
      echo
      if [[ $FAIL_FAST -eq 1 ]]; then echo "stopping: --fail-fast"; return; fi
      continue
    fi
    "$PY" "$REPORTER" report "$id" --status-file "$STATUS"
    echo
  done
}

main 2>&1 | tee "$LOG"
main_rc=${PIPESTATUS[0]}

"$PY" "$REPORTER" summary --status-file "$STATUS" --log "${LOG#../}" --json-out "$RUN_DIR/experiment_summary.json" 2>&1 | tee -a "$LOG"
summary_rc=${PIPESTATUS[0]}
cp -f "$RUN_DIR/experiment_summary.json" ../data/processed_data/experiments/experiment_summary.json 2>/dev/null

if [[ -f $PREREQ_FAILED ]]; then
  echo "  Prerequisite scripts that failed: $(tr '\n' ' ' < "$PREREQ_FAILED")" | tee -a "$LOG"
fi
if [[ -f $PREREQ_FAILED ]] || grep -q $'\tfailed\t' "$STATUS" || [[ $summary_rc -ne 0 || $main_rc -ne 0 ]]; then
  exit 1
fi
exit 0
