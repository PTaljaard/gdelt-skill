#!/usr/bin/env python3
"""Run quick test query to check for White Cross / Washington memorial coverage in GKG."""

import os
from google.cloud import bigquery
import pandas as pd

PROJECT = "gen-lang-client-0418790586"
client = bigquery.Client(project=PROJECT)

# Quick test query - broader search for memorial/Washington/AfriForum coverage
query = """
SELECT 
  GKGRECORDID,
  DATE,
  SourceCommonName,
  DocumentIdentifier,
  V2Themes,
  V2Tone
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE _PARTITIONDATE BETWEEN '2026-09-20' AND '2026-10-10'
  AND (V2Themes LIKE '%SOUTH_AFRICA%' OR V2Locations LIKE '%SOUTH_AFRICA%')
  AND (
    LOWER(DocumentIdentifier) LIKE '%washington%' 
    OR LOWER(DocumentIdentifier) LIKE '%memorial%'
    OR LOWER(DocumentIdentifier) LIKE '%cross%'
    OR LOWER(DocumentIdentifier) LIKE '%afriforum%'
    OR LOWER(DocumentIdentifier) LIKE '%white%cross%'
    OR LOWER(DocumentIdentifier) LIKE '%lex%libertas%'
    OR LOWER(DocumentIdentifier) LIKE '%roets%'
  )
ORDER BY DATE DESC
LIMIT 50;
"""

print("📡 Running quick test query for memorial/Washington/AfriForum coverage...")
print("🔍 Partition range: Sept 20 - Oct 10, 2026")

try:
    # Dry run
    dry_run = bigquery.QueryJobConfig(dry_run=True)
    job = client.query(query, job_config=dry_run)
    print(f"💰 Dry run: {job.total_bytes_processed / 1e6:.2f} MB")
    
    # Actual query
    df = client.query(query).to_dataframe()
    print(f"✅ Query complete! Rows returned: {len(df)}")
    
    if len(df) > 0:
        output_path = "/home/user/pieter-kb/GDELT/quick_test_results.csv"
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"💾 Results saved to: {output_path}")
        
        print(f"\n📋 Sample data:")
        for _, row in df.head(10).iterrows():
            print(f"\n  Date: {row['DATE']}")
            print(f"  Source: {row['SourceCommonName']}")
            print(f"  URL: {row['DocumentIdentifier']}")
            print(f"  Themes: {str(row['V2Themes'])[:150]}...")
            print(f"  Tone: {str(row['V2Tone'])[:80]}...")
    else:
        print("⚠️  No results found with those keywords in DocumentIdentifier")
        print("   Trying broader theme-only search...")
        
        # Fallback: Just theme-based search for the period
        fallback_query = """
        SELECT 
          GKGRECORDID,
          DATE,
          SourceCommonName,
          DocumentIdentifier,
          V2Themes,
          V2Tone
        FROM `gdelt-bq.gdeltv2.gkg_partitioned`
        WHERE _PARTITIONDATE BETWEEN '2026-09-20' AND '2026-10-10'
          AND (V2Themes LIKE '%SOUTH_AFRICA%' OR V2Locations LIKE '%SOUTH_AFRICA%')
          AND (V2Themes LIKE '%RURAL_SAFETY%' OR V2Themes LIKE '%CRIME_VIOLENCE%' 
               OR V2Themes LIKE '%ETHNIC_CONFLICT%' OR V2Themes LIKE '%GENOCIDE%')
        ORDER BY DATE DESC
        LIMIT 20;
        """
        
        df2 = client.query(fallback_query).to_dataframe()
        print(f"\n📋 Fallback (theme-only) results: {len(df2)} rows")
        for _, row in df2.head(5).iterrows():
            print(f"  {row['DATE']} | {row['SourceCommonName']} | {row['DocumentIdentifier'][:80]}")
            print(f"    Themes: {str(row['V2Themes'])[:120]}...")
            
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()