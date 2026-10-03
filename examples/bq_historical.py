#!/usr/bin/env python3
"""BigQuery historical analysis example for PhD research.

Queries GDELT Events (1986–2014) and GKG (2015–present) for South Africa
using partitioned queries to stay within free tier (1 TB/month).
"""

import os
from scripts.gdelt_api import GDELTBigQueryClient

def main():
    # Requires: pip install google-cloud-bigquery
    # Auth: gcloud auth application-default login
    # OR set GOOGLE_APPLICATION_CREDENTIALS
    
    project_id = os.getenv("GCP_PROJECT")  # or pass explicitly
    if not project_id:
        print("ERROR: Set GCP_PROJECT environment variable")
        print("   export GCP_PROJECT=your-project-id")
        return

    print(f"Using GCP Project: {project_id}")
    bq = GDELTBigQueryClient(project_id=project_id)

    # -------------------------------------------------------------------------
    # 1. Historical Events: Apartheid to Transition (1986–1994)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("1. Historical Events: 1986–1994 (Apartheid → Democracy)")
    print("=" * 60)
    
    # Query in monthly batches to stay within free tier
    # Each month ~50 MB, 1 TB free = ~20 years of monthly queries
    apartheid_events = bq.query_sa_filter(
        filter_name="afrikaner_genocide",
        start_date="1986-01-01",
        end_date="1994-12-31",
        max_records=50000,
        table="events"
    )
    print(f"Retrieved {len(apartheid_events)} events")
    
    if apartheid_events:
        # Show sample
        print("\nSample events:")
        for e in apartheid_events[:5]:
            print(f"  {e.get('DATEADDED')}: {e.get('Actor1Name')} → {e.get('Actor2Name')}")
            print(f"    EventCode: {e.get('EventCode')}, Goldstein: {e.get('GoldsteinScale')}, Tone: {e.get('AvgTone')}")
            print(f"    Location: {e.get('ActionGeo_FullName')}")

    # -------------------------------------------------------------------------
    # 2. Transition Period (1994–2010)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("2. Transition Period: 1994–2010")
    print("=" * 60)
    
    transition_events = bq.query_sa_filter(
        filter_name="afrikaner_genocide",
        start_date="1994-01-01",
        end_date="2010-12-31",
        max_records=50000,
        table="events"
    )
    print(f"Retrieved {len(transition_events)} events")

    # -------------------------------------------------------------------------
    # 3. Modern GKG (2015–present): Narrative Analysis
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("3. Modern GKG: 2015–2024 (Themes + Tone + URLs)")
    print("=" * 60)
    
    gkg_records = bq.query_sa_filter(
        filter_name="rsa_usa_diplomatic",
        start_date="2015-01-01",
        end_date="2024-12-31",
        max_records=20000,
        table="gkg"
    )
    print(f"Retrieved {len(gkg_records)} GKG records")
    
    if gkg_records:
        print("\nSample GKG records:")
        for r in gkg_records[:3]:
            print(f"  Date: {r.get('DATE')}, Source: {r.get('SourceCommonName')}")
            print(f"  URL: {r.get('DocumentIdentifier')}")
            print(f"  Themes: {r.get('Themes', '')[:100]}...")
            print(f"  V2Tone: {r.get('V2Tone', '')[:80]}...")

    # -------------------------------------------------------------------------
    # 4. Export for LLM Claim Extraction
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("4. Export GKG URLs for LLM Claim Extraction")
    print("=" * 60)
    
    # Get records with URLs for LLM processing
    llm_export = bq.gkg_query(
        filters={"theme": "CRIME_VIOLENCE,ETHNIC_CONFLICT,GENOCIDE", "country": "ZA,SF"},
        start_date="2024-01-01",
        end_date="2024-12-31",
        max_records=5000
    )
    
    urls = [r.get('DocumentIdentifier') for r in llm_export if r.get('DocumentIdentifier')]
    print(f"Extracted {len(urls)} unique article URLs for LLM processing")
    
    # Save to file for LLM pipeline
    import json
    with open("gkg_urls_for_llm.json", "w") as f:
        json.dump([{
            "gkg_id": r.get('GKGRECORDID'),
            "date": r.get('DATE'),
            "source": r.get('SourceCommonName'),
            "url": r.get('DocumentIdentifier'),
            "themes": r.get('Themes'),
            "v2_tone": r.get('V2Tone')
        } for r in llm_export], f, indent=2)
    
    print("Saved to gkg_urls_for_llm.json")

    # -------------------------------------------------------------------------
    # 5. Cost Estimation
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("5. Cost Estimation (Dry Run)")
    print("=" * 60)
    
    # Example: Estimate cost of full 1986-2024 scan
    test_query = """
    SELECT GLOBALEVENTID, DATEADDED, Actor1Name, Actor2Name, EventCode,
           GoldsteinScale, AvgTone, ActionGeo_CountryCode, SOURCEURL
    FROM `gdelt-bq.gdeltv2.events`
    WHERE DATEADDED BETWEEN 19860101000000 AND 20241231235959
      AND ActionGeo_CountryCode = 'SF'
    """
    
    tb = bq.estimate_query_cost(test_query)
    print(f"Full 38-year SA scan: {tb:.4f} TB = ${tb * 5:.2f}")
    print(f"Free tier (1 TB/month): {'FREE' if tb <= 1 else f'${(tb - 1) * 5:.2f} overage'}")

    print("\n" + "=" * 60)
    print("BigQuery analysis complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()