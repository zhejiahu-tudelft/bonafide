"""Insider transactions (SEC Form 4) and major holders for HPE.

Parses every Form 4 XML retrieved by fetch_sec.py (Sep-2024 onward) into a transaction table and
summarises open-market buys/sells versus award, tax-withholding and option-exercise activity, so
that routine compensation-related filings are not mistaken for conviction signals.

Transaction codes: P open-market purchase · S open-market sale · A grant/award · M option/RSU
conversion · F shares withheld for tax · G gift · C conversion · J other.

Outputs: data/processed_data/ownership/form4_transactions.csv, insider_summary.csv
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

import pandas as pd

from common import FIN_DATA, PROC

OUT = PROC / "ownership"
OUT.mkdir(exist_ok=True)


def text(node, path: str) -> str:
    el = node.find(path)
    return el.text.strip() if el is not None and el.text else ""


def parse(path) -> list[dict]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return []
    owner = text(root, "reportingOwner/reportingOwnerId/rptOwnerName")
    rel = root.find("reportingOwner/reportingOwnerRelationship")
    role = []
    if rel is not None:
        if text(rel, "isDirector") in ("1", "true"):
            role.append("Director")
        if text(rel, "isOfficer") in ("1", "true"):
            role.append(text(rel, "officerTitle") or "Officer")
        if text(rel, "isTenPercentOwner") in ("1", "true"):
            role.append("10% owner")
    rows = []
    for tx in root.findall("nonDerivativeTable/nonDerivativeTransaction"):
        shares = float(text(tx, "transactionAmounts/transactionShares/value") or 0)
        price = float(text(tx, "transactionAmounts/transactionPricePerShare/value") or 0)
        rows.append(dict(
            filing=path.name, owner=owner, role="; ".join(role),
            date=text(tx, "transactionDate/value"), code=text(tx, "transactionCoding/transactionCode"),
            acquired_disposed=text(tx, "transactionAmounts/transactionAcquiredDisposedCode/value"),
            shares=shares, price=price, value=shares * price,
            shares_after=float(text(tx, "postTransactionAmounts/sharesOwnedFollowingTransaction/value") or 0),
            plan_10b5_1=text(root, "aff10b5One") in ("1", "true"),
        ))
    return rows


def main() -> None:
    rows = [r for p in sorted((FIN_DATA / "form4").glob("*.xml")) for r in parse(p)]
    tx = pd.DataFrame(rows)
    tx["date"] = pd.to_datetime(tx["date"])
    tx = tx.sort_values("date")
    tx.to_csv(OUT / "form4_transactions.csv", index=False)

    label = {"P": "Open-market purchase", "S": "Open-market sale", "A": "Grant/award", "M": "Exercise/conversion",
             "F": "Tax withholding", "G": "Gift"}
    tx["type"] = tx["code"].map(label).fillna("Other")
    last12 = tx[tx["date"] > tx["date"].max() - pd.DateOffset(months=12)]
    summary = last12.groupby("type").agg(transactions=("shares", "size"), shares=("shares", "sum"), value_usd=("value", "sum"))
    summary.to_csv(OUT / "insider_summary.csv")
    sells = last12[last12["code"] == "S"].groupby(["owner", "role"]).agg(
        shares_sold=("shares", "sum"), value_usd=("value", "sum"), avg_price=("price", "mean"),
        last_sale=("date", "max"), shares_after=("shares_after", "last")).sort_values("value_usd", ascending=False)
    sells.to_csv(OUT / "insider_sales_by_person_12m.csv")
    buys = last12[last12["code"] == "P"]
    buys.to_csv(OUT / "insider_purchases_12m.csv", index=False)

    pd.set_option("display.width", 220)
    print(f"{len(tx)} transactions parsed from {tx['filing'].nunique()} Form 4 filings; "
          f"{tx['date'].min().date()} to {tx['date'].max().date()}")
    print(summary.round(0))
    print("Open-market sales by insider (12m):\n", sells.round(2).head(15))
    print("Open-market purchases (12m):\n", buys[["date", "owner", "role", "shares", "price"]])


if __name__ == "__main__":
    main()
