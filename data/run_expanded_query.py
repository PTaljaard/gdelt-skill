#!/usr/bin/env python3
"""Expanded query: Food security + geopolitics + local rhetoric (exact flashpoint days)."""

import os
from google.cloud import bigquery
import pandas as pd

PROJECT = "gen-lang-client-0418790586"
client = bigquery.Client(project=PROJECT)

# Your key dates + new supply chain flashpoints
FLASHPOINT_DAYS = [
    # Original diplomatic flashpoints
    ("2020-08-23", "Trump farm seizures tweet"),
    ("2021-04-09", "State Dept human rights report"),
    ("2022-03-02", "SA UN abstention on Russia"),
    ("2023-08-22", "BRICS summit Day 1"),
    ("2023-08-23", "BRICS summit Day 2"),
    ("2023-12-29", "ICJ genocide case filing"),
    ("2024-05-29", "SA national election"),
    ("2026-09-20", "White Cross memorial start"),
    ("2026-09-28", "White Cross memorial end"),
    
    # Supply chain / food security flashpoints
    ("2022-02-24", "Russia invades Ukraine (fertilizer shock)"),
    ("2022-03-15", "Fertilizer price peak (post-invasion)"),
    ("2023-10-07", "Hamas attacks Israel (Gaza war starts)"),
    ("2024-04-13", "Iran attacks Israel (escalation)"),
    ("2024-10-01", "Iran missile barrage on Israel"),
    ("2022-06-15", "Diesel price record high (SA)"),
    ("2023-02-15", "EWC Bill parliamentary process"),
    ("2024-01-15", "MK Party launch (Zuma)"),
    ("2024-05-29", "Election: ANC loses majority"),
]

# Expanded theme filter
THEME_FILTER = """
  AND (
    -- Diplomatic/policy (original)
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
    -- Supply chain / food security (NEW)
    OR V2Themes LIKE '%FOOD_SECURITY%'
    OR V2Themes LIKE '%AGRICULTURE%'
    OR V2Themes LIKE '%FERTILIZER%'
    OR V2Themes LIKE '%ENERGY_SECURITY%'
    OR V2Themes LIKE '%OIL_PRICES%'
    OR V2Themes LIKE '%DIESEL%'
    OR V2Themes LIKE '%SUPPLY_CHAIN%'
    OR V2Themes LIKE '%TRADE_RESTRICTIONS%'
    OR V2Themes LIKE '%PLASTICS%'
    OR V2Themes LIKE '%AGRICULTURE_INPUTS%'
    OR V2Themes LIKE '%COMMODITY_PRICES%'
    -- Geopolitical actors (NEW)
    OR V2Themes LIKE '%IRAN%'
    OR V2Themes LIKE '%RUSSIA_UKRAINE%'
    OR V2Themes LIKE '%ISRAEL_HAMAS%'
    OR V2Themes LIKE '%ISRAEL_IRAN%'
    OR V2Themes LIKE '%MIDDLE_EAST_CONFLICT%'
    -- Local SA political rhetoric (NEW)
    OR V2Themes LIKE '%HATE_SPEECH%'
    OR V2Themes LIKE '%INCITEMENT%'
    OR V2Themes LIKE '%POLITICAL_VIOLENCE%'
    OR V2Themes LIKE '%ELECTION%'
    OR V2Themes LIKE '%COALITION_GOVERNMENT%'
    OR V2Themes LIKE '%GOVERNMENT_OF_NATIONAL_UNITY%'
    OR V2Themes LIKE '%SERVICE_DELIVERY_PROTEST%'
  )
"""

all_results = []
total_gb = 0

for start, label in FLASHPOINT_DAYS:
    query = f"""
    SELECT 
      GKGRECORDID, DATE, SourceCommonName, DocumentIdentifier,
      V2Themes, V2Locations, V2Persons, V2Organizations, V2Tone
    FROM `gdelt-bq.gdeltv2.gkg_partitioned`
    WHERE _PARTITIONDATE = '{start}'
      AND (V2Themes LIKE '%SOUTH_AFRICA%' OR V2Locations LIKE '%SOUTH_AFRICA%')
      {THEME_FILTER}
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
        
        if gb > 2:
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
    output_path = "/home/user/pieter-kb/GDELT/expanded_food_security_geopolitics.csv"
    final_df.to_csv(output_path, index=False, encoding='utf-8')
    print(f"\n💾 Saved: {output_path}")
    print(f"📊 Total records: {len(final_df)}")
    print(f"💰 Total scanned: {total_gb / 1e9:.2f} GB")
    
    print(f"\n📅 Flashpoint distribution:")
    print(final_df['flashpoint'].value_counts())
    
    # Theme analysis
    all_themes = []
    for themes in final_df['V2Themes'].dropna():
        all_themes.extend([t.strip() for t in str(themes).split(';') if t.strip()])
    
    from collections import Counter
    theme_counts = Counter(all_themes)
    
    # Categorize themes
    categories = {
        'Diplomatic/Policy': ['DIPLOMATIC', 'SANCTION', 'VISA', 'MAGNITSKY', 'FOREIGN_POLICY', 'HUMAN_RIGHTS', 'REFUGEE', 'ASYLUM', 'INTERNATIONAL_RELATIONS', 'DIPLOMACY', 'GENOCIDE', 'ETHNIC_CLEANSING', 'CRIMES_AGAINST', 'WAR_CRIMES', 'LAND_REFORM', 'EXPROPRIATION', 'LAND_REDISTRIBUTION', 'PROPERTY_RIGHTS'],
        'Food Security/Supply Chain': ['FOOD_SECURITY', 'AGRICULTURE', 'FERTILIZER', 'ENERGY_SECURITY', 'OIL_PRICES', 'DIESEL', 'SUPPLY_CHAIN', 'TRADE_RESTRICTIONS', 'PLASTICS', 'AGRICULTURE_INPUTS', 'COMMODITY_PRICES'],
        'Geopolitical Actors': ['IRAN', 'RUSSIA_UKRAINE', 'ISRAEL_HAMAS', 'ISRAEL_IRAN', 'MIDDLE_EAST_CONFLICT'],
        'Local Rhetoric': ['HATE_SPEECH', 'INCITEMENT', 'POLITICAL_VIOLENCE', 'ELECTION', 'COALITION_GOVERNMENT', 'GOVERNMENT_OF_NATIONAL_UNITY', 'SERVICE_DELIVERY_PROTEST'],
    }
    
    print(f"\n🎯 Theme categories:")
    for cat, keywords in categories.items():
        cat_themes = [t for t in theme_counts.keys() if any(kw in t for kw in keywords)]
        total = sum(theme_counts[t] for t in cat_themes)
        print(f"  {cat}: {total} mentions across {len(cat_themes)} themes")
        for t in sorted(cat_themes, key=lambda x: -theme_counts[x])[:5]:
            print(f"    {t}: {theme_counts[t]}")
    
    # Sample
    print(f"\n📋 Sample records:")
    for _, row in final_df.head(10).iterrows():
        print(f"  {row['DATE']} | {row['SourceCommonName']} | {row['flashpoint']}")
        print(f"    URL: {row['DocumentIdentifier'][:100]}")
        print(f"    Themes: {str(row['V2Themes'])[:150]}...")
        
else:
    print("❌ No results collected")