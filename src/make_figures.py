"""Figures from the CSVs written by analysis.py."""
from pathlib import Path
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / "outputs"; FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 140})
TIER = {1: "#c8553d", 2: "#e09f3e", 3: "#5b8e7d", 4: "#2f5d8a"}
NAME = {1: "Lowest quarter of spenders", 2: "Second quarter", 3: "Third quarter", 4: "Highest quarter of spenders"}


def oop_by_tier():
    d = pd.read_csv(OUT / "financing_mix_by_tier.csv"); fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for t, g in d.groupby("tier"):
        ax.plot(g.year, g.oop_med, color=TIER[t], lw=2, label=NAME[t])
        ax.fill_between(g.year, g.oop_q1, g.oop_q3, color=TIER[t], alpha=.12, lw=0)
    ax.set_ylabel("Out-of-pocket share of health spending (%)"); ax.set_title("Out-of-pocket payments have fallen everywhere, but remain high where spending is lowest", loc="left", fontsize=10)
    ax.axvspan(2020, 2021, color="grey", alpha=.12); ax.text(2020.05, 3, "pandemic", fontsize=8, color="grey")
    ax.legend(frameon=False, fontsize=8, loc="upper right"); ax.set_ylim(0, 75)
    ax.text(0, -.17, "Lines are medians by spending tier (tiers fixed on 2019 spend per person); bands are interquartile ranges. Source: WHO GHED.", transform=ax.transAxes, fontsize=7.5, color="#555")
    fig.tight_layout(); fig.savefig(FIG / "oop_by_tier.png"); plt.close(fig)


def preston():
    d = pd.read_csv(OUT / "life_expectancy_vs_spending_2019.csv"); eu = pd.read_csv(OUT / "eu27_panel.csv"); eu = eu[eu.year == 2019]
    fig, ax = plt.subplots(figsize=(7.5, 4.6)); ax.scatter(d.che_pc_usd, d.life_expectancy, s=14, color="#9aa5b1", alpha=.8, label="Other countries")
    e = d[d.iso3.isin(eu.iso3)]; ax.scatter(e.che_pc_usd, e.life_expectancy, s=22, color="#2f5d8a", label="EU27")
    ie = d[d.iso3 == "IRL"]; ax.scatter(ie.che_pc_usd, ie.life_expectancy, s=70, color="#c8553d", zorder=5, label="Ireland")
    x = np.logspace(np.log10(d.che_pc_usd.min()), np.log10(d.che_pc_usd.max()), 200); b = np.polyfit(np.log10(d.che_pc_usd), d.life_expectancy, 2)
    ax.plot(x, np.polyval(b, np.log10(x)), color="#222", lw=1.5, label="Quadratic fit in log spend"); ax.set_xscale("log")
    ax.set_xlabel("Health spending per person, 2019 (constant 2023 US$, log scale)"); ax.set_ylabel("Life expectancy at birth (years)")
    ax.set_title("More spending goes with longer life, with sharply diminishing returns", loc="left", fontsize=10); ax.legend(frameon=False, fontsize=8, loc="lower right")
    fig.tight_layout(); fig.savefig(FIG / "life_expectancy_vs_spending.png"); plt.close(fig)


def covid():
    d = pd.read_csv(OUT / "change_since_2019.csv"); fig, ax = plt.subplots(1, 2, figsize=(9, 4), sharey=False)
    for a, col, ttl in [(ax[0], "pct_change_2021", "Spend per person, 2021 vs 2019 (%)"), (ax[1], "d_oop_pp_2021", "Out-of-pocket share, 2021 vs 2019 (points)")]:
        data = [d[d.tier == t][col].dropna() for t in (1, 2, 3, 4)]
        bp = a.boxplot(data, widths=.55, showfliers=False, patch_artist=True, medianprops=dict(color="#222", lw=1.5))
        for p, t in zip(bp["boxes"], (1, 2, 3, 4)): p.set(facecolor=TIER[t], alpha=.55, lw=0)
        a.axhline(0, color="#888", lw=.8); a.set_xticklabels(["Lowest", "2nd", "3rd", "Highest"]); a.set_xlabel("2019 spending tier"); a.set_title(ttl, loc="left", fontsize=9)
    fig.suptitle("Most countries spent more per person after the pandemic began, and out-of-pocket shares edged down", x=.01, ha="left", fontsize=10)
    fig.tight_layout(); fig.savefig(FIG / "pandemic_change.png"); plt.close(fig)


def profiles():
    d = pd.read_csv(OUT / "financing_profiles_2019.csv"); fig, ax = plt.subplots(figsize=(6.5, 4.6))
    for c, col, lab in [(0, "#2f5d8a", "Cluster A: mostly compulsory (public) financing"), (1, "#c8553d", "Cluster B: mostly out-of-pocket")]:
        g = d[d.cluster == c]; ax.scatter(g.compulsory_share, g.oop_share, s=16, color=col, alpha=.75, label=f"{lab} (n={len(g)})")
    ie = d[d.iso3 == "IRL"]; ax.scatter(ie.compulsory_share, ie.oop_share, s=80, facecolor="none", edgecolor="#111", lw=1.6, label="Ireland", zorder=5)
    ax.set_xlabel("Compulsory schemes (% of health spending)"); ax.set_ylabel("Out-of-pocket (% of health spending)"); ax.set_title("Two financing profiles in 2019 (k-means on the four scheme shares)", loc="left", fontsize=10)
    ax.legend(frameon=False, fontsize=7.5); fig.tight_layout(); fig.savefig(FIG / "financing_profiles.png"); plt.close(fig)


if __name__ == "__main__":
    oop_by_tier(); preston(); covid(); profiles(); print("figures written")
