"""Parse the primary financial statements out of HPE's 10-K / 10-Q filings.

Reads the text copies produced by extract_text.py and extracts the Consolidated Statements of
Earnings, Balance Sheets and Cash Flows into a long table. Keeping the filing's own row labels
means each figure in the analysis can be traced back to the statement it came from.

Output: data/financial_data/hpe_statements_long.csv
        columns: filing, form, statement, section, label, period, value ($ millions)

Usage: python parse_statements.py
"""
from __future__ import annotations

import re
import warnings

import pandas as pd
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from common import FIN_DATA, PROC, REPORT

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
TEXT = PROC / "text" / "company_filings"


def html_text(path) -> str:
    """Plain text of an EDGAR HTML filing with table rows kept on one line (cells joined by ' | ')."""
    soup = BeautifulSoup(path.read_bytes(), "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    for tr in soup.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        tr.replace_with(" | ".join(c for c in cells if c) + "\n")
    lines = (ln.strip() for ln in soup.get_text("\n").splitlines())
    return "\n".join(ln for ln in lines if ln)


def ensure_text() -> None:
    """Create or refresh text copies of the 10-K / 10-Q filings stored under report/company_filings."""
    for src in sorted((REPORT / "company_filings").glob("10-[KQ]/*.htm")):
        dest = TEXT / src.parent.name / f"{src.stem}.txt"
        if dest.exists() and dest.stat().st_mtime >= src.stat().st_mtime:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html_text(src), encoding="utf-8")
HEADINGS = {
    "IS": re.compile(r"^(Condensed )?Consolidated Statements of Earnings( \(Loss\))?( \(Unaudited\))?$"),
    "BS": re.compile(r"^(Condensed )?Consolidated Balance Sheets( \(Unaudited\))?$"),
    "CF": re.compile(r"^(Condensed )?Consolidated Statements of Cash Flows( \(Unaudited\))?$"),
}
DATE_TOKEN = re.compile(r"^((January|April|July|October) \d{1,2}, )?\d{4}$")
NUM = re.compile(r"^\(?\s*-?[\d,]+(\.\d+)?\s*\)?$")


def parse_number(tok: str) -> float | None:
    tok = tok.strip()
    if tok in {"—", "–", "-"}:
        return 0.0
    if not NUM.match(tok):
        return None
    neg = tok.startswith("(")
    val = float(re.sub(r"[(),\s]", "", tok))
    return -val if neg else val


def column_names(header_lines: list[str], dates: list[str]) -> list[str]:
    context = " ".join(header_lines).lower()
    if len(dates) == 4 and "three months" in context and "nine months" in context:
        return [f"3M_{dates[0][-4:]}", f"3M_{dates[1][-4:]}", f"9M_{dates[2][-4:]}", f"9M_{dates[3][-4:]}"]
    if len(dates) == 4 and "three months" in context and "six months" in context:
        return [f"3M_{dates[0][-4:]}", f"3M_{dates[1][-4:]}", f"6M_{dates[2][-4:]}", f"6M_{dates[3][-4:]}"]
    if "six months" in context:
        return [f"6M_{d[-4:]}" for d in dates]
    if "nine months" in context:
        return [f"9M_{d[-4:]}" for d in dates]
    if "three months" in context:
        return [f"3M_{d[-4:]}" for d in dates]
    return [d if "," in d else f"FY{d}" for d in dates]


def extract(path, statement: str) -> list[dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    for i, ln in enumerate(lines):
        if not HEADINGS[statement].match(ln.strip()):
            continue
        # locate the column-date header within the next few lines
        for j in range(i + 1, min(i + 10, len(lines))):
            toks = [t.strip() for t in lines[j].split("|") if t.strip()]
            if toks and all(DATE_TOKEN.match(t) for t in toks) and len(toks) >= 2:
                cols = column_names(lines[i:j], toks)
                break
        else:
            continue  # table-of-contents entry, not the statement itself
        rows, section = [], ""
        for ln2 in lines[j + 1:]:
            if ln2.startswith("The accompanying notes") or (ln2.startswith("Table of Contents") and len(rows) > 10):
                break
            if "|" not in ln2:
                if ln2.strip().endswith(":"):
                    section = ln2.strip().rstrip(":")
                continue
            toks = [t.strip() for t in ln2.split("|")]
            label = toks[0]
            vals = [parse_number(t) for t in toks[1:] if t not in {"$", ""}]
            vals = [v for v in vals if v is not None]
            if label and len(vals) == len(cols):
                if label.endswith(":"):
                    section = label.rstrip(":")
                for c, v in zip(cols, vals):
                    rows.append(dict(statement=statement, section=section, label=label, period=c, value=v))
        if len(rows) > 10:
            return rows
    return []


def main() -> None:
    ensure_text()
    out = []
    for path in sorted(TEXT.glob("10-[KQ]/*.txt")):
        form = path.parent.name
        for st in HEADINGS:
            rows = extract(path, st)
            for r in rows:
                r.update(filing=path.stem, form=form)
            out.extend(rows)
            print(f"{path.stem:<40} {st}: {len(rows)//max(1, len({r['period'] for r in rows})) if rows else 0} rows")
    df = pd.DataFrame(out)[["filing", "form", "statement", "section", "label", "period", "value"]]
    df.to_csv(FIN_DATA / "hpe_statements_long.csv", index=False)
    print(f"saved {len(df)} values")


if __name__ == "__main__":
    main()
