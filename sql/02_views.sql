-- Analytical views on top of `panel`. Window functions and CTEs; no Python logic needed to reproduce these tables.

-- Spending tier: quartile of 2019 (pre-pandemic) health spending per person. Tier 1 = lowest spenders.
DROP VIEW IF EXISTS v_tier;
CREATE VIEW v_tier AS
SELECT iso3, country, che_pc_usd AS pc_2019,
       NTILE(4) OVER (ORDER BY che_pc_usd) AS tier
FROM panel
WHERE year = 2019 AND che_pc_usd IS NOT NULL;

-- Change from the pre-pandemic baseline (2019) to 2021 and 2023, per country.
DROP VIEW IF EXISTS v_change;
CREATE VIEW v_change AS
WITH b AS (SELECT iso3, che_pc_usd AS pc, compulsory_share AS comp, oop_share AS oop FROM panel WHERE year = 2019),
     y21 AS (SELECT iso3, che_pc_usd AS pc, compulsory_share AS comp, oop_share AS oop FROM panel WHERE year = 2021),
     y23 AS (SELECT iso3, che_pc_usd AS pc, compulsory_share AS comp, oop_share AS oop FROM panel WHERE year = 2023)
SELECT t.iso3, t.country, t.tier,
       b.pc AS pc_2019, y21.pc AS pc_2021, y23.pc AS pc_2023,
       100.0 * (y21.pc / b.pc - 1) AS pct_change_2021,
       100.0 * (y23.pc / b.pc - 1) AS pct_change_2023,
       y21.comp - b.comp AS d_compulsory_pp_2021, y23.comp - b.comp AS d_compulsory_pp_2023,
       y21.oop  - b.oop  AS d_oop_pp_2021,        y23.oop  - b.oop  AS d_oop_pp_2023
FROM v_tier t
JOIN b   ON b.iso3   = t.iso3
JOIN y21 ON y21.iso3 = t.iso3
JOIN y23 ON y23.iso3 = t.iso3
WHERE b.pc > 0;

-- Year-on-year growth in spending per person, with the largest single-year jumps flagged.
DROP VIEW IF EXISTS v_yoy;
CREATE VIEW v_yoy AS
SELECT iso3, country, year, che_pc_usd,
       100.0 * (che_pc_usd / LAG(che_pc_usd) OVER (PARTITION BY iso3 ORDER BY year) - 1) AS yoy_pct
FROM panel
WHERE che_pc_usd IS NOT NULL;

-- Latest-year league table: rank by out-of-pocket share and by spending per person.
DROP VIEW IF EXISTS v_latest;
CREATE VIEW v_latest AS
SELECT iso3, country, year, che_pc_usd, compulsory_share, voluntary_share, oop_share,
       RANK() OVER (ORDER BY oop_share DESC)  AS oop_rank_high_to_low,
       RANK() OVER (ORDER BY che_pc_usd DESC) AS spend_rank_high_to_low,
       COUNT(*) OVER () AS n_countries
FROM panel
WHERE year = 2023 AND oop_share IS NOT NULL AND che_pc_usd IS NOT NULL;

-- Ireland against the EU27 (the eu27 table is created by the Python build step).
DROP VIEW IF EXISTS v_eu;
CREATE VIEW v_eu AS
SELECT p.iso3, p.country, p.year, p.che_pc_usd, p.compulsory_share, p.voluntary_share, p.oop_share,
       RANK() OVER (PARTITION BY p.year ORDER BY p.che_pc_usd DESC)   AS spend_rank,
       RANK() OVER (PARTITION BY p.year ORDER BY p.oop_share DESC)    AS oop_rank,
       COUNT(*) OVER (PARTITION BY p.year)                            AS n_eu
FROM panel p
JOIN eu27 e ON e.iso3 = p.iso3
WHERE p.che_pc_usd IS NOT NULL AND p.oop_share IS NOT NULL;
