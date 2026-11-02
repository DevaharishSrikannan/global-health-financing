"""Download the five source files into data/raw/ (skips files that already exist)."""
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
TT = "https://raw.githubusercontent.com/rfordatascience/tidytuesday/main/data"
SOURCES = {
    # WHO Global Health Expenditure Database, as published by TidyTuesday (2026-04-21)
    "health_spending.csv": f"{TT}/2026/2026-04-21/health_spending.csv",
    "financing_schemes.csv": f"{TT}/2026/2026-04-21/financing_schemes.csv",
    "spending_purpose.csv": f"{TT}/2026/2026-04-21/spending_purpose.csv",
    # Life expectancy at birth, Our World in Data, via TidyTuesday (2023-12-05)
    "life_expectancy.csv": f"{TT}/2023/2023-12-05/life_expectancy.csv",
    # Total population, World Bank, via the open "datasets/population" repository
    "population.csv": "https://raw.githubusercontent.com/datasets/population/main/data/population.csv",
}

if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCES.items():
        out = RAW / name
        if out.exists():
            print("have", name); continue
        print("downloading", name); urllib.request.urlretrieve(url, out)
