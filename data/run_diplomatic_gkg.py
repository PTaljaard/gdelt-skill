#!/usr/bin/env python3
"""Diplomatic/policy query using GKG partitioned table (proper day partitioning)."""

import os
from google.cloud import bigquery
import pandas as pd

PROJECT = "gen-lang-client-0418790586"
client = bigquery.Client(project=PROJECT)

# GKG partitioned table IS partitioned by DAY on DATE field (YYYYMMDD)
# Use _PARTITIONDATE for partition pruning

# Flashpoint periods - use GKG themes for diplomatic/policy content
FLASHPOINTS = [
    ("2020-08-17", "2020-08-31", "Trump farm seizures tweet"),
    ("2021-03-29", "2021-04-11", "State Dept human rights report"),
    ("2022-02-28", "2022-03-13", "SA UN abstention on Russia"),
    ("2023-08-21", "2023-09-03", "BRICS summit Johannesburg"),
    ("2023-12-25", "2024-01-07", "ICJ genocide case filing"),
    ("2024-05-20", "2024-06-02", "SA national election"),
    ("2025-02-01", "2025-02-14", "Trump 2025 Afrikaner refugee policy"),
    ("2026-09-14", "2026-09-28", "White Cross memorial week"),
    ("2026-09-28", "2026-10-12", "Post-memorial diplomatic fallout"),
]

all_results = []

for start, end, label in FLASHPOINTS:
    query = f"""
    SELECT 
      GKGRECORDID, DATE, SourceCommonName, DocumentIdentifier,
      V2Themes, V2Locations, V2Persons, V2Organizations, V2Tone
    FROM `gdelt-bq.gdeltv2.gkg_partitioned`
    WHERE _PARTITIONDATE BETWEEN '{start}' AND '{end}'
      AND (V2Themes LIKE '%SOUTH_AFRICA%' OR V2Locations LIKE '%SOUTH_AFRICA%')
      AND (
        -- Diplomatic/policy themes
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
    LIMIT 200;
    """
    
    print(f"\n📡 {label} ({start} to {end})")
    
    try:
        dry_run = bigquery.QueryJobConfig(dry_run=True)
        job = client.query(query, job_config=dry_run)
        mb = job.total_bytes_processed / 1e6
        print(f"  💰 {mb:.1f} MB")
        
        if mb > 200:
            print(f"  ⚠️  Skipping ({mb:.0f} MB)")
            continue
            
        df = client.query(query).to_dataframe()
        if len(df) > 0:
            df['flashpoint'] = label
            all_results.append(df)
            print(f"  ✅ {len(df)} records")
        else:
            print(f"  ✅ 0 records")
            
    except Exception as e:
        print(f"  ❌ Error: {e}")

if all_results:
    final_df = pd.concat(all_results, ignore_index=True)
    output_path = "/home/user/pieter-kb/GDELT/diplomatic_gkg_flashpoints.csv"
    final_df.to_csv(output_path, index=False, encoding='utf-8')
    print(f"\n💾 Saved: {output_path}")
    print(f"📊 Total records: {len(final_df)}")
    
    print(f"\n📅 Flashpoint distribution:")
    print(final_df['flashpoint'].value_counts())
    
    print(f"\n📰 Top sources:")
    print(final_df['SourceCommonName'].value_counts().head(15))
    
    # Theme analysis
    all_themes = []
    for themes in final_df['V2Themes'].dropna():
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
    
    # Key persons
    all_persons = []
    for persons in final_df['V2Persons'].dropna():
        all_persons.extend([p.strip() for p in str(persons).split(';') if p.strip()])
    person_counts = Counter(all_persons)
    key_persons = [p for p in person_counts.keys() if any(kw in p.upper() for kw in 
        ['TRUMP', 'BIDEN', 'BLINKEN', 'RAMAPHOSA', 'ROETS', 'KRIEL', 'AFRIFORUM', 'PUTIN', 'XI', 'LULA'])]
    print(f"\n👤 Key persons:")
    for p in sorted(key_persons, key=lambda x: -person_counts[x]):
        print(f"  {p}: {person_counts[x]}")
        
    # Key orgs
    all_orgs = []
    for orgs in final_df['V2Organizations'].dropna():
        all_orgs.extend([o.strip() for o in str(orgs).split(';') if o.strip()])
    org_counts = Counter(all_orgs)
    key_orgs = [o for o in org_counts.keys() if any(kw in o.upper() for kw in 
        ['WHITE_HOUSE', 'STATE_DEPT', 'DIRCO', 'AFRIFORUM', 'ANC', 'SACP', 'ISS', 'BRICS', 'UN', 'ICC', 'ICJ'])]
    print(f"\n🏛️ Key organizations:")
    for o in sorted(key_orgs, key=lambda x: -org_counts[x]):
        print(f"  {o}: {org_counts[o]}")
    
    # Sample
    print(f"\n📋 Sample records:")
    for _, row in final_df.head(5).iterrows():
        print(f"  {row['DATE']} | {row['SourceCommonName']} | {row['flashpoint']}")
        print(f"    URL: {row['DocumentIdentifier'][:80]}")
        print(f"    Themes: {str(row['V2Themes'])[:120]}...")
        
else:
    print("❌ No results collected")