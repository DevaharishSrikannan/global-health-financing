# Who pays for health care? Financing patterns in 195 countries, 2000 to 2023

An analysis of how countries finance health care, built as a SQL-first pipeline with Python statistics, figures and an interactive dashboard.

**Questions**

1. How does the financing mix (compulsory schemes, voluntary schemes, out-of-pocket) differ by spending level, and how has it moved since 2000?
2. What happened to spending and out-of-pocket shares after the pandemic began?
3. How strongly is spending per person associated with life expectancy, and where does Ireland sit?
4. Do countries fall into distinct financing profiles?

**Interactive dashboard:** `dashboard/index.html` (single file, opens offline).

## Findings

- Out-of-pocket share falls as compulsory financing rises: Spearman rho -0.84 across 191 countries in 2023 (bootstrap 95% CI -0.89 to -0.77). Its link with spending per person is weaker (rho -0.47, CI -0.58 to -0.36).
- In 2023, 56 of 191 countries still paid 40% or more of health spending out of pocket. Their median spend was about US$94 per person.
- Median out-of-pocket share fell in every spending tier between 2000 and 2023 (lowest tier 56% to 45%, highest tier 20% to 15%), but the gap between tiers remains large.
- Spending per person in 2021 was a median 10.5% above 2019 (95% CI 7.6% to 13.0%; Wilcoxon signed-rank p < 0.001), and about 80% of countries were higher. By 2023 the median was 8.3% above 2019. Median out-of-pocket share moved down by about 1.1 points in 2021.
- A quadratic in log spend explains about 69% of the variation in 2019 life expectancy. One doubling of spending is associated with roughly 2.7 years near US$300 per person and 2.3 years near US$3,000.
- K-means on the four scheme shares splits countries into a mostly compulsory group (118 countries, median profile about 71% compulsory, 20% out-of-pocket) and a mostly out-of-pocket group (76 countries, about 50% out-of-pocket). Bootstrap stability is high (median adjusted Rand index 0.94), though silhouette scores are similar for several k, so two groups is a simplification rather than a sharp boundary.
- Ireland: second highest spend per person in the EU27 in 2023 (about US$6,800 vs an EU median of about US$3,000) with a lower out-of-pocket share than the EU median (11% vs 18%) and a high voluntary share (12% vs 5%). Its life expectancy sits close to the fitted curve (residual +0.1 years, 95% CI -0.8 to +1.1), so spending level alone does not distinguish it.

## Limitations

- Everything here is descriptive and associational. Nothing supports a causal claim about spending and life expectancy.
- Spending is in constant 2023 US$ converted at market rates, not purchasing power parity.
- Small island states with very low life expectancy for their spending (for example Palau, Nauru, Tuvalu) pull the curve down; the fit is not robust to them and I did not model them separately.
- Where WHO leaves the rest-of-world share blank, the other shares sum to 100, so blanks are treated as zero. A small number of country-years (about 1%) have a shortfall because of spending WHO classes as "not elsewhere classified"; these are kept and flagged by the tests.
- Life expectancy is from a different source than spending; the two series are matched on country code and year only.

## Skills shown

SQL (CTEs, conditional-aggregation pivots, window functions: NTILE, LAG, RANK), pandas, data validation tests, nonparametric statistics with bootstrap confidence intervals, regression, clustering with stability checks, matplotlib, and a dependency-free interactive dashboard.

## Reproduce

```
pip install -r requirements.txt
python3 src/fetch_data.py        # downloads the five source files into data/raw/
python3 src/build_database.py    # SQLite database and the analytical panel (sql/01_panel.sql)
python3 src/analysis.py          # views (sql/02_views.sql), statistics, outputs/*.csv and results.json
python3 tests/test_data_quality.py
python3 src/make_figures.py
python3 src/build_dashboard.py
```

## Data and attribution

Raw files are downloaded at run time and are not stored in this repository.

- WHO Global Health Expenditure Database, as published in the TidyTuesday 2026-04-21 dataset.
- World Bank total population, via the open `datasets/population` repository.
- Life expectancy at birth from Our World in Data, via TidyTuesday 2023-12-05.

Check each source's licence and terms before reusing derived tables.
