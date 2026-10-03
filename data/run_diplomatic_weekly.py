#!/usr/bin/env python3
"""Ultra-targeted: Weekly windows using MonthYear partition key."""

import os
from google.cloud import bigquery
import pandas as pd
from datetime import datetime, timedelta

PROJECT = "gen-lang-client-0418790586"
client = bigquery.Client(project=PROJECT)

# Specific flashpoint weeks (known events)
FLASHPOINT_WEEKS = [
    # 2020: Trump tweet Aug 23, 2020
    ("2020-08-17", "2020-08-31", "Trump farm seizures tweet"),
    # 2021: State Dept human rights report April 2021
    ("2021-03-29", "2021-04-11", "State Dept human rights report"),
    # 2022: SA UN votes on Russia March 2022
    ("2022-02-28", "2022-03-13", "SA UN abstention on Russia"),
    # 2023: BRICS summit Aug 2023, ICJ case Dec 2023
    ("2023-08-21", "2023-09-03", "BRICS summit Johannesburg"),
    ("2023-12-25", "2024-01-07", "ICJ genocide case filing"),
    # 2024: SA election May 2024
    ("2024-05-20", "2024-06-02", "SA national election"),
    # 2025: Trump refugee policy (hypothetical - Feb 2025)
    ("2025-02-01", "2025-02-14", "Trump 2025 Afrikaner refugee policy"),
    # 2026: White Cross memorial Sept 20-28, 2026
    ("2026-09-14", "2026-09-28", "White Cross memorial week"),
    ("2026-09-28", "2026-10-12", "Post-memorial diplomatic fallout"),
]

all_results = []

for start_str, end_str, label in FLASHPOINT_WEEKS:
    start_dt = datetime.strptime(start_str, "%Y-%m-%d")
    end_dt = datetime.strptime(end_str, "%Y-%m-%d")
    
    # MonthYear integers for partition pruning
    month_years = set()
    current = start_dt
    while current <= end_dt:
        month_years.add(current.year * 100 + current.month)
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    
    monthyear_filter = " OR ".join([f"MonthYear = {my}" for my in sorted(month_years)])
    
    start_int = int(start_str.replace("-", "") + "000000")
    end_int = int(end_str.replace("-", "") + "235959")
    
    query = f"""
    SELECT 
      GLOBALEVENTID, DATEADDED, MonthYear, Actor1Name, Actor2Name,
      Actor1CountryCode, Actor2CountryCode, ActionGeo_CountryCode,
      EventCode, EventBaseCode, EventRootCode, QuadClass,
      GoldsteinScale, NumMentions, NumSources, NumArticles, AvgTone,
      ActionGeo_FullName, ActionGeo_Lat, ActionGeo_Long, SOURCEURL
    FROM `gdelt-bq.gdeltv2.events`
    WHERE ({monthyear_filter})
      AND DATEADDED BETWEEN {start_int} AND {end_int}
      AND ActionGeo_CountryCode = 'SF'
      AND (
        EventRootCode IN ('01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12', '13', '14', '15', '16', '17')
        OR EventRootCode IN ('18', '19', '20')
      )
      AND (
        Actor1CountryCode IN ('US', 'ZA', 'GB', 'EU', 'RU', 'CN') 
        OR Actor2CountryCode IN ('US', 'ZA', 'GB', 'EU', 'RU', 'CN')
      )
    ORDER BY DATEADDED DESC
    LIMIT 500;
    """
    
    print(f"\n📡 {label} ({start_str} to {end_str}) - MonthYear: {sorted(month_years)}")
    
    try:
        dry_run = bigquery.QueryJobConfig(dry_run=True)
        job = client.query(query, job_config=dry_run)
        mb = job.total_bytes_processed / 1e6
        print(f"  💰 {mb:.1f} MB")
        
        if mb > 100:
            print(f"  ⚠️  Skipping ({mb:.0f} MB)")
            continue
            
        df = client.query(query).to_dataframe()
        if len(df) > 0:
            df['flashpoint'] = label
            all_results.append(df)
            print(f"  ✅ {len(df)} events")
        else:
            print(f"  ✅ 0 events")
            
    except Exception as e:
        print(f"  ❌ Error: {e}")

if all_results:
    final_df = pd.concat(all_results, ignore_index=True)
    output_path = "/home/user/pieter-kb/GDELT/diplomatic_events_flashpoints.csv"
    final_df.to_csv(output_path, index=False, encoding='utf-8')
    print(f"\n💾 Saved: {output_path}")
    print(f"📊 Total events: {len(final_df)}")
    
    print(f"\n📅 Flashpoint distribution:")
    print(final_df['flashpoint'].value_counts())
    
    print(f"\n🎭 EventRootCode distribution:")
    print(final_df['EventRootCode'].value_counts().sort_index())
    
    print(f"\n👥 Top Actor1 (diplomatic actors):")
    print(final_df['Actor1Name'].value_counts().head(20))
    
    print(f"\n👥 Top Actor2:")
    print(final_df['Actor2Name'].value_counts().head(15))
    
    print(f"\n🌍 ActionGeo locations:")
    print(final_df['ActionGeo_FullName'].value_counts().head(10))
    
    print(f"\n📈 Avg Tone by Flashpoint:")
    print(final_df.groupby('flashpoint')['AvgTone'].mean())
    
    # Sample events
    print(f"\n📋 Sample events:")
    for _, row in final_df.head(10).iterrows():
        print(f"  {row['DATEADDED']} | {row['Actor1Name']} -> {row['Actor2Name']} | Code: {row['EventCode']} | Goldstein: {row['GoldsteinScale']:.1f} | Tone: {row['AvgTone']:.2f} | {row['ActionGeo_FullName']}")
        
else:
    print("❌ No results collected")