#!/usr/bin/env python3
"""Broader diplomatic/policy query: 2020-2026 SA farm violence international dimension."""

import os
from google.cloud import bigquery
import pandas as pd

PROJECT = "gen-lang-client-0418790586"
client = bigquery.Client(project=PROJECT)

# Broader query: diplomatic, policy, sanctions, key actors
query = """
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
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE _PARTITIONDATE BETWEEN '2020-01-01' AND '2026-12-31'
  AND (V2Themes LIKE '%SOUTH_AFRICA%' OR V2Locations LIKE '%SOUTH_AFRICA%')
  AND (
    -- Diplomatic/policy intervention themes
    V2Themes LIKE '%DIPLOMATIC_DISPUTE%'
    OR V2Themes LIKE '%SANCTIONS%'
    OR V2Themes LIKE '%VISA_RESTRICTIONS%'
    OR V2Themes LIKE '%MAGNITSKY%'
    OR V2Themes LIKE '%FOREIGN_POLICY%'
    OR V2Themes LIKE '%HUMAN_RIGHTS%'
    OR V2Themes LIKE '%REFUGEE%'
    OR V2Themes LIKE '%ASYLUM%'
    OR V2Themes LIKE '%INTERNATIONAL_RELATIONS%'
    OR V2Themes LIKE '%DIPLOMACY%'
    -- Genocide/violence themes
    OR V2Themes LIKE '%GENOCIDE%'
    OR V2Themes LIKE '%ETHNIC_CLEANSING%'
    OR V2Themes LIKE '%CRIMES_AGAINST_HUMANITY%'
    OR V2Themes LIKE '%WAR_CRIMES%'
    -- Land/expropriation themes
    OR V2Themes LIKE '%LAND_REFORM%'
    OR V2Themes LIKE '%EXPROPRIATION%'
    OR V2Themes LIKE '%LAND_REDISTRIBUTION%'
    OR V2Themes LIKE '%PROPERTY_RIGHTS%'
  )
ORDER BY DATE DESC
LIMIT 500;
"""

print("📡 Querying diplomatic/policy dimension: 2020-2026...")
print("🔍 Themes: diplomatic disputes, sanctions, visa restrictions, human rights, refugee, genocide, land reform")

try:
    # Dry run
    dry_run = bigquery.QueryJobConfig(dry_run=True)
    job = client.query(query, job_config=dry_run)
    print(f"💰 Dry run: {job.total_bytes_processed / 1e9:.2f} GB")
    
    # Actual query
    df = client.query(query).to_dataframe()
    print(f"✅ Query complete! Rows returned: {len(df)}")
    
    if len(df) > 0:
        output_path = "/home/user/pieter-kb/GDELT/diplomatic_policy_2020_2026.csv"
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"💾 Saved to: {output_path}")
        
        # Quick analysis
        print(f"\n📊 Year distribution:")
        df['year'] = df['DATE'].astype(str).str[:4]
        print(df['year'].value_counts().sort_index())
        
        print(f"\n📰 Top sources:")
        print(df['SourceCommonName'].value_counts().head(20))
        
        # Theme analysis
        all_themes = []
        for themes in df['V2Themes'].dropna():
            all_themes.extend([t.strip() for t in str(themes).split(';') if t.strip()])
        
        from collections import Counter
        theme_counts = Counter(all_themes)
        target_themes = [t for t in theme_counts.keys() if any(kw in t for kw in 
            ['DIPLOMATIC', 'SANCTION', 'VISA', 'MAGNITSKY', 'HUMAN_RIGHTS', 'REFUGEE', 'ASYLUM',
             'GENOCIDE', 'ETHNIC_CLEANSING', 'CRIMES_AGAINST', 'WAR_CRIMES',
             'LAND_REFORM', 'EXPROPRIATION', 'LAND_REDISTRIBUTION', 'PROPERTY_RIGHTS',
             'FOREIGN_POLICY', 'INTERNATIONAL_RELATIONS', 'DIPLOMACY'])]
        
        print(f"\n🎯 Target theme frequencies:")
        for t in sorted(target_themes, key=lambda x: -theme_counts[x]):
            print(f"  {t}: {theme_counts[t]}")
        
        # Key persons/orgs
        all_persons = []
        for persons in df['V2Persons'].dropna():
            all_persons.extend([p.strip() for p in str(persons).split(';') if p.strip()])
        person_counts = Counter(all_persons)
        key_persons = [p for p in person_counts.keys() if any(kw in p.upper() for kw in 
            ['TRUMP', 'BIDEN', 'BLINKEN', 'RAMAPHOSA', 'ROETS', 'KRIEL', 'AFRIFORUM', 'PUTIN', 'XI', 'LULA'])]
        print(f"\n👤 Key persons mentioned:")
        for p in sorted(key_persons, key=lambda x: -person_counts[x]):
            print(f"  {p}: {person_counts[x]}")
            
        all_orgs = []
        for orgs in df['V2Organizations'].dropna():
            all_orgs.extend([o.strip() for o in str(orgs).split(';') if o.strip()])
        org_counts = Counter(all_orgs)
        key_orgs = [o for o in org_counts.keys() if any(kw in o.upper() for kw in 
            ['WHITE_HOUSE', 'STATE_DEPT', 'DIRCO', 'AFRIFORUM', 'ANC', 'SACP', 'ISS', 'BRICS', 'UN', 'ICC', 'ICJ'])]
        print(f"\n🏛️ Key organizations mentioned:")
        for o in sorted(key_orgs, key=lambda x: -org_counts[x]):
            print(f"  {o}: {org_counts[x]}")
            
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()