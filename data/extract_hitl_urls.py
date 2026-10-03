#!/usr/bin/env python3
"""Extract specific URLs with GENOCIDE + AFRIKANER + FARMERS + RURAL theme combo."""

import os
from google.cloud import bigquery
import pandas as pd

PROJECT = "gen-lang-client-0418790586"
client = bigquery.Client(project=PROJECT)

# Query for the specific theme combination
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
  AND V2Themes LIKE '%GENOCIDE%'
  AND V2Themes LIKE '%AFRIKANER%'
  AND V2Themes LIKE '%FARMERS%'
  AND V2Themes LIKE '%RURAL%'
ORDER BY DATE DESC
LIMIT 50;
"""

print("📡 Querying for GENOCIDE + AFRIKANER + FARMERS + RURAL theme combo...")

try:
    df = client.query(query).to_dataframe()
    print(f"✅ Rows with all 4 themes: {len(df)}")
    
    if len(df) == 0:
        print("⚠️  No articles have ALL 4 themes simultaneously.")
        print("   Trying pairwise combinations...")
        
        # Try combinations
        combos = [
            ("GENOCIDE + AFRIKANER", "%GENOCIDE%", "%AFRIKANER%"),
            ("GENOCIDE + FARMERS", "%GENOCIDE%", "%FARMERS%"),
            ("GENOCIDE + RURAL", "%GENOCIDE%", "%RURAL%"),
            ("AFRIKANER + FARMERS", "%AFRIKANER%", "%FARMERS%"),
            ("AFRIKANER + RURAL", "%AFRIKANER%", "%RURAL%"),
            ("FARMERS + RURAL", "%FARMERS%", "%RURAL%"),
        ]
        
        all_results = []
        for label, theme1, theme2 in combos:
            q = f"""
            SELECT GKGRECORDID, DATE, SourceCommonName, DocumentIdentifier, V2Themes, V2Tone
            FROM `gdelt-bq.gdeltv2.gkg_partitioned`
            WHERE _PARTITIONDATE BETWEEN '2026-09-20' AND '2026-10-10'
              AND (V2Themes LIKE '%SOUTH_AFRICA%' OR V2Locations LIKE '%SOUTH_AFRICA%')
              AND V2Themes LIKE '{theme1}'
              AND V2Themes LIKE '{theme2}'
            ORDER BY DATE DESC
            LIMIT 20;
            """
            df_combo = client.query(q).to_dataframe()
            if len(df_combo) > 0:
                df_combo['theme_combo'] = label
                all_results.append(df_combo)
                print(f"  {label}: {len(df_combo)} articles")
        
        if all_results:
            df = pd.concat(all_results, ignore_index=True).drop_duplicates(subset=['GKGRECORDID'])
            print(f"\n✅ Total unique articles with at least 2 target themes: {len(df)}")
        else:
            print("  No pairwise matches either.")
    
    if len(df) > 0:
        # Save to CSV
        output_path = "/home/user/pieter-kb/GDELT/hitl_review_urls.csv"
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"\n💾 Saved to: {output_path}")
        
        print(f"\n📋 Articles for HITL review:")
        for _, row in df.iterrows():
            print(f"\n  GKG ID: {row['GKGRECORDID']}")
            print(f"  Date: {row['DATE']}")
            print(f"  Source: {row['SourceCommonName']}")
            print(f"  URL: {row['DocumentIdentifier']}")
            print(f"  Themes: {str(row['V2Themes'])[:200]}...")
            if 'theme_combo' in row:
                print(f"  Matched: {row['theme_combo']}")
            print(f"  Tone: {str(row['V2Tone'])[:100]}...")
            
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()