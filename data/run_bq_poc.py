#!/usr/bin/env python3
"""Run BigQuery POC query and save results to CSV."""

import os
from google.cloud import bigquery
import pandas as pd

# Set project explicitly
PROJECT = "gen-lang-client-0418790586"

client = bigquery.Client(project=PROJECT)

# Fixed query - GKG Date field is YYYYMMDDHHMMSS format
query = """
DECLARE start_ts INT64 DEFAULT 20260920000000;
DECLARE end_ts INT64 DEFAULT 20260930235959;

SELECT
  GKGRECORDID,
  Date,
  -- Extract date from YYYYMMDDHHMMSS format
  DATE(PARSE_TIMESTAMP('%Y%m%d%H%M%S', CAST(Date AS STRING))) AS EventDate,
  SourceCommonName,
  DocumentIdentifier,
  V2Themes,
  V2Locations,
  V2Persons,
  V2Organizations,
  V2Tone,
  SharingImage,
  SocialImageEmbeds,
  TranslationInfo
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE _PARTITIONDATE BETWEEN DATE('2026-09-20') AND DATE('2026-09-30')
  AND CAST(Date AS INT64) BETWEEN start_ts AND end_ts
  AND (V2Themes LIKE '%SOUTH_AFRICA%' 
       OR V2Locations LIKE '%SOUTH_AFRICA%'
       OR LOWER(DocumentIdentifier) LIKE '%south%africa%')
  AND (
    LOWER(V2Themes) LIKE '%rural_safety%' 
    OR LOWER(V2Themes) LIKE '%crime_violence%'
    OR LOWER(V2Themes) LIKE '%ethnic_conflict%'
    OR LOWER(DocumentIdentifier) LIKE '%farm%murder%'
    OR LOWER(DocumentIdentifier) LIKE '%white%cross%'
    OR LOWER(DocumentIdentifier) LIKE '%lex%libertas%'
    OR LOWER(DocumentIdentifier) LIKE '%roets%'
  )
ORDER BY EventDate DESC
LIMIT 500;
"""

print(f"📡 Running BigQuery POC query on project: {PROJECT}")
print("🔍 Querying gdelt-bq.gdeltv2.gkg_partitioned for Sept 20-30, 2026...")

try:
    # Dry run first to check bytes
    dry_run_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    dry_run_job = client.query(query, job_config=dry_run_config)
    print(f"💰 Dry run: {dry_run_job.total_bytes_processed / 1e6:.2f} MB will be scanned")
    
    # Actual query
    job_config = bigquery.QueryJobConfig(use_query_cache=False)
    query_job = client.query(query, job_config=job_config)
    df = query_job.result().to_dataframe()
    
    print(f"✅ Query complete! Rows returned: {len(df)}")
    print(f"💰 Bytes billed: {query_job.total_bytes_billed / 1e6:.2f} MB")
    
    if len(df) > 0:
        # Save to CSV
        output_path = "/home/user/pieter-kb/GDELT/gdelt_poc_results.csv"
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"💾 Results saved to: {output_path}")
        
        # Show summary
        print(f"\n📊 Column summary:")
        print(df.dtypes)
        print(f"\n📋 Sample data (first 5 rows):")
        print(df[['EventDate', 'SourceCommonName', 'DocumentIdentifier', 'V2Themes']].head(5).to_string())
        
        # Theme analysis
        all_themes = []
        for themes in df['V2Themes'].dropna():
            all_themes.extend([t.strip() for t in str(themes).split(';') if t.strip()])
        
        from collections import Counter
        theme_counts = Counter(all_themes)
        print(f"\n🎯 Top 20 themes:")
        for theme, count in theme_counts.most_common(20):
            print(f"  {theme}: {count}")
            
        # Tone analysis
        print(f"\n🎭 V2Tone sample (first 3):")
        for tone in df['V2Tone'].dropna().head(3):
            print(f"  {tone}")
            
    else:
        print("⚠️  No results returned. Try broadening the query.")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()