"""Load the raw CSVs into SQLite and build the analytical panel with sql/01_panel.sql."""
import sqlite3
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DB = ROOT / "outputs" / "health_financing.db"


def build():
    DB.parent.mkdir(exist_ok=True)
    if DB.exists(): DB.unlink()
    con = sqlite3.connect(DB)
    pd.read_csv(RAW / "health_spending.csv").to_sql("ghed_spending", con, index=False)
    pd.read_csv(RAW / "financing_schemes.csv").to_sql("ghed_schemes", con, index=False)
    pd.read_csv(RAW / "spending_purpose.csv").to_sql("ghed_purpose", con, index=False)
    pop = pd.read_csv(RAW / "population.csv").rename(columns={"Country Code": "iso3", "Year": "year", "Value": "population"})
    pop[["iso3", "year", "population"]].to_sql("population", con, index=False)
    le = pd.read_csv(RAW / "life_expectancy.csv").rename(columns={"Code": "iso3", "Year": "year", "LifeExpectancy": "life_expectancy"})
    le[["iso3", "year", "life_expectancy"]].dropna(subset=["iso3"]).to_sql("life_expectancy", con, index=False)
    con.executescript((ROOT / "sql" / "01_panel.sql").read_text())
    con.commit()
    return con


if __name__ == "__main__":
    con = build()
    n, = con.execute("SELECT COUNT(*) FROM panel").fetchone()
    print("panel rows:", n)
    print(pd.read_sql("""SELECT COUNT(*) AS rows, COUNT(che_pc_usd) AS has_per_capita, COUNT(oop_share) AS has_oop,
                         COUNT(life_expectancy) AS has_life_exp, COUNT(preventive_share) AS has_purpose FROM panel""", con).to_string(index=False))
