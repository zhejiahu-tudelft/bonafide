"""Capital structure, financing history, dilution and liquidity for HPE.

All inputs are keyed from primary filings (source noted per item):
  * Q3 FY26 10-Q / earnings release (31-Jul-2026 balance sheet, preferred, warrant, repurchase authorisation)
  * FY2025 10-K (debt maturities at face, RSU activity, preferred terms, equity plan)
  * Q3 FY26 earnings call (net leverage, planned note repayment)

The fully diluted share count used everywhere in valuation is produced here (capital_summary.json).

Outputs: data/processed_data/capital/*.csv, capital_summary.json; charts.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import viz
from common import MKT_DATA, PROC, VALUATION_DATE

OUT = PROC / "capital"
OUT.mkdir(exist_ok=True)

BS_Q3FY26 = {"short_term_debt": 2901, "long_term_debt": 17343, "cash": 6216, "nci": 62, "hpe_equity": 26514,
             "common_shares_outstanding_m": 1328.0, "authorized_common_m": 9600.0}   # Q3 FY26 release p.14
PREFERRED = {"shares_m": 30.0, "liquidation_pref": 50.0, "dividend_rate": 0.07625, "min_rate": 2.5352,
             "max_rate": 3.1056, "mandatory_conversion": "~2027-09-01"}          # FY25 10-K; 424B5 Sep-2024
EMPLOYEE_TSM_DILUTION_M = 37.0          # Q3 FY26 diluted EPS: dilutive effect of employee stock plans
RSU_OUTSTANDING_FY25_M = 75.41          # FY25 10-K RSU table (incl. Juniper replacement awards)
ORACLE_WARRANT_M = 4.156466             # Q3 FY26 10-Q: warrant dated 2-Jul-2026, $0.01 strike, milestone vesting
REPURCHASE_AUTH_REMAINING = 3200        # Q3 FY26 10-Q
MATURITIES_FY25_10K = {"FY2026": 3804, "FY2027": 3136, "FY2028": 3778, "FY2029": 2376, "FY2030": 404, "Thereafter": 8250}
FY26_ISSUANCE = [("Floating rate notes due Mar-2028", 300, "FY2028"), ("4.50% senior notes due Mar-2028", 500, "FY2028"),
                 ("4.60% senior notes due Mar-2029", 600, "FY2029"), ("5.25% senior notes due Apr-2033", 600, "Thereafter")]
LIQUIDITY = {"revolver_capacity": 5250, "cp_program_max_combined": 5750, "subsidiary_cp_outstanding": 622}
COMPANY_NET_LEVERAGE = 1.8              # Q3 FY26 call: net leverage ratio, target 2x


def main() -> None:
    price = float(pd.read_csv(MKT_DATA / "HPE_daily.csv", parse_dates=["date"]).set_index("date").loc[:VALUATION_DATE, "close"].iloc[-1])
    pref_rate = PREFERRED["min_rate"] if price >= PREFERRED["liquidation_pref"] / PREFERRED["min_rate"] else (
        PREFERRED["max_rate"] if price <= PREFERRED["liquidation_pref"] / PREFERRED["max_rate"]
        else PREFERRED["liquidation_pref"] / price)
    pref_shares = PREFERRED["shares_m"] * pref_rate

    dil = pd.DataFrame([
        ("Common shares outstanding (31-Jul-2026)", BS_Q3FY26["common_shares_outstanding_m"], "Q3 FY26 balance sheet", "Reported"),
        ("RSUs / PRSUs (treasury-stock method)", EMPLOYEE_TSM_DILUTION_M,
         f"Q3 FY26 diluted EPS; {RSU_OUTSTANDING_FY25_M:.1f}m RSUs outstanding at FY25 end", "Reported"),
        ("7.625% Series C mandatory convertible preferred (as converted)", pref_shares,
         f"30.0m pref × {pref_rate:.4f} (min. rate applies above ${PREFERRED['liquidation_pref'] / PREFERRED['min_rate']:.2f})", "Calculated"),
        ("Oracle warrant (max., milestone-vesting)", ORACLE_WARRANT_M, "Q3 FY26 10-Q; $0.01 exercise price", "Reported (upper bound)"),
        ("Employee stock options", 0.0, "Not material in reviewed filings", "Data unavailable from the reviewed sources"),
        ("Convertible notes", 0.0, "None identified in reviewed filings", "Reported"),
    ], columns=["instrument", "shares_m", "basis", "status"])
    fully_diluted = dil["shares_m"].sum()
    dil["pct_of_basic"] = dil["shares_m"] / BS_Q3FY26["common_shares_outstanding_m"]
    dil.to_csv(OUT / "dilution_table.csv", index=False)

    mat = pd.DataFrame({"reported_fy25_10k": pd.Series(MATURITIES_FY25_10K)})
    add = pd.Series(0.0, index=mat.index)
    for _, amt, bucket in FY26_ISSUANCE:
        add[bucket] += amt
    mat["fy26_new_issuance"] = add
    mat.to_csv(OUT / "debt_maturities.csv")

    fin = pd.read_csv(PROC / "financials" / "hpe_financials.csv", index_col=0)
    hist = fin.loc[["debt_issued", "debt_repaid", "preferred_issued", "buybacks", "dividends_common", "dividends_preferred",
                    "acquisitions", "shares_diluted", "sbc"]].T
    hist.to_csv(OUT / "financing_history.csv")

    gross_debt = BS_Q3FY26["short_term_debt"] + BS_Q3FY26["long_term_debt"]
    adj_ebitda_ttm = fin.at["non_gaap_operating_profit", "TTM Q3 FY26"] + fin.at["d_and_a", "TTM Q3 FY26"] - fin.at["amortization", "TTM Q3 FY26"]
    summary = {
        "valuation_date": VALUATION_DATE, "price": price,
        "basic_shares_m": BS_Q3FY26["common_shares_outstanding_m"], "fully_diluted_shares_m": round(fully_diluted, 2),
        "preferred_conversion_rate_at_price": pref_rate, "preferred_as_converted_m": round(pref_shares, 2),
        "market_cap_basic_m": round(price * BS_Q3FY26["common_shares_outstanding_m"], 0),
        "market_cap_fully_diluted_m": round(price * fully_diluted, 0),
        "gross_debt_m": gross_debt, "cash_m": BS_Q3FY26["cash"], "net_debt_m": gross_debt - BS_Q3FY26["cash"],
        "nci_m": BS_Q3FY26["nci"],
        "enterprise_value_m": round(price * fully_diluted + gross_debt - BS_Q3FY26["cash"] + BS_Q3FY26["nci"], 0),
        "adj_ebitda_ttm_company_basis_m": round(adj_ebitda_ttm, 0),
        "gross_debt_to_adj_ebitda": round(gross_debt / adj_ebitda_ttm, 2),
        "net_debt_to_adj_ebitda": round((gross_debt - BS_Q3FY26["cash"]) / adj_ebitda_ttm, 2),
        "company_reported_net_leverage": COMPANY_NET_LEVERAGE,
        "preferred_annual_dividend_m": PREFERRED["shares_m"] * PREFERRED["liquidation_pref"] * PREFERRED["dividend_rate"],
        "repurchase_authorization_remaining_m": REPURCHASE_AUTH_REMAINING,
        "liquidity_cash_plus_revolver_m": BS_Q3FY26["cash"] + LIQUIDITY["revolver_capacity"],
        "dilution_vs_basic_pct": round(fully_diluted / BS_Q3FY26["common_shares_outstanding_m"] - 1, 4),
        "oracle_warrant_value_at_price_m": round(ORACLE_WARRANT_M * (price - 0.01), 0),
    }
    (OUT / "capital_summary.json").write_text(json.dumps(summary, indent=2))

    # Chart: maturity ladder (FY25 10-K face values + FY26 issuance)
    fig, ax = viz.figure(8, 3.0)
    x = np.arange(len(mat))
    ax.bar(x, mat["reported_fy25_10k"] / 1000, width=0.55, color=viz.GREEN, edgecolor=viz.SURFACE, linewidth=1.5,
           label="Maturities at 31-Oct-2025 (10-K, face)")
    ax.bar(x, mat["fy26_new_issuance"] / 1000, bottom=mat["reported_fy25_10k"] / 1000, width=0.55, color=viz.GOLD,
           edgecolor=viz.SURFACE, linewidth=1.5, label="Notes issued Mar-2026")
    for i, (idx, row) in enumerate(mat.iterrows()):
        tot = row.sum() / 1000
        ax.text(i, tot + 0.15, f"${tot:.1f}bn", ha="center", fontsize=7.5, color=viz.INK2)
    ax.set_xticks(x, mat.index)
    ax.set_ylabel("$bn")
    ax.set_ylim(0, mat.sum(axis=1).max() / 1000 * 1.2)
    ax.legend(loc="upper left")
    viz.titles(ax, "Maturities are spread out; FY26–FY28 towers are refinanceable from FCF",
               "Borrowings by fiscal year of maturity; FY26 bucket largely repaid during FY26 (term loan, Sep-2026 notes)")
    viz.source(fig, "HPE FY2025 10-K Note 14; Q3 FY26 10-Q; Bona Fide analysis.")
    viz.save(fig, "cap_debt_maturities")

    # Chart: share-count bridge (basic -> fully diluted)
    fig, ax = viz.figure(8, 3.0)
    steps = dil[dil["shares_m"] > 0].reset_index(drop=True)
    names = ["Basic shares", "RSUs/PRSUs (TSM)", "Mandatory convertible\npreferred", "Oracle warrant (max.)"]
    level = 0.0
    for i, row in steps.iterrows():
        bottom = 0 if i == 0 else level
        ax.bar(i, row.shares_m, bottom=bottom, width=0.55, color=viz.GREEN if i == 0 else viz.GOLD)
        level = bottom + row.shares_m
        ax.text(i, level + 3, f"{row.shares_m:,.0f}m" if i == 0 else f"+{row.shares_m:,.1f}m", ha="center",
                fontsize=7.5, color=viz.INK2)
    total_x = len(steps)
    ax.bar(total_x, level, width=0.55, color=viz.BLUE)
    ax.text(total_x, level + 3, f"{level:,.0f}m (+{level / BS_Q3FY26['common_shares_outstanding_m'] - 1:.1%})",
            ha="center", fontsize=7.5, color=viz.INK)
    ax.set_xticks(range(total_x + 1), names + ["Fully diluted"], fontsize=7.5)
    ax.set_ylim(1250, level * 1.03)
    ax.set_ylabel("Shares (m); axis starts at 1,250m")
    viz.titles(ax, "Fully diluted share count is ~9% above basic, mostly the preferred",
               "Bridge from basic to fully diluted shares at $62.09 (preferred converts at the minimum rate)")
    viz.source(fig, "HPE Q3 FY26 10-Q and earnings release; FY25 10-K; Bona Fide analysis.")
    viz.save(fig, "cap_dilution_bridge")

    pd.set_option("display.width", 200)
    print(dil.round(3).to_string())
    print(mat)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
