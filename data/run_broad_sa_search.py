#!/usr/bin/env python3
"""Broader search: ALL South Africa GKG records for Sept 20 - Oct 10, 2026."""

import os
from google.cloud import bigquery
import pandas as pd

PROJECT = "gen-lang-client-0418790586"
client = bigquery.Client(project=PROJECT)

# Get ALL SA records for the period to understand coverage
query = """
SELECT 
  GKGRECORDID,
  DATE,
  SourceCommonName,
  DocumentIdentifier,
  V2Themes
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE _PARTITIONDATE BETWEEN '2026-09-20' AND '2026-10-10'
  AND (V2Themes LIKE '%SOUTH_AFRICA%' OR V2Locations LIKE '%SOUTH_AFRICA%')
ORDER BY DATE DESC
LIMIT 100;
"""

print("📡 Getting ALL South Africa GKG records for Sept 20 - Oct 10, 2026...")

try:
    df = client.query(query).to_dataframe()
    print(f"✅ Total SA records in period: {len(df)}")
    
    if len(df) > 0:
        # Analyze themes
        all_themes = []
        for themes in df['V2Themes'].dropna():
            all_themes.extend([t.strip() for t in str(themes).split(';') if t.strip()])
        
        from collections import Counter
        theme_counts = Counter(all_themes)
        print(f"\n🎯 Top 30 themes in SA coverage:")
        for theme, count in theme_counts.most_common(30):
            print(f"  {theme}: {count}")
        
        # Show sources
        print(f"\n📰 Sources:")
        source_counts = df['SourceCommonName'].value_counts()
        for src, cnt in source_counts.head(15).items():
            print(f"  {src}: {cnt}")
        
        # Check for any farm/rural/violence themes
        print(f"\n🔍 Searching for violence/rural/farm themes in ALL records...")
        violence_themes = [t for t in theme_counts.keys() if any(kw in t.upper() for kw in 
            ['FARM', 'RURAL', 'VIOLENCE', 'CRIME', 'MURDER', 'GENOCIDE', 'ATTACK', 'KILL', 'CONFLICT', 'ETHNIC'])]
        print(f"  Violence-related themes found: {len(violence_themes)}")
        for t in violence_themes:
            print(f"    {t}: {theme_counts[t]}")
        
        # Save full results
        output_path = "/home/user/pieter-kb/GDELT/all_sa_coverage.csv"
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"\n💾 Full results saved to: {output_path}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()