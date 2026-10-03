# GDELT BigQuery Query Patterns

This document covers optimized BigQuery query patterns for the GDELT 2.0 tables, designed for cost-effective historical analysis at PhD scale.

## Table Overview

| Table | Coverage | Partitioning | Key Columns |
|-------|----------|--------------|-------------|
| `gdelt-bq.gdeltv2.events` | 1979–present | `DATEADDED` (INT64 YYYYMMDDHHMMSS) | GLOBALEVENTID, Actor1/2, EventCode, GoldsteinScale, AvgTone, ActionGeo |
| `gdelt-bq.gdeltv2.mentions` | 2015–present | `MentionTimeDate` (INT64) | GLOBALEVENTID, MentionSourceName, MentionIdentifier, MentionDocTone |
| `gdelt-bq.gdeltv2.gkg` | 2015–present | `DATE` (INT64 YYYYMMDD) | GKGRECORDID, Themes, V2Themes, Locations, Persons, Organizations, V2Tone |

## Cost Optimization Rules

### 1. Always Filter by Partition Column First

```sql
-- ✅ GOOD: Partition pruning on DATE column
SELECT * FROM `gdelt-bq.gdeltv2.events`
WHERE DATEADDED >= 19860101000000 AND DATEADDED <= 19861231235959
  AND ActionGeo_CountryCode = 'SF';

-- ❌ BAD: Full table scan
SELECT * FROM `gdelt-bq.gdeltv2.events`
WHERE ActionGeo_CountryCode = 'SF';
```

### 2. Use Integer Date Ranges (Not STRING Parsing)

```sql
-- ✅ GOOD: Integer comparison on partition column
WHERE DATEADDED BETWEEN 19860101000000 AND 19861231235959

-- ❌ BAD: String parsing defeats partitioning
WHERE PARSE_DATE('%Y%m%d%H%M%S', CAST(DATEADDED AS STRING)) 
      BETWEEN '1986-01-01' AND '1986-12-31'
```

### 3. Select Only Needed Columns

```sql
-- ✅ GOOD: ~50 MB for 1 year of SA events
SELECT GLOBALEVENTID, DATEADDED, Actor1Name, Actor2Name, EventCode, 
       GoldsteinScale, AvgTone, ActionGeo_CountryCode, ActionGeo_Lat, ActionGeo_Long, SOURCEURL
FROM `gdelt-bq.gdeltv2.events`
WHERE DATEADDED BETWEEN 19860101000000 AND 19861231235959
  AND ActionGeo_CountryCode = 'SF';

-- ❌ BAD: SELECT * scans all columns (~500 MB for same query)
SELECT * FROM ...
```

### 4. Use Dry Run Before Execution

```python
from google.cloud import bigquery

client = bigquery.Client()
job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
query_job = client.query(your_sql, job_config=job_config)
print(f"Bytes to be processed: {query_job.total_bytes_processed / 1e9:.2f} GB")
print(f"Estimated cost: ${query_job.total_bytes_processed / 1e12 * 5:.4f}")
```

## South Africa Query Templates

### Historical Events (1986–2014): Apartheid to Transition

```sql
-- Apartheid-era rural violence (CAMEO codes 18=Assault, 19=Threaten, 20=Mass Violence)
SELECT 
  GLOBALEVENTID,
  DATEADDED,
  Actor1Name, Actor1Code, Actor1CountryCode, Actor1EthnicCode,
  Actor2Name, Actor2Code, Actor2CountryCode, Actor2EthnicCode,
  EventCode, EventBaseCode, EventRootCode,
  GoldsteinScale, NumMentions, NumSources, NumArticles, AvgTone,
  ActionGeo_FullName, ActionGeo_Lat, ActionGeo_Long, SOURCEURL
FROM `gdelt-bq.gdeltv2.events`
WHERE DATEADDED BETWEEN 19860101000000 AND 19941231235959  -- Apartheid to 1994 election
  AND ActionGeo_CountryCode = 'SF'
  AND EventRootCode IN ('18', '19', '20')  -- Violence/threat codes
  AND (Actor1EthnicCode IN ('AFR', 'BUE') OR Actor2EthnicCode IN ('AFR', 'BUE'))
ORDER BY DATEADDED;
```

### Modern GKG (2015–present): Narrative Analysis

```sql
-- Theme-based query with V2Tone for sentiment analysis
SELECT
  GKGRECORDID,
  DATE,
  SourceCommonName,
  DocumentIdentifier,
  V2Themes,
  V2Locations,
  V2Persons,
  V2Organizations,
  V2Tone
FROM `gdelt-bq.gdeltv2.gkg`
WHERE DATE BETWEEN 20240101 AND 20241231
  AND (
    V2Themes LIKE '%SOUTH_AFRICA%' 
    OR V2Locations LIKE '%SOUTH_AFRICA%'
    OR LOWER(DocumentIdentifier) LIKE '%south%africa%'
  )
  AND (
    V2Themes LIKE '%RURAL_SAFETY%' 
    OR V2Themes LIKE '%CRIME_VIOLENCE%' 
    OR V2Themes LIKE '%ETHNIC_CONFLICT%'
    OR V2Themes LIKE '%GENOCIDE%'
  )
ORDER BY DATE DESC;
```

### Partitioned Date Loop (Python)

```python
from google.cloud import bigquery
import pandas as pd

client = bigquery.Client()

def query_monthly_batches(start_year, end_year, country_code='SF'):
    """Query GDELT events in monthly batches to stay within free tier."""
    all_results = []
    
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            month_str = f"{year}{month:02d}"
            start_int = int(month_str + "01000000")
            end_day = 31 if month in [1,3,5,7,8,10,12] else 30
            if month == 2:
                end_day = 29 if year % 4 == 0 else 28
            end_int = int(f"{month_str}{end_day:02d}235959")
            
            query = f"""
            SELECT GLOBALEVENTID, DATEADDED, Actor1Name, Actor2Name, 
                   EventCode, GoldsteinScale, AvgTone, 
                   ActionGeo_CountryCode, ActionGeo_Lat, ActionGeo_Long, SOURCEURL
            FROM `gdelt-bq.gdeltv2.events`
            WHERE DATEADDED BETWEEN {start_int} AND {end_int}
              AND ActionGeo_CountryCode = '{country_code}'
            """
            
            # Dry run first
            dry_run = bigquery.QueryJobConfig(dry_run=True)
            job = client.query(query, job_config=dry_run)
            mb = job.total_bytes_processed / 1e6
            
            if mb > 100:  # Skip if >100 MB (unexpected for single month)
                print(f"⚠️  {month_str}: {mb:.1f} MB - skipping")
                continue
                
            df = client.query(query).to_dataframe()
            all_results.append(df)
            print(f"✅ {month_str}: {len(df)} rows, {mb:.1f} MB")
    
    return pd.concat(all_results, ignore_index=True) if all_results else pd.DataFrame()
```

## CAMEO Code Reference for SA Violence

| Root Code | Description | Relevance |
|-----------|-------------|-----------|
| 18 | Assault | Farm attacks, physical violence |
| 19 | Threaten | Verbal threats, intimidation |
| 20 | Unconventional Mass Violence | Genocide claims, mass killings |
| 17 | Coerce | Political pressure, forced displacement |
| 14 | Protest | Farm protests, land reform demonstrations |

### Ethnic Codes (Actor1EthnicCode / Actor2EthnicCode)

| Code | Group |
|------|-------|
| AFR | Afrikaner |
| BUE | Boer |
| ZUL | Zulu |
| XHO | Xhosa |
| SOT | Sotho |

## Free Tier Budgeting

| Query Type | Typical Scan | Monthly Free Tier (1 TB) |
|------------|--------------|--------------------------|
| 1 year SA events | ~500 MB | 2 years |
| 1 month SA GKG | ~50 MB | 20 months |
| Full 40-year SA events | ~20 GB | Use monthly batches |

**Pro tip**: Run monthly batches as separate queries — each gets its own 1 TB free tier allocation.

## Export for LLM Processing

```sql
-- Export GKG records with URLs for LLM claim extraction
SELECT
  GKGRECORDID,
  DATE,
  SourceCommonName,
  DocumentIdentifier,
  V2Themes,
  V2Tone,
  V2Persons,
  V2Organizations
FROM `gdelt-bq.gdeltv2.gkg`
WHERE DATE BETWEEN 20240101 AND 20241231
  AND V2Themes LIKE '%SOUTH_AFRICA%'
  AND V2Themes LIKE '%CRIME_VIOLENCE%'
ORDER BY DATE DESC;
```

Feed `DocumentIdentifier` URLs to LLM pipeline for:
- Claimant identification (AfriForum, DIRCO, ISS, etc.)
- Stance classification (GENOCIDE / CRIMINALITY / POLITICAL_VIOLENCE / DISPUTED)
- Evidence extraction (URLs, reports, statistics cited)
- Certainty scoring (0.0–1.0)