#!/usr/bin/env python3
"""Run exact-day GKG queries accepting ~1 GB/day scan (within free tier)."""

import os
from google.cloud import bigquery
import pandas as pd

PROJECT = "gen-lang-client-0418790586"
client = bigquery.Client(project=PROJECT)

# Exact flashpoint dates - run ALL, accept ~1 GB/day
FLASHPOINT_DAYS = [
    ("2020-08-23", "2020-08-23", "Trump farm seizures tweet"),
    ("2021-04-09", "2021-04-09", "State Dept human rights report"),
    ("2022-03-02", "2022-03-02", "SA UN abstention on Russia"),
    ("2023-08-22", "2023-08-22", "BRICS summit Day 1"),
    ("2023-08-23", "2023-08-23", "BRICS summit Day 2"),
    ("2023-12-29", "2023-12-29", "ICJ genocide case filing"),
    ("2024-05-29", "2024-05-29", "SA national election"),
    ("2026-09-20", "2026-09-20", "White Cross memorial start"),
    ("2026-09-28", "2026-09-28", "White Cross memorial end"),
]

all_results = []
total_gb = 0

for start, end, label in FLASHPOINT_DAYS:
    query = f"""
    SELECT 
      GKGRECORDID, DATE, SourceCommonName, DocumentIdentifier,
      V2Themes, V2Locations, V2Persons, V2Organizations, V2Tone
    FROM `gdelt-bq.gdeltv2.gkg_partitioned`
    WHERE _PARTITIONDATE BETWEEN '{start}' AND '{end}'
      AND (V2Themes LIKE '%SOUTH_AFRICA%' OR V2Locations LIKE '%SOUTH_AFRICA%')
      AND (
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
        OR V2Themes LIKE '%GENOCIDE%'
        OR V2Themes LIKE '%ETHNIC_CLEANSING%'
        OR V2Themes LIKE '%CRIMES_AGAINST_HUMANITY%'
        OR V2Themes LIKE '%WAR_CRIMES%'
        OR V2Themes LIKE '%LAND_REFORM%'
        OR V2Themes LIKE '%EXPROPRIATION%'
        OR V2Themes LIKE '%LAND_REDISTRIBUTION%'
        OR V2Themes LIKE '%PROPERTY_RIGHTS%'
      )
    ORDER BY DATE DESC
    LIMIT 100;
    """
    
    print(f"\n📡 {label} ({start})")
    
    try:
        dry_run = bigquery.QueryJobConfig(dry_run=True)
        job = client.query(query, job_config=dry_run)
        gb = job.total_bytes_processed / 1e9
        total_gb += job.total_bytes_processed
        print(f"  💰 {gb:.2f} GB")
        
        if gb > 3:
            print(f"  ⚠️  Skipping ({gb:.2f} GB)")
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
    output_path = "/home/user/pieter-kb/GDELT/diplomatic_gkg_exact_days.csv"
    final_df.to_csv(output_path, index=False, encoding='utf-8')
    print(f"\n💾 Saved: {output_path}")
    print(f"📊 Total records: {len(final_df)}")
    print(f"💰 Total scanned: {total_gb / 1e9:.2f} GB")
    
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
    for _, row in final_df.head(15).iterrows():
        print(f"  {row['DATE']} | {row['SourceCommonName']} | {row['flashpoint']}")
        print(f"    URL: {row['DocumentIdentifier'][:100]}")
        print(f"    Themes: {str(row['V2Themes'])[:150]}...")
        
else:
    print("❌ No results collected")