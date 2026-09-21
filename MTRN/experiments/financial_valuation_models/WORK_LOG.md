# Work log

## Continuation, 2026-09-21 — complete

Resumed after the previous run stopped mid-file at `code/report.py`, where `make_figures()`
was finished but no HTML builder, `build()` or entry point existed and `figures/` and `final/`
were empty. `score.py` and `documentation.py` had also been edited after their last execution,
so their outputs were stale.

Audited the existing pipeline before extending it. Verified as correct and reused unchanged:
point-in-time SEC selection (next session after filing; later restatements cannot revise an
earlier snapshot), target alignment (hand-checked against raw adjusted closes to 1e-15),
one-session delays on external series, training-only preprocessing and tuning with label
purging, the expanding-window outer design, and the separation of the return and variance
tasks. A re-run reproduced the archived forecasts bit for bit.

Corrected six defects, recorded with their effects in `CONTINUATION_AUDIT.json`: prefix-based
block removal leaking `pe_pct_change` into the valuation-free model; three accounting-extraction
gaps that voided central variables for Entegris, Carpenter and Materion; per-issuer alias
columns duplicating named series inside one model; and an unavailable yield change being
counted as a falling-rate regime.

Added the protocol requirements that were absent: the zero benchmark, the excess-return
secondary target, the protocol-order ablation ladder beside the market-first one, the frozen
sixteen-contrast family with Holm adjustment, fallback-excluded matched scores, limited-sample
labelling for dynamic fits, variance inflation factors, trailing valuation percentiles, the
full section-7 exposure schema, and the Elastic Net mixing grid.

Completed the report: eighteen figures under one style registry, numbered by the order they
appear in the document, each introduced and discussed in the text; the standalone HTML in the
section-16 order with all eight experiments following the question → setup → variables →
criteria → results → figures → interpretation → conclusion → limitations sequence.

Added `validate.py` (fail-closed, 42 checks), extended `tests/test_methods.py` to 16 method
tests, pinned `requirements.txt`, wrote `README.md` and the single offline rebuild command
`run_experiments.py`.

**Findings.** No factor block, transformation, added lag or ARMA error process reliably improved
on the expanding historical mean for next-month returns. The variance task does improve on its
persistence benchmark, mainly through pooling and persistence rather than added external
volatility inputs. Estimates on the return task are imprecise rather than measured zeros; the
binding constraint is 44 monthly outcomes per issuer.

**Untested and recorded as such.** Archived analyst consensus (so forward P/E, earnings surprise
and estimate revisions could not be tested at all), a reconciled EV/ROIC claims bridge,
historical index membership, historical bid-ask spreads, tungsten and molybdenum price history,
and formal modelling of ELMT. The high-yield credit spread archive begins in 2023 and fails the
training coverage gate.

Original files remain immutable: all preserved hashes verify. Environment
`/tmp/mtrn-research-venv`, Python 3.12, seed 20260918, deterministic.
