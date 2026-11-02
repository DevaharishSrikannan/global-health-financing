-- Country-year analytical panel built from the five raw tables.
-- Conditional aggregation pivots the long WHO tables into one row per country and year.

DROP TABLE IF EXISTS panel;
CREATE TABLE panel AS
WITH spend AS (
    SELECT iso3_code AS iso3, country_name AS country, year,
           MAX(CASE WHEN indicator_code = 'che_usd2023'   THEN value END) AS che_usd,
           MAX(CASE WHEN indicator_code = 'gghed_che'     THEN value END) AS gov_share,
           MAX(CASE WHEN indicator_code = 'pvtd_che'      THEN value END) AS pvt_share,
           MAX(CASE WHEN indicator_code = 'ext_che'       THEN value END) AS ext_share
    FROM ghed_spending
    GROUP BY iso3_code, country_name, year
),
schemes AS (
    SELECT iso3_code AS iso3, year,
           MAX(CASE WHEN indicator_code = 'hf1_che' THEN value END) AS compulsory_share,
           MAX(CASE WHEN indicator_code = 'hf2_che' THEN value END) AS voluntary_share,
           MAX(CASE WHEN indicator_code = 'hf3_che' THEN value END) AS oop_share,
           MAX(CASE WHEN indicator_code = 'hf4_che' THEN value END) AS row_share_raw,
           MAX(CASE WHEN indicator_code = 'hfnec_che' THEN value END) AS nec_share_raw
    FROM ghed_schemes
    GROUP BY iso3_code, year
),
purpose AS (
    SELECT iso3_code AS iso3, year,
           MAX(CASE WHEN indicator_code = 'hc1_che' THEN value END) AS curative_share,
           MAX(CASE WHEN indicator_code = 'hc6_che' THEN value END) AS preventive_share
    FROM ghed_purpose
    GROUP BY iso3_code, year
)
SELECT s.iso3, s.country, s.year,
       s.che_usd,
       p.population,
       s.che_usd * 1.0 / p.population AS che_pc_usd,          -- constant 2023 US$ per person
       s.gov_share, s.pvt_share, s.ext_share,
       c.compulsory_share, c.voluntary_share, c.oop_share,
       -- WHO leaves hf4 / hfnec blank when the scheme does not exist; the five shares then still sum to 100,
       -- so a blank is a true zero. It is kept as NULL if the shares do not add up.
       CASE WHEN c.row_share_raw IS NOT NULL THEN c.row_share_raw
            WHEN ABS(COALESCE(c.compulsory_share,0)+COALESCE(c.voluntary_share,0)+COALESCE(c.oop_share,0)+COALESCE(c.nec_share_raw,0)-100) <= 1 THEN 0.0 END AS row_share,
       u.curative_share, u.preventive_share,
       l.life_expectancy
FROM spend s
LEFT JOIN schemes c USING (iso3, year)
LEFT JOIN purpose u USING (iso3, year)
LEFT JOIN population p ON p.iso3 = s.iso3 AND p.year = s.year
LEFT JOIN life_expectancy l ON l.iso3 = s.iso3 AND l.year = s.year;

CREATE INDEX idx_panel ON panel (iso3, year);
