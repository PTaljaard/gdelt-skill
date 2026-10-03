#!/usr/bin/env python3
"""Get ALL SA articles that have ANY of the target themes individually."""

import os
from google.cloud import bigquery
import pandas as pd

PROJECT = "gen-lang-client-0418790586"
client = bigquery.Client(project=PROJECT)

# Get all SA articles with any of the 4 target themes
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
    V2Themes LIKE '%GENOCIDE%'
    OR V2Themes LIKE '%AFRIKANER%'
    OR V2Themes LIKE '%FARMERS%'
    OR V2Themes LIKE '%RURAL%'
  )
ORDER BY DATE DESC
LIMIT 100;
"""

print("📡 Getting ALL SA articles with ANY target theme (GENOCIDE, AFRIKANER, FARMERS, RURAL)...")

try:
    df = client.query(query).to_dataframe()
    print(f"✅ Total SA articles with at least 1 target theme: {len(df)}")
    
    if len(df) > 0:
        # Tag each row with which themes it has
        def tag_themes(themes_str):
            tags = []
            if 'GENOCIDE' in str(themes_str).upper():
                tags.append('GENOCIDE')
            if 'AFRIKANER' in str(themes_str).upper():
                tags.append('AFRIKANER')
            if 'FARMERS' in str(themes_str).upper():
                tags.append('FARMERS')
            if 'RURAL' in str(themes_str).upper():
                tags.append('RURAL')
            return ' + '.join(tags) if tags else 'NONE'
        
        df['matched_themes'] = df['V2Themes'].apply(tag_themes)
        
        # Save to CSV
        output_path = "/home/user/pieter-kb/GDELT/hitl_review_urls.csv"
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"\n💾 Saved to: {output_path}")
        
        print(f"\n📋 Articles for HITL review (grouped by theme combo):")
        for combo, group in df.groupby('matched_themes'):
            print(f"\n  === {combo} ({len(group)} articles) ===")
            for _, row in group.iterrows():
                print(f"    {row['DATE']} | {row['SourceCommonName']}")
                print(f"      URL: {row['DocumentIdentifier']}")
                print(f"      Tone: {str(row['V2Tone'])[:80]}...")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()