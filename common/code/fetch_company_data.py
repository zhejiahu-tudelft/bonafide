"""Reusable, ticker-agnostic data retrieval for fundamental equity research.

Downloads raw inputs only (cached and re-runnable); every calculation lives in the analysis scripts.
Files land in the standard project layout (report/…, data/…) and each source is appended to
report/source_log.csv.

Examples
  # HPE project (as used for this repository)
  python fetch_company_data.py --ticker HPE --peers DELL,SMCI,CSCO,ANET,NTAP,P --benchmarks SPY,XLK \
      --xbrl-extra MSFT,GOOGL,AMZN,META,ORCL,MU --since 2015-10-01 --end 2026-09-11 --all
  # another company, market data and XBRL only, into a new project folder
  python fetch_company_data.py --ticker NTAP --peers PSTG,DELL --xbrl --prices --end 2026-09-11 --out ../../NTAP

Sections (combine flags, or use --all)
  --sec        SEC filings for --ticker (forms in --forms, filed on/after --since); 8-K Item 2.02
               earnings releases saved from Exhibit 99.1
  --form4      insider Form 4 XML (filed within --form4-years of --end)
  --xbrl       XBRL company facts for ticker, peers and --xbrl-extra (macro / industry proxies)
  --prices     daily OHLCV from Yahoo Finance (split- and spin-off-adjusted; dividend-adjusted close)
               for ticker, peers and benchmarks, plus a Nasdaq close series for cross-checking
  --estimates  Yahoo Finance consensus estimates, price targets, rating changes and holders (yfinance)
  --rates      10-year Treasury and 3-month bill (FRED, Yahoo fallback) and the US dollar index
  --damodaran  Damodaran datasets: implied ERP, industry betas, country risk, cost of capital, FCFF Ginzu

The SEC fair-access policy requires a descriptive User-Agent: export SEC_USER_AGENT="Name email@domain".
Company IR decks, transcripts and industry research are not crawled; see README "Reusing for another ticker"
for the search keywords and sources used to collect them.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import os
import re
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

SEC_HEADERS = {"User-Agent": os.environ.get("SEC_USER_AGENT", "Research research-contact@example.com"),
               "Accept-Encoding": "gzip, deflate"}
BROWSER = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
DEFAULT_FORMS = "10-K,10-Q,8-K,DEF 14A,424B2,424B5,FWP,S-8,S-3ASR,SC 13D,SC 13G"
NY = ZoneInfo("America/New_York")
SESSION = requests.Session()
LOG_FIELDS = ["id", "category", "source", "title", "publisher", "pub_date", "retrieved", "url", "local_path",
              "forecast_period", "key_data", "relevance", "source_type"]
DAMODARAN = {
    "pc/datasets/histimpl.xls": "Implied equity risk premiums, US (history)",
    "pc/datasets/betas.xls": "Betas by sector (US)",
    "pc/datasets/ctryprem.xlsx": "Country default spreads and risk premiums",
    "pc/datasets/wacc.xls": "Cost of capital by sector (US)",
    "pc/fcffsimpleginzu.xlsx": "FCFF simple Ginzu valuation spreadsheet",
}


# ------------------------------------------------------------------------------------------ project + http
class Project:
    def __init__(self, root: Path, refresh: bool):
        self.root, self.refresh = root.resolve(), refresh
        self.fin = self.root / "data" / "financial_data"
        self.mkt = self.root / "data" / "market_data"
        self.filings = self.root / "report" / "company_filings"
        self.earnings = self.root / "report" / "earnings_materials"
        self.other = self.root / "report" / "other_evidence"
        self.log = self.root / "report" / "source_log.csv"
        for p in (self.fin, self.mkt, self.filings, self.earnings, self.other):
            p.mkdir(parents=True, exist_ok=True)

    def log_source(self, category, title, publisher, url, path=None, pub_date="", source_type="primary"):
        rows = list(csv.DictReader(self.log.open(encoding="utf-8"))) if self.log.exists() else []
        local = str(Path(path).resolve().relative_to(self.root)) if path else ""
        row = dict(category=category, source=publisher, title=title, publisher=publisher, pub_date=pub_date,
                   retrieved=dt.date.today().isoformat(), url=url, local_path=local, forecast_period="", key_data="",
                   relevance="", source_type=source_type)
        for existing in rows:
            if existing["url"] == url and existing["title"] == title:
                existing.update({k: v for k, v in row.items() if v})
                break
        else:
            row["id"] = f"S{len(rows) + 1:03d}"
            rows.append(row)
        with self.log.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=LOG_FIELDS, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)


def get(url: str, headers: dict, sleep: float = 0.15, retries: int = 3, timeout: int = 60) -> requests.Response | None:
    for attempt in range(retries):
        try:
            r = SESSION.get(url, headers=headers, timeout=timeout)
            time.sleep(sleep)
            if r.status_code == 200:
                return r
            if r.status_code in (403, 404, 410):
                return None
        except requests.RequestException:
            pass
        time.sleep(1.5 * (attempt + 1))
    return None


def download(url: str, dest: Path, headers: dict, refresh: bool, min_bytes: int = 500) -> Path | None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size >= min_bytes and not refresh:
        return dest
    r = get(url, headers)
    if r is None or len(r.content) < min_bytes:
        return None
    dest.write_bytes(r.content)
    return dest


def cached_json(url: str, cache: Path, headers: dict, refresh: bool) -> dict | None:
    if cache.exists() and not refresh:
        return json.loads(cache.read_text())
    r = get(url, headers)
    if r is None:
        return None
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(r.text)
    return r.json()


# ------------------------------------------------------------------------------------------ SEC EDGAR
def cik_map(proj: Project) -> dict[str, str]:
    data = cached_json("https://www.sec.gov/files/company_tickers.json", proj.fin / "sec_company_tickers.json", SEC_HEADERS, proj.refresh)
    return {v["ticker"].upper(): f"{int(v['cik_str']):010d}" for v in data.values()}


def submissions(proj: Project, ticker: str, cik: str) -> tuple[list[dict], str]:
    sub = cached_json(f"https://data.sec.gov/submissions/CIK{cik}.json", proj.fin / f"sec_submissions_{ticker}.json", SEC_HEADERS, True)
    pages = [sub["filings"]["recent"]]
    for extra in sub["filings"].get("files", []):
        pages.append(cached_json(f"https://data.sec.gov/submissions/{extra['name']}", proj.fin / f"sec_{extra['name']}", SEC_HEADERS, proj.refresh))
    keys = ("accessionNumber", "filingDate", "reportDate", "form", "items", "primaryDocument")
    rows = [{k: p[k][i] for k in keys} for p in pages for i in range(len(p["accessionNumber"]))]
    return sorted(rows, key=lambda r: r["filingDate"], reverse=True), sub.get("fiscalYearEnd") or "1231"


def fiscal_label(report_date: str, fye: str) -> tuple[int, int]:
    """Fiscal year and quarter for a period-end date given the fiscal-year-end month-day (e.g. '1031')."""
    d = dt.date.fromisoformat(report_date)
    fye_month = int(fye[:2])
    fy = d.year if d.month <= fye_month else d.year + 1
    quarter = ((d.month - fye_month - 1) % 12) // 3 + 1
    return fy, quarter


def exhibit_991(cik_int: int, acc: str) -> str | None:
    idx = get(f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc.replace('-', '')}/index.json", SEC_HEADERS)
    if idx is None:
        return None
    names = [it["name"] for it in idx.json()["directory"]["item"]]
    hits = [n for n in names if re.search(r"ex[-_]?99[-_.]?0?1", n, re.I) and n.lower().endswith((".htm", ".html"))]
    return sorted(hits, key=len)[0] if hits else None


def fetch_sec(proj: Project, ticker: str, cik: str, forms: set[str], since: str, form4_since: str | None) -> dict:
    cik_int = int(cik)
    rows, fye = submissions(proj, ticker, cik)
    counts: dict[str, int] = {}
    base = f"https://www.sec.gov/Archives/edgar/data/{cik_int}"

    def save(f, dest, category, title, doc=None, min_bytes=800):
        url = f"{base}/{f['accessionNumber'].replace('-', '')}/{doc or f['primaryDocument']}"
        path = download(url, dest, SEC_HEADERS, proj.refresh, min_bytes)
        if path:
            proj.log_source(category, title, f"SEC EDGAR / {ticker}", url, path, pub_date=f["filingDate"])
            counts[f["form"]] = counts.get(f["form"], 0) + 1
        return path

    for f in rows:
        form, fd, rd, items, acc = f["form"], f["filingDate"], f["reportDate"], f["items"] or "", f["accessionNumber"]
        normalized = form.upper().replace("SCHEDULE ", "SC ").replace("/A", "")
        if form == "4":
            if form4_since and fd >= form4_since:
                raw = f["primaryDocument"].split("/")[-1]
                if download(f"{base}/{acc.replace('-', '')}/{raw}", proj.fin / "form4" / f"{fd}_{acc}.xml", SEC_HEADERS, False, 300):
                    counts["4"] = counts.get("4", 0) + 1
            continue
        if fd < since or normalized not in forms:
            continue
        if form == "10-K":
            fy, _ = fiscal_label(rd, fye)
            save(f, proj.filings / "10-K" / f"{ticker}_10-K_FY{fy}_filed{fd}.htm", "company_filings", f"{ticker} Form 10-K FY{fy} (period ended {rd})", min_bytes=2000)
        elif form == "10-Q":
            fy, q = fiscal_label(rd, fye)
            save(f, proj.filings / "10-Q" / f"{ticker}_10-Q_FY{fy}Q{q}_{rd}.htm", "company_filings", f"{ticker} Form 10-Q FY{fy}Q{q} (period ended {rd})", min_bytes=2000)
        elif form == "8-K":
            ex = exhibit_991(cik_int, acc)
            if "2.02" in items and ex:
                save(f, proj.earnings / "sec_8k_ex99" / f"{ticker}_8-K_Ex99-1_earnings_{fd}.htm", "earnings_materials",
                     f"{ticker} earnings release (8-K Ex-99.1) filed {fd}", doc=ex, min_bytes=2000)
            else:
                tag = items.replace(",", "_").replace(".", "")
                save(f, proj.filings / "8-K" / f"{ticker}_8-K_{fd}_items{tag}.htm", "company_filings", f"{ticker} Form 8-K filed {fd} (items {items})")
                if ex:
                    save(f, proj.filings / "8-K" / f"{ticker}_8-K_{fd}_ex99-1.htm", "company_filings", f"{ticker} 8-K Ex-99.1 filed {fd} (items {items})", doc=ex)
        elif form == "DEF 14A":
            save(f, proj.filings / "proxy" / f"{ticker}_DEF14A_{fd}.htm", "company_filings", f"{ticker} proxy statement filed {fd}", min_bytes=2000)
        elif normalized in {"424B2", "424B5", "FWP"}:
            save(f, proj.filings / "financing" / f"{ticker}_{form}_{fd}_{acc[-6:]}.htm", "company_filings", f"{ticker} {form} prospectus/term sheet filed {fd}")
        elif normalized in {"S-8", "S-3ASR", "S-4"}:
            save(f, proj.filings / "registration" / f"{ticker}_{form}_{fd}.htm", "company_filings", f"{ticker} {form} registration statement filed {fd}")
        elif normalized.startswith(("SC 13D", "SC 13G")):
            safe = form.replace(" ", "").replace("/", "-")
            save(f, proj.other / "ownership" / f"{ticker}_{safe}_{fd}_{acc[-6:]}.htm", "other_evidence", f"{form} beneficial ownership filing on {ticker}, filed {fd}", min_bytes=500)
    return counts


def fetch_xbrl(proj: Project, tickers: list[str], extra: list[str], ciks: dict[str, str]) -> list[str]:
    done = []
    for t in tickers + extra:
        cik = ciks.get(t.upper())
        if not cik:
            print(f"  XBRL: no CIK for {t}")
            continue
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        dest = (proj.fin / "industry" / f"companyfacts_{cik}.json") if t in extra else (proj.fin / f"companyfacts_{t}.json")
        if cached_json(url, dest, SEC_HEADERS, proj.refresh) is not None:
            proj.log_source("financial_data", f"SEC XBRL company facts: {t}", "SEC EDGAR", url, dest)
            done.append(t)
    return done


# ------------------------------------------------------------------------------------------ market data
def yahoo_chart(symbol: str, start: str, end: str) -> tuple[pd.DataFrame, dict]:
    p1 = int(dt.datetime.fromisoformat(start).replace(tzinfo=NY).timestamp())
    p2 = int((dt.datetime.fromisoformat(end).replace(tzinfo=NY) + dt.timedelta(days=1)).timestamp())
    url = (f"https://query2.finance.yahoo.com/v8/finance/chart/{requests.utils.quote(symbol)}?period1={p1}&period2={p2}"
           f"&interval=1d&events=div%2Csplit")
    r = get(url, BROWSER, sleep=0.5)
    if r is None:
        raise RuntimeError(f"Yahoo chart request failed for {symbol}")
    res = r.json()["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    adj = res["indicators"].get("adjclose", [{}])[0].get("adjclose", q["close"])
    df = pd.DataFrame({"date": [dt.datetime.fromtimestamp(t, NY).date() for t in res["timestamp"]], "open": q["open"],
                       "high": q["high"], "low": q["low"], "close": q["close"], "adj_close": adj, "volume": q["volume"]})
    df = df.dropna(subset=["close"])
    return df[df["date"] <= dt.date.fromisoformat(end)].drop_duplicates("date", keep="last"), res.get("events", {})


def fetch_prices(proj: Project, ticker: str, others: list[str], start: str, end: str) -> None:
    for t in [ticker, *others]:
        path = proj.mkt / f"{t}_daily.csv"
        if path.exists() and not proj.refresh:
            continue
        df, events = yahoo_chart(t, start, end)
        df.to_csv(path, index=False)
        proj.log_source("market_data", f"{t} daily OHLCV (split/spin-off adjusted) {df.date.min()}–{df.date.max()}",
                        "Yahoo Finance chart API", f"https://finance.yahoo.com/quote/{t}/history", path, source_type="secondary (market data)")
        if t == ticker:
            for kind in ("dividends", "splits"):
                ev = pd.DataFrame(events.get(kind, {}).values())
                if not ev.empty:
                    ev["date"] = [dt.datetime.fromtimestamp(x, NY).date() for x in ev["date"]]
                    ev.sort_values("date").to_csv(proj.mkt / f"{t}_{kind}.csv", index=False)
    url = (f"https://api.nasdaq.com/api/quote/{ticker}/historical?assetclass=stocks&fromdate={start}&limit=9999&todate={end}")
    r = get(url, BROWSER)
    if r is not None and r.json().get("data"):
        rows = r.json()["data"]["tradesTable"]["rows"]
        num = lambda s: float(s.replace("$", "").replace(",", ""))
        nas = pd.DataFrame({"date": [dt.datetime.strptime(x["date"], "%m/%d/%Y").date() for x in rows],
                            "close": [num(x["close"]) for x in rows], "volume": [num(x["volume"]) for x in rows]}).sort_values("date")
        nas.to_csv(proj.mkt / f"{ticker}_nasdaq_daily.csv", index=False)
        proj.log_source("market_data", f"{ticker} daily close/volume (cross-check)", "Nasdaq historical quotes API",
                        f"https://www.nasdaq.com/market-activity/stocks/{ticker.lower()}/historical", proj.mkt / f"{ticker}_nasdaq_daily.csv",
                        source_type="secondary (market data)")


def fetch_estimates(proj: Project, tickers: list[str]) -> None:
    import yfinance as yf
    out = proj.mkt / "yahoo"
    out.mkdir(exist_ok=True)
    for t in tickers:
        tk = yf.Ticker(t)
        for name in ("info", "analyst_price_targets", "earnings_estimate", "revenue_estimate", "eps_trend",
                     "upgrades_downgrades", "institutional_holders", "major_holders"):
            try:
                obj = getattr(tk, name)
            except Exception as exc:  # schema or network changes: skip the item, keep going
                print(f"  {t} {name}: unavailable ({type(exc).__name__})")
                continue
            if obj is None or (hasattr(obj, "empty") and obj.empty):
                continue
            if isinstance(obj, pd.DataFrame):
                obj.to_csv(out / f"yahoo_{t}_{name}.csv")
            else:
                (out / f"yahoo_{t}_{name}.json").write_text(json.dumps(obj, indent=2, default=str))
        proj.log_source("market_data", f"{t} consensus estimates, targets, ratings and holders", "Yahoo Finance (yfinance)",
                        f"https://finance.yahoo.com/quote/{t}/analysis", out, source_type="secondary (market data)")


def fetch_rates(proj: Project, start: str, end: str) -> None:
    out = proj.mkt / "macro"
    out.mkdir(exist_ok=True)
    for name, symbol, label in (("DGS10", "^TNX", "10-year US Treasury yield (%)"), ("DTB3", "^IRX", "13-week US Treasury bill yield (%)"),
                                ("DXY", "DX-Y.NYB", "ICE US dollar index")):
        df, src = None, "FRED"
        if name != "DXY":
            try:
                r = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={name}", timeout=15)
                if r.status_code == 200:
                    df = pd.read_csv(io.StringIO(r.text))
                    df.columns = ["date", "value"]
            except requests.RequestException:
                df = None
        if df is None:
            px, _ = yahoo_chart(symbol, start, end)
            df, src = px[["date", "close"]].rename(columns={"close": "value"}), "Yahoo Finance"
        df.to_csv(out / f"{name}.csv", index=False)
        url = f"https://fred.stlouisfed.org/series/{name}" if src == "FRED" else f"https://finance.yahoo.com/quote/{symbol}"
        proj.log_source("macro_research", f"{label} ({src})", src, url, out / f"{name}.csv", pub_date=str(df["date"].iloc[-1]),
                        source_type="secondary (market data)")


def fetch_damodaran(proj: Project) -> None:
    for rel, title in DAMODARAN.items():
        url = f"https://pages.stern.nyu.edu/~adamodar/{rel}"
        path = download(url, proj.other / "damodaran" / rel.split("/")[-1], BROWSER, proj.refresh, 5000)
        proj.log_source("other_evidence", f"Damodaran: {title}", "Aswath Damodaran, NYU Stern", url, path, source_type="secondary (academic dataset)")


# ------------------------------------------------------------------------------------------ CLI
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--peers", default="")
    ap.add_argument("--benchmarks", default="SPY")
    ap.add_argument("--xbrl-extra", default="", help="extra tickers for XBRL facts (e.g. demand or input-cost proxies)")
    ap.add_argument("--forms", default=DEFAULT_FORMS)
    ap.add_argument("--since", default="2015-01-01", help="earliest filing date and price start")
    ap.add_argument("--end", default=dt.date.today().isoformat(), help="valuation / last price date")
    ap.add_argument("--form4-years", type=float, default=2.0)
    ap.add_argument("--out", default=None, help="project root folder (default: cwd/TICKER)")
    ap.add_argument("--refresh", action="store_true")
    for flag in ("sec", "form4", "xbrl", "prices", "estimates", "rates", "damodaran", "all"):
        ap.add_argument(f"--{flag}", action="store_true")
    a = ap.parse_args()

    proj = Project(Path(a.out) if a.out else Path.cwd() / a.ticker.upper(), a.refresh)
    ticker = a.ticker.upper()
    peers = [p.strip().upper() for p in a.peers.split(",") if p.strip()]
    benches = [b.strip().upper() for b in a.benchmarks.split(",") if b.strip()]
    extra = [x.strip().upper() for x in a.xbrl_extra.split(",") if x.strip()]
    run = lambda flag: a.all or getattr(a, flag)

    if run("sec") or run("form4") or run("xbrl"):
        ciks = cik_map(proj)
        if ticker not in ciks:
            raise SystemExit(f"{ticker} not found in the SEC ticker list")
    if run("sec") or run("form4"):
        forms = {f.strip().upper() for f in a.forms.split(",")} if run("sec") else set()
        end = dt.date.fromisoformat(a.end)
        f4 = (end - dt.timedelta(days=int(365 * a.form4_years))).isoformat() if run("form4") else None
        print("SEC filings:", fetch_sec(proj, ticker, ciks[ticker], forms, a.since, f4))
    if run("xbrl"):
        print("XBRL facts:", fetch_xbrl(proj, [ticker, *peers], extra, ciks))
    if run("prices"):
        fetch_prices(proj, ticker, peers + benches, a.since, a.end)
        print("Prices saved for", [ticker, *peers, *benches])
    if run("estimates"):
        fetch_estimates(proj, [ticker, *peers])
    if run("rates"):
        fetch_rates(proj, a.since, a.end)
    if run("damodaran"):
        fetch_damodaran(proj)
    print("done →", proj.root)


if __name__ == "__main__":
    main()
