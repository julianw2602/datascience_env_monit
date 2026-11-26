"""Analyse annual GPP against deadwood, with MODIS NDVI as a canopy-greenness description.

Python-only analysis for Block 5, student 34.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr


ROOT = Path(__file__).resolve().parents[2]
DAILY = ROOT / "data" / "processed" / "site_daily.csv"
DEADTREES = ROOT / "data" / "external" / "deadtrees" / "deadtrees_my_sites.csv"
MODIS = ROOT / "data" / "external" / "modis" / "modis_vi_my_sites.csv"
OUT = ROOT / "reports" / "block5_question"
OUT.mkdir(parents=True, exist_ok=True)


daily = pd.read_csv(DAILY, parse_dates=["date"])
deadwood = pd.read_csv(DEADTREES)
modis = pd.read_csv(MODIS, parse_dates=["date"])

daily["year"] = daily["date"].dt.year
gpp = (
    daily.dropna(subset=["GPP_NT_VUT_REF"])
    .groupby(["site_id", "year"])
    .agg(
        annual_gpp_gC_m2=("GPP_NT_VUT_REF", "sum"),
        gpp_observed_days=("GPP_NT_VUT_REF", "size"),
    )
    .reset_index()
)
# Keep a year only if at least 300 of its daily GPP values are observed.
gpp = gpp[gpp["gpp_observed_days"] >= 300]

modis["year"] = modis["date"].dt.year
modis["month"] = modis["date"].dt.month
growing = modis[modis["month"].between(4, 9)]
ndvi_annual = (
    growing.groupby(["site_id", "year"])
    .agg(annual_mean_ndvi_apr_sep=("ndvi", "mean"), ndvi_dates=("ndvi", "size"))
    .reset_index()
)

annual = deadwood.merge(gpp, on=["site_id", "year"], how="inner")
annual = annual.merge(ndvi_annual, on=["site_id", "year"], how="left")
annual = annual.dropna(subset=["annual_gpp_gC_m2", "deadwood_pct"])
annual.to_csv(OUT / "annual_deadwood_gpp.csv", index=False)

european = ["FI-Hyy", "DE-Geb", "ES-LM1"]
analysis = annual[annual["site_id"].isin(european)].copy()
r, p = pearsonr(analysis["deadwood_pct"], analysis["annual_gpp_gC_m2"])

summary = pd.DataFrame(
    [{
        "n_tower_years": len(analysis),
        "n_towers": analysis["site_id"].nunique(),
        "pearson_r": r,
        "p_value": p,
        "gpp_method": "sum of observed GPP_NT_VUT_REF days; year >= 300 observed days",
    }]
)
summary.to_csv(OUT / "deadwood_gpp_summary.csv", index=False)

tower_means = (
    analysis.groupby("site_id", as_index=False)
    .agg(
        mean_deadwood_pct=("deadwood_pct", "mean"),
        mean_annual_gpp_gC_m2=("annual_gpp_gC_m2", "mean"),
        mean_ndvi_apr_sep=("annual_mean_ndvi_apr_sep", "mean"),
    )
)
tower_means.to_csv(OUT / "european_tower_means.csv", index=False)

colors = {"FI-Hyy": "#1b9e77", "DE-Geb": "#d95f02", "ES-LM1": "#7570b3"}

fig, ax = plt.subplots(figsize=(8, 5.5))
for site, group in analysis.groupby("site_id"):
    ax.scatter(
        group["deadwood_pct"],
        group["annual_gpp_gC_m2"],
        s=38,
        color=colors[site],
        alpha=0.82,
        label=site,
    )
if len(analysis) >= 2:
    slope, intercept = np.polyfit(analysis["deadwood_pct"], analysis["annual_gpp_gC_m2"], 1)
    x = np.linspace(analysis["deadwood_pct"].min(), analysis["deadwood_pct"].max(), 100)
    ax.plot(x, slope * x + intercept, color="black", linewidth=1.5, label="All points")
ax.set(
    xlabel="Standing deadwood cover in 2 km x 2 km box (%)",
    ylabel="Annual GPP (g C m-2 yr-1)",
    title="Annual GPP versus standing deadwood",
)
ax.legend(title="Tower")
ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(OUT / "deadwood_vs_annual_gpp.png", dpi=200)
plt.close(fig)

fi = analysis[analysis["site_id"] == "FI-Hyy"].sort_values("year")
if not fi.empty:
    fig, ax1 = plt.subplots(figsize=(8, 5))
    ax1.plot(fi["year"], fi["deadwood_pct"], marker="o", color="#b2182b", label="Deadwood")
    ax1.set_xlabel("Year")
    ax1.set_ylabel("Standing deadwood cover (%)", color="#b2182b")
    ax1.tick_params(axis="y", labelcolor="#b2182b")
    ax2 = ax1.twinx()
    ax2.plot(fi["year"], fi["annual_gpp_gC_m2"], marker="o", color="#2166ac", label="GPP")
    ax2.set_ylabel("Annual GPP (g C m-2 yr-1)", color="#2166ac")
    ax2.tick_params(axis="y", labelcolor="#2166ac")
    ax1.set_title("FI-Hyy: deadwood and GPP through time")
    ax1.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT / "fi_hyy_deadwood_gpp_timeseries.png", dpi=200)
    plt.close(fig)

fig, ax = plt.subplots(figsize=(8, 5.5))
for site, group in analysis.groupby("site_id"):
    ax.scatter(
        group["annual_mean_ndvi_apr_sep"],
        group["annual_gpp_gC_m2"],
        s=38,
        color=colors[site],
        alpha=0.82,
        label=site,
    )
ax.set(
    xlabel="MODIS mean NDVI, April-September (unitless)",
    ylabel="Annual GPP (g C m-2 yr-1)",
    title="MODIS canopy greenness and annual GPP",
)
ax.legend(title="Tower")
ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(OUT / "ndvi_vs_annual_gpp.png", dpi=200)
plt.close(fig)

print(summary.to_string(index=False))
print("\nEuropean tower means:")
print(tower_means.to_string(index=False))
