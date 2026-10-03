#!/usr/bin/env python3
"""Partitioned diplomatic/policy query: 2020-2026 in monthly batches."""

import os
from google.cloud import bigquery
import pandas as pd
import time

PROJECT = "gen-lang-client-0418790586"
client = bigquery.Client(project=PROJECT)

# Theme filter (same as before)
THEME_FILTER = """
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
"""

all_results = []
total_bytes = 0

for year in range(2020, 2027):
    for month in range(1, 13):
        if year == 2026 and month > 10:  # Only up to Oct 2026
            break
            
        month_str = f"{year}{month:02d}"
        start_date = f"{year}-{month:02d}-01"
        
        # Calculate end date
        if month == 12:
            end_date = f"{year+1}-01-01"
        else:
            end_date = f"{year}-{month+1:02d}-01"
        
        query = f"""
        SELECT 
          GKGRECORDID, DATE, SourceCommonName, DocumentIdentifier,
          V2Themes, V2Locations, V2Persons, V2Organizations, V2Tone
        FROM `gdelt-bq.gdeltv2.gkg_partitioned`
        WHERE _PARTITIONDATE BETWEEN '{start_date}' AND '{end_date}'
          AND (V2Themes LIKE '%SOUTH_AFRICA%' OR V2Locations LIKE '%SOUTH_AFRICA%')
          {THEME_FILTER}
        ORDER BY DATE DESC
        LIMIT 1000;
        """
        
        print(f"\n📡 Querying {month_str}...")
        
        try:
            # Dry run first
            dry_run = bigquery.QueryJobConfig(dry_run=True)
            job = client.query(query, job_config=dry_run)
            mb = job.total_bytes_processed / 1e6
            total_bytes += job.total_bytes_processed
            
            if mb > 200:  # Skip if too large
                print(f"  ⚠️  {mb:.0f} MB - skipping (too large)")
                continue
            
            # Actual query
            df = client.query(query).to_dataframe()
            if len(df) > 0:
                df['query_month'] = month_str
                all_results.append(df)
                print(f"  ✅ {len(df)} rows, {mb:.0f} MB")
            else:
                print(f"  ✅ 0 rows, {mb:.0f} MB")
                
            # Small delay between queries
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            continue

# Combine results
if all_results:
    final_df = pd.concat(all_results, ignore_index=True)
    output_path = "/home/user/pieter-kb/GDELT/diplomatic_policy_2020_2026.csv"
    final_df.to_csv(output_path, index=False, encoding='utf-8')
    print(f"\n💾 Combined results saved: {output_path}")
    print(f"📊 Total rows: {len(final_df)}")
    print(f"💰 Total bytes scanned: {total_bytes / 1e9:.2f} GB")
    
    # Quick analysis
    print(f"\n📅 Year distribution:")
    final_df['year'] = final_df['DATE'].astype(str).str[:4]
    print(final_df['year'].value_counts().sort_index())
    
    print(f"\n📰 Top 15 sources:")
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
        print(f"  {o}: {org_counts[x]}")
        
else:
    print("❌ No results collected")