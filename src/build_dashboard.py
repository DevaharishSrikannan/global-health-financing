"""Write dashboard/index.html: one self-contained page with the derived data embedded (no raw WHO files)."""
import json, sqlite3
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
con = sqlite3.connect(ROOT / "outputs" / "health_financing.db")
p = pd.read_sql("SELECT iso3,country,year,che_pc_usd,oop_share,compulsory_share,life_expectancy FROM panel", con)
tier = pd.read_csv(ROOT / "outputs" / "change_since_2019.csv")[["iso3", "tier"]]

prof = pd.read_csv(ROOT / "outputs" / "financing_profiles_2019.csv")[["iso3", "cluster"]]
tiers = pd.read_sql("SELECT iso3, NTILE(4) OVER (ORDER BY che_pc_usd) AS tier FROM panel WHERE year=2019 AND che_pc_usd IS NOT NULL", con)
eu = set(pd.read_csv(ROOT / "outputs" / "eu27_panel.csv").iso3)
R = json.load(open(ROOT / "outputs" / "results.json"))
tm = dict(zip(tiers.iso3, tiers.tier)); cm = dict(zip(prof.iso3, prof.cluster))
years = list(range(2000, 2024)); rnd = lambda v: None if pd.isna(v) else round(float(v), 1)
rows = []
for iso, g in p.groupby("iso3"):
    g = g.set_index("year").reindex(years)
    rows.append({"i": iso, "n": p[p.iso3 == iso].country.iloc[0], "t": tm.get(iso), "c": cm.get(iso), "eu": iso in eu,
                 "pc": [rnd(v) for v in g.che_pc_usd], "oop": [rnd(v) for v in g.oop_share], "comp": [rnd(v) for v in g.compulsory_share], "le": [rnd(v) for v in g.life_expectancy]})
facts = {"rho_oop_spend": R["oop_vs_spending_2023"], "rho_oop_comp": R["oop_vs_compulsory_share_2023"], "covid21": R["covid"]["2021"]["median_pct_change"],
         "covid21_ci": R["covid"]["2021"]["ci95"], "r2": R["spending_vs_life_expectancy_2019"]["r_squared_quadratic_in_log10_spend"],
         "gain": R["spending_vs_life_expectancy_2019"]["life_exp_gain_per_doubling_at_300usd"], "gain3000": R["spending_vs_life_expectancy_2019"]["life_exp_gain_per_doubling_at_3000usd"]}
html = (ROOT / "src" / "dashboard_template.html").read_text().replace("__DATA__", json.dumps(rows, separators=(",", ":"))).replace("__FACTS__", json.dumps(facts))
(ROOT / "dashboard").mkdir(exist_ok=True); (ROOT / "dashboard" / "index.html").write_text(html)
print("dashboard written,", len(html) // 1024, "KB")
