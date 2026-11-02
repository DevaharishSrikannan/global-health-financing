"""Checks on the built panel. Run after build_database.py: python3 tests/test_data_quality.py"""
import sqlite3
from pathlib import Path
import pandas as pd

DB = Path(__file__).resolve().parents[1] / "outputs" / "health_financing.db"
p = pd.read_sql("SELECT * FROM panel", sqlite3.connect(DB))
fails = []

def check(name, ok):
    print(("ok   " if ok else "FAIL ") + name)
    if not ok: fails.append(name)

check("one row per country-year", not p.duplicated(["iso3", "year"]).any())
check("years span 2000-2023", p.year.min() == 2000 and p.year.max() == 2023)
check("spending is non-negative", (p.che_usd.dropna() >= 0).all())
check("shares lie between 0 and 100", ((p[["compulsory_share", "voluntary_share", "oop_share", "gov_share"]].dropna() >= 0) & (p[["compulsory_share", "voluntary_share", "oop_share", "gov_share"]].dropna() <= 100.5)).all().all())
s = p[["gov_share", "pvt_share", "ext_share"]].dropna().sum(axis=1)
check("government + private + external shares sum to 100", ((s - 100).abs() <= 1).all())
tot = p[["compulsory_share", "voluntary_share", "oop_share", "row_share"]].sum(axis=1, min_count=4)
check("four scheme shares never exceed 100", (tot.dropna() <= 100.5).all())
# A shortfall means WHO's 'not elsewhere classified' scheme is non-zero; it is not part of this panel.
check("scheme shortfalls (unclassified spending) affect under 2% of country-years", ((tot < 98.5).sum() / tot.notna().sum()) < 0.02)
check("every country with scheme data has a resolved rest-of-world share", p[p.oop_share.notna()].row_share.notna().all())
check("per-person spend is in a plausible range", p.che_pc_usd.dropna().between(1, 20000).all())
check("life expectancy is in a plausible range", p.life_expectancy.dropna().between(30, 95).all())
check("Ireland present in 2019 with per-person spend above 4000 US$", p[(p.iso3 == "IRL") & (p.year == 2019)].che_pc_usd.iloc[0] > 4000)
raise SystemExit(1 if fails else 0)
