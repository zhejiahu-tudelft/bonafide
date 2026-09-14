"""Shared paths and constants for the HPE equity-research analysis scripts.

Every script in /code imports from here so that folder locations, the valuation date and the peer
set are defined exactly once. Data retrieval lives in fetch_company_data.py (ticker-agnostic).
"""
from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
DATA = ROOT / "data"
FIN_DATA = DATA / "financial_data"
MKT_DATA = DATA / "market_data"
PROC = DATA / "processed_data"
CHARTS = PROC / "charts"
EXCEL = ROOT / "excel"
REPORT = ROOT / "report"
FILINGS = REPORT / "company_filings"
EARNINGS = REPORT / "earnings_materials"
INDUSTRY = REPORT / "industry_research"
MACRO = REPORT / "macro_research"
COMPETITORS = REPORT / "competitor_research"
OTHER = REPORT / "other_evidence"
FINAL = ROOT / "final"
TEMPLATE = ROOT.parent / "Template.pptx"
SOURCE_LOG = REPORT / "source_log.csv"

for _p in (FIN_DATA, MKT_DATA, PROC, CHARTS, EXCEL, FILINGS, EARNINGS, INDUSTRY, MACRO, COMPETITORS, OTHER, FINAL):
    _p.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------- constants
TICKER = "HPE"
COMPANY = "Hewlett Packard Enterprise Company"
CIK = "0001645590"
FISCAL_YEAR_END = "10-31"
AS_OF_DATE = "2026-09-14"          # report as-of date
VALUATION_DATE = "2026-09-11"      # last completed trading session used for pricing
LISTING_DATE = "2015-11-02"        # regular-way trading after separation from HP Co.
WHEN_ISSUED_DATE = "2015-10-19"

# Pure Storage renamed itself Everpure, Inc. (ticker P, same CIK 1474432).
PEERS = ["DELL", "SMCI", "CSCO", "ANET", "NTAP", "P"]
BENCHMARKS = ["SPY", "XLK"]
PEER_NAMES = {"HPE": "HPE", "DELL": "Dell", "SMCI": "Supermicro", "CSCO": "Cisco", "ANET": "Arista",
              "NTAP": "NetApp", "P": "Everpure (ex-Pure Storage)", "SPY": "S&P 500 (SPY)", "XLK": "Tech sector (XLK)"}
