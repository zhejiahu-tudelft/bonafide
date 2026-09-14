"""Practitioner Q&A 1: is Juniper equipment unusually exposed to actively exploited vulnerabilities?

Counts entries in the CISA Known Exploited Vulnerabilities (KEV) catalogue for Juniper and for other
enterprise network and security infrastructure vendors, in total and since 2024.

Input: the KEV catalogue cached in report/other_evidence/practitioner_qa/
(https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json).
KEV lists vulnerabilities with evidence of exploitation in the wild. Counts are not normalised for
installed base or product breadth, so they measure exposure history, not per-device risk.
"""
from __future__ import annotations

import json

import matplotlib.pyplot as plt
import pandas as pd

import viz
from common import OTHER, PROC

KEV_FILE = OTHER / "practitioner_qa" / "cisa_kev_catalog_2026.09.11.json"
OUT = PROC / "qa"
OUT.mkdir(parents=True, exist_ok=True)

# enterprise network / security infrastructure vendors as named in the KEV vendorProject field
# (consumer networking brands and virtualisation software are excluded)
VENDORS = {
    "Cisco": "Cisco", "Ivanti": "Ivanti", "Fortinet": "Fortinet", "Citrix": "Citrix",
    "SonicWall": "SonicWall", "Palo Alto Networks": "Palo Alto Networks", "Zyxel": "Zyxel",
    "Juniper": "Juniper", "F5": "F5", "Sophos": "Sophos", "Check Point": "Check Point",
    "Arista": "Arista", "Hewlett Packard Enterprise (HPE)": "HPE (excl. Juniper)",
}
HPE_OWNED = {"Juniper", "HPE (excl. Juniper)"}


def main() -> None:
    kev = json.load(open(KEV_FILE))
    df = pd.DataFrame(kev["vulnerabilities"])
    df["dateAdded"] = pd.to_datetime(df["dateAdded"])
    df = df[df["vendorProject"].isin(VENDORS)].assign(vendor=lambda d: d["vendorProject"].map(VENDORS))

    counts = (df.groupby("vendor")
                .agg(kev_entries=("cveID", "size"),
                     added_since_2024=("dateAdded", lambda s: int((s >= "2024-01-01").sum())),
                     known_ransomware_use=("knownRansomwareCampaignUse", lambda s: int((s == "Known").sum())),
                     first_added=("dateAdded", "min"), last_added=("dateAdded", "max"))
                .sort_values("kev_entries", ascending=False))
    counts["share_of_group"] = counts["kev_entries"] / counts["kev_entries"].sum()
    counts.to_csv(OUT / "kev_vendor_counts.csv", date_format="%Y-%m-%d")

    jnpr = (df[df["vendor"] == "Juniper"]
            .sort_values("dateAdded")[["cveID", "product", "vulnerabilityName", "dateAdded", "dueDate",
                                       "knownRansomwareCampaignUse"]])
    jnpr.to_csv(OUT / "kev_juniper_entries.csv", index=False, date_format="%Y-%m-%d")

    rank = int(counts.index.get_loc("Juniper")) + 1
    summary = {
        "catalog_version": kev["catalogVersion"], "catalog_entries": int(kev["count"]),
        "vendors_compared": len(counts), "juniper_entries": int(counts.loc["Juniper", "kev_entries"]),
        "juniper_rank": rank, "juniper_since_2024": int(counts.loc["Juniper", "added_since_2024"]),
        "juniper_share_of_group": round(float(counts.loc["Juniper", "share_of_group"]), 4),
        "group_median_entries": float(counts["kev_entries"].median()),
        "counts": counts[["kev_entries", "added_since_2024", "known_ransomware_use"]].to_dict("index"),
        "juniper_by_year": jnpr["dateAdded"].dt.year.value_counts().sort_index().to_dict(),
    }
    json.dump(summary, open(OUT / "kev_summary.json", "w"), indent=2, default=int)

    # chart: total entries by vendor; HPE-owned vendors in HPE green, others as context
    plot = counts.iloc[::-1]
    fig, ax = plt.subplots(figsize=(5.2, 3.3))
    ax.grid(axis="x"); ax.grid(axis="y", visible=False)
    colours = [viz.GREEN if v in HPE_OWNED else viz.CONTEXT for v in plot.index]
    ax.barh(plot.index, plot["kev_entries"], color=colours, height=0.68)
    for y, (v, row) in enumerate(plot.iterrows()):
        ax.text(row["kev_entries"] + 1.2, y, f"{row['kev_entries']}  ({row['added_since_2024']} since 2024)",
                va="center", fontsize=7.5, color=viz.INK if v in HPE_OWNED else viz.INK2,
                fontweight="bold" if v in HPE_OWNED else "normal")
    ax.set_xlim(0, counts["kev_entries"].max() * 1.32)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("Entries in CISA Known Exploited Vulnerabilities catalogue", color=viz.INK2, fontsize=8)
    viz.titles(ax, "Juniper is not an outlier in actively exploited vulnerabilities",
               f"KEV entries by vendor, catalogue {kev['catalogVersion']}; HPE-owned vendors in green")
    viz.source(fig, "CISA KEV catalogue; Bona Fide analysis. Not normalised for installed base or product breadth.")
    viz.save(fig, "qa_kev_vendor_exposure")

    print(counts[["kev_entries", "added_since_2024", "known_ransomware_use"]].to_string())
    print(f"Juniper rank {rank}/{len(counts)}; entries {summary['juniper_entries']}; by year {summary['juniper_by_year']}")


if __name__ == "__main__":
    main()
