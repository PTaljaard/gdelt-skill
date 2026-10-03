#!/usr/bin/env python3
"""Targeted diplomatic events query using CAMEO codes (Events table is smaller)."""

import os
from google.cloud import bigquery
import pandas as pd

PROJECT = "gen-lang-client-0418790586"
client = bigquery.Client(project=PROJECT)

# CAMEO codes for diplomatic/policy actions:
# 010-019: Make public statement
# 020-029: Appeal
# 030-039: Express intent to cooperate
# 040-049: Consult
# 050-059: Engage in diplomatic cooperation
# 060-069: Engage in material cooperation
# 070-079: Provide aid
# 080-089: Yield
# 090-099: Investigate
# 100-109: Demand
# 110-119: Disapprove
# 120-129: Reject
# 130-139: Threaten (130-139)
# 140-149: Protest
# 150-159: Exhibit force posture
# 160-169: Reduce relations
# 170-179: Coerce
# 180-189: Assault
# 190-199: Fight
# 200-209: Unconventional mass violence

# Flashpoint periods for SA-US diplomatic tensions
FLASHPOINTS = [
    ("2020-08-01", "2020-09-30", "Trump 'farm seizures' tweet + land expropriation debate"),
    ("2021-03-01", "2021-06-30", "Biden admin human rights report on SA"),
    ("2022-02-01", "2022-08-30", "SA abstains on UN Russia votes, US pressure"),
    ("2023-08-01", "2023-12-31", "BRICS expansion, SA ICJ case vs Israel"),
    ("2024-02-01", "2024-06-30", "SA election, US-SA relations review"),
    ("2025-01-01", "2025-12-31", "Trump 2025 refugee policy for Afrikaners"),
    ("2026-01-01", "2026-12-31", "White Cross memorial, diplomatic rupture"),
]

all_results = []

for start, end, label in FLASHPOINTS:
    start_int = int(start.replace("-", "") + "000000")
    end_int = int(end.replace("-", "") + "235959")
    
    query = f"""
    SELECT 
      GLOBALEVENTID, DATEADDED, Actor1Name, Actor2Name,
      Actor1CountryCode, Actor2CountryCode, ActionGeo_CountryCode,
      EventCode, EventBaseCode, EventRootCode, QuadClass,
      GoldsteinScale, NumMentions, NumSources, NumArticles, AvgTone,
      ActionGeo_FullName, ActionGeo_Lat, ActionGeo_Long, SOURCEURL
    FROM `gdelt-bq.gdeltv2.events`
    WHERE DATEADDED BETWEEN {start_int} AND {end_int}
      AND ActionGeo_CountryCode = 'SF'
      AND (
        -- Diplomatic codes
        EventRootCode IN ('01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12', '13', '14', '15', '16', '17')
        -- Violence codes (for context)
        OR EventRootCode IN ('18', '19', '20')
      )
      AND (
        Actor1CountryCode IN ('US', 'ZA', 'GB', 'EU', 'RU', 'CN') 
        OR Actor2CountryCode IN ('US', 'ZA', 'GB', 'EU', 'RU', 'CN')
      )
    ORDER BY DATEADDED DESC
    LIMIT 2000;
    """
    
    print(f"\n📡 {label} ({start} to {end})...")
    
    try:
        # Dry run
        dry_run = bigquery.QueryJobConfig(dry_run=True)
        job = client.query(query, job_config=dry_run)
        mb = job.total_bytes_processed / 1e6
        print(f"  💰 {mb:.0f} MB")
        
        if mb > 500:
            print(f"  ⚠️  Skipping (too large)")
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
    
    # Analysis
    print(f"\n📅 Flashpoint distribution:")
    print(final_df['flashpoint'].value_counts())
    
    print(f"\n🎭 EventRootCode distribution:")
    print(final_df['EventRootCode'].value_counts().sort_index())
    
    print(f"\n👥 Top Actor1:")
    print(final_df['Actor1Name'].value_counts().head(15))
    
    print(f"\n👥 Top Actor2:")
    print(final_df['Actor2Name'].value_counts().head(15))
    
    print(f"\n🌍 ActionGeo:")
    print(final_df['ActionGeo_FullName'].value_counts().head(10))
    
    print(f"\n📈 Avg Tone by Flashpoint:")
    print(final_df.groupby('flashpoint')['AvgTone'].mean())
    
else:
    print("❌ No results")