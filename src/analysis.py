"""Statistical analysis of WHO health-financing data. Reads views from the SQLite database, writes outputs/results.json."""
import json, sqlite3, warnings
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "outputs" / "health_financing.db"
RNG = np.random.default_rng(2026)
EU27 = ["AUT", "BEL", "BGR", "HRV", "CYP", "CZE", "DNK", "EST", "FIN", "FRA", "DEU", "GRC", "HUN", "IRL",
        "ITA", "LVA", "LTU", "LUX", "MLT", "NLD", "POL", "PRT", "ROU", "SVK", "SVN", "ESP", "SWE"]


def connect():
    con = sqlite3.connect(DB)
    con.execute("DROP TABLE IF EXISTS eu27"); con.execute("CREATE TABLE eu27 (iso3 TEXT PRIMARY KEY)")
    con.executemany("INSERT INTO eu27 VALUES (?)", [(c,) for c in EU27])
    con.executescript((ROOT / "sql" / "02_views.sql").read_text()); con.commit()
    return con


def boot_ci(x, fn=np.median, n=4000):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    return [float(np.percentile([fn(RNG.choice(x, len(x))) for _ in range(n)], q)) for q in (2.5, 97.5)]


def spearman_ci(a, b, n=3000):
    a, b = np.asarray(a, float), np.asarray(b, float); m = ~(np.isnan(a) | np.isnan(b)); a, b = a[m], b[m]
    rho = stats.spearmanr(a, b)[0]; idx = np.arange(len(a))
    bs = [stats.spearmanr(a[i], b[i])[0] for i in (RNG.choice(idx, len(idx)) for _ in range(n))]
    return float(rho), [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))], int(len(a))


def quad_fit(x, y):
    X = np.column_stack([np.ones_like(x), x, x ** 2]); beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return beta, 1 - ((y - X @ beta) ** 2).sum() / ((y - y.mean()) ** 2).sum()


def main():
    con = connect(); R = {}
    panel = pd.read_sql("SELECT * FROM panel", con)

    # ---------------------------------------------------------------- data quality
    key = panel[["iso3", "year"]]
    R["data_quality"] = {
        "country_years": int(len(panel)), "countries": int(panel.iso3.nunique()), "years": [int(panel.year.min()), int(panel.year.max())],
        "duplicate_country_years": int(key.duplicated().sum()),
        "missing_population_countries": sorted(panel[panel.population.isna()].iso3.unique().tolist()),
        "share_sum_gov_pvt_ext_outside_99_101": int(((panel[["gov_share", "pvt_share", "ext_share"]].sum(axis=1, min_count=3) - 100).abs() > 1).sum()),
        "scheme_shares_unresolved_rest_of_world": int((panel.compulsory_share.notna() & panel.oop_share.notna() & panel.row_share.isna()).sum()),
        "negative_spending": int((panel.che_usd < 0).sum()),
        "life_expectancy_coverage_2019": int(panel[(panel.year == 2019) & panel.life_expectancy.notna()].shape[0]),
    }

    # ---------------------------------------------------------------- who pays, over time, by spending tier
    tier = pd.read_sql("SELECT * FROM v_tier", con)
    m = panel.merge(tier[["iso3", "tier"]], on="iso3")
    mix = m.groupby(["tier", "year"]).agg(oop_med=("oop_share", "median"), oop_q1=("oop_share", lambda s: s.quantile(.25)), oop_q3=("oop_share", lambda s: s.quantile(.75)),
                                          comp_med=("compulsory_share", "median"), ext_med=("ext_share", "median"), n=("iso3", "nunique")).reset_index()
    mix.to_csv(ROOT / "outputs" / "financing_mix_by_tier.csv", index=False)
    R["tier_cutpoints_usd_2019"] = [float(x) for x in tier.groupby("tier").pc_2019.max().values]
    t = lambda tr, y, c: float(mix[(mix.tier == tr) & (mix.year == y)][c].iloc[0])
    R["mix_by_tier"] = {f"tier{tr}": {"oop_median_2000": t(tr, 2000, "oop_med"), "oop_median_2023": t(tr, 2023, "oop_med"),
                                      "compulsory_median_2000": t(tr, 2000, "comp_med"), "compulsory_median_2023": t(tr, 2023, "comp_med")} for tr in (1, 2, 3, 4)}

    # ---------------------------------------------------------------- cross-country relationships (2023)
    lt = pd.read_sql("SELECT * FROM v_latest", con)
    rho, ci, n = spearman_ci(np.log10(lt.che_pc_usd), lt.oop_share)
    R["oop_vs_spending_2023"] = {"spearman_rho": rho, "ci95": ci, "n": n}
    rho2, ci2, n2 = spearman_ci(lt.compulsory_share, lt.oop_share)
    R["oop_vs_compulsory_share_2023"] = {"spearman_rho": rho2, "ci95": ci2, "n": n2}
    R["top_oop_2023"] = lt.nsmallest(8, "oop_rank_high_to_low")[["country", "oop_share", "che_pc_usd"]].round(1).to_dict("records")
    hi = lt[lt.oop_share >= 40]; R["countries_oop_ge_40pct_2023"] = {"n": int(len(hi)), "of": int(len(lt)), "median_spend_pc_usd": float(hi.che_pc_usd.median())}
    # WHO financial-protection benchmark: out-of-pocket below about 15-20% of current spending
    R["countries_oop_le_15pct_2023"] = int((lt.oop_share <= 15).sum())

    # ---------------------------------------------------------------- pandemic-era change vs 2019
    ch = pd.read_sql("SELECT * FROM v_change", con); R["covid"] = {"n": int(len(ch))}
    for y in ("2021", "2023"):
        x = ch[f"pct_change_{y}"]
        lr = np.log(ch[f"pc_{y}"] / ch.pc_2019)
        R["covid"][y] = {"median_pct_change": float(x.median()), "ci95": boot_ci(x), "share_of_countries_higher": float((x > 0).mean()),
                         "wilcoxon_p": float(stats.wilcoxon(lr).pvalue),
                         "median_d_compulsory_pp": float(ch[f"d_compulsory_pp_{y}"].median()), "median_d_oop_pp": float(ch[f"d_oop_pp_{y}"].median()),
                         "ci95_d_oop_pp": boot_ci(ch[f"d_oop_pp_{y}"]), "by_tier_median_pct": {int(k): float(v) for k, v in ch.groupby("tier")[f"pct_change_{y}"].median().items()}}
    yoy = pd.read_sql("SELECT * FROM v_yoy WHERE year BETWEEN 2020 AND 2023", con)
    R["covid"]["median_yoy_by_year"] = {int(k): float(v) for k, v in yoy.groupby("year").yoy_pct.median().items()}
    ch.to_csv(ROOT / "outputs" / "change_since_2019.csv", index=False)

    # ---------------------------------------------------------------- spending vs life expectancy (2019)
    d = panel[(panel.year == 2019)].dropna(subset=["che_pc_usd", "life_expectancy"]).copy(); d = d[d.che_pc_usd > 0]
    x = np.log10(d.che_pc_usd.values); y = d.life_expectancy.values
    beta, r2 = quad_fit(x, y); d["fitted"] = np.column_stack([np.ones_like(x), x, x ** 2]) @ beta; d["resid"] = d.life_expectancy - d.fitted
    d["resid_rank_high_to_low"] = d.resid.rank(ascending=False).astype(int)
    boots = []
    for _ in range(2000):
        i = RNG.choice(len(d), len(d)); b, _ = quad_fit(x[i], y[i]); boots.append(b)
    irl_x = np.log10(d[d.iso3 == "IRL"].che_pc_usd.iloc[0]); irl_y = d[d.iso3 == "IRL"].life_expectancy.iloc[0]
    irl_res = [irl_y - (b[0] + b[1] * irl_x + b[2] * irl_x ** 2) for b in boots]
    R["spending_vs_life_expectancy_2019"] = {
        "n": int(len(d)), "r_squared_quadratic_in_log10_spend": float(r2),
        "life_exp_gain_per_doubling_at_300usd": float((beta[1] + 2 * beta[2] * np.log10(300)) * np.log10(2)),
        "life_exp_gain_per_doubling_at_3000usd": float((beta[1] + 2 * beta[2] * np.log10(3000)) * np.log10(2)),
        "ireland": {"spend_pc_usd": float(10 ** irl_x), "life_expectancy": float(irl_y), "residual_years": float(d[d.iso3 == "IRL"].resid.iloc[0]),
                    "residual_ci95": [float(np.percentile(irl_res, 2.5)), float(np.percentile(irl_res, 97.5))], "rank_of_n": int(d[d.iso3 == "IRL"].resid_rank_high_to_low.iloc[0])},
        "above_curve_top5": d.nlargest(5, "resid")[["country", "che_pc_usd", "life_expectancy", "resid"]].round(1).to_dict("records"),
        "below_curve_bottom5": d.nsmallest(5, "resid")[["country", "che_pc_usd", "life_expectancy", "resid"]].round(1).to_dict("records")}
    d[["iso3", "country", "che_pc_usd", "life_expectancy", "fitted", "resid"]].round(3).to_csv(ROOT / "outputs" / "life_expectancy_vs_spending_2019.csv", index=False)

    # ---------------------------------------------------------------- financing profiles (k-means on 2019 scheme shares)
    f = panel[panel.year == 2019].dropna(subset=["compulsory_share", "voluntary_share", "oop_share", "row_share"]).copy()
    cols = ["compulsory_share", "voluntary_share", "oop_share", "row_share"]; Xf = f[cols].values
    sil = {k: float(silhouette_score(Xf, KMeans(k, n_init=20, random_state=0).fit_predict(Xf))) for k in range(2, 8)}
    k = max(sil, key=sil.get); km = KMeans(k, n_init=50, random_state=0).fit(Xf); f["cluster"] = km.labels_
    aris = []
    for _ in range(100):
        i = RNG.choice(len(f), len(f)); kb = KMeans(k, n_init=10, random_state=int(RNG.integers(1e6))).fit(Xf[i]); aris.append(adjusted_rand_score(km.labels_, kb.predict(Xf)))
    cen = pd.DataFrame(km.cluster_centers_, columns=cols).round(1); cen["n"] = np.bincount(km.labels_)
    R["profiles_2019"] = {"silhouette_by_k": sil, "chosen_k": int(k), "bootstrap_ari_median": float(np.median(aris)), "bootstrap_ari_p10": float(np.percentile(aris, 10)),
                          "centroids": cen.to_dict("records"), "ireland_cluster": int(f[f.iso3 == "IRL"].cluster.iloc[0])}
    f[["iso3", "country", "cluster"] + cols + ["che_pc_usd"]].round(2).to_csv(ROOT / "outputs" / "financing_profiles_2019.csv", index=False)

    # ---------------------------------------------------------------- Ireland and the EU27
    eu = pd.read_sql("SELECT * FROM v_eu", con)
    for yr in (2000, 2019, 2023):
        e = eu[eu.year == yr]; ir = e[e.iso3 == "IRL"].iloc[0]
        R.setdefault("ireland_vs_eu27", {})[str(yr)] = {"n_eu": int(ir.n_eu), "spend_pc_usd": float(ir.che_pc_usd), "eu_median_spend_pc_usd": float(e.che_pc_usd.median()), "spend_rank": int(ir.spend_rank),
            "oop_share": float(ir.oop_share), "eu_median_oop_share": float(e.oop_share.median()), "oop_rank_high_to_low": int(ir.oop_rank),
            "compulsory_share": float(ir.compulsory_share), "eu_median_compulsory_share": float(e.compulsory_share.median()),
            "voluntary_share": float(ir.voluntary_share), "eu_median_voluntary_share": float(e.voluntary_share.median())}
    pv = panel[panel.iso3.isin(EU27) & (panel.year == 2022) & panel.preventive_share.notna()]
    R["ireland_vs_eu27"]["preventive_share_2022"] = {"n_eu_with_data": int(len(pv)), "eu_median": float(pv.preventive_share.median()),
        "ireland": float(pv[pv.iso3 == "IRL"].preventive_share.iloc[0]) if (pv.iso3 == "IRL").any() else None}
    pv19 = panel[panel.iso3.isin(EU27) & (panel.year == 2019) & panel.preventive_share.notna()]
    R["ireland_vs_eu27"]["preventive_share_2019"] = {"n_eu_with_data": int(len(pv19)), "eu_median": float(pv19.preventive_share.median()),
        "ireland": float(pv19[pv19.iso3 == "IRL"].preventive_share.iloc[0]) if (pv19.iso3 == "IRL").any() else None}
    eu.to_csv(ROOT / "outputs" / "eu27_panel.csv", index=False)

    json.dump(R, open(ROOT / "outputs" / "results.json", "w"), indent=1, default=float)
    return R, panel, d, f, mix, ch, eu


if __name__ == "__main__":
    print(json.dumps(main()[0], indent=1, default=float))
