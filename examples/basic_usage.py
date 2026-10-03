#!/usr/bin/env python3
"""Basic usage examples for GDELT API client."""

from scripts.gdelt_api import GDELTClient, SA_FILTERS, SA_NGRAM_SEARCH_TERMS

def main():
    client = GDELTClient(rate_limit=1.0)  # 1 req/sec (free tier)

    print("=" * 60)
    print("GDELT Basic Usage Examples")
    print("=" * 60)

    # Example 1: Query using pre-built SA filter (Events API)
    print("\n1. Events API: Afrikaner Genocide filter (last 7 days)")
    events = client.query_sa_filter(
        filter_name="afrikaner_genocide",
        start_date="2024-12-01",
        end_date="2024-12-07",
        max_records=50,
        api="events"
    )
    print(f"   Found {len(events)} events")
    for e in events[:3]:
        print(f"   {e.day}: {e.actor1_name} → {e.actor2_name} "
              f"[{e.event_code}] Goldstein={e.goldstein_scale:.1f} Tone={e.avg_tone:.2f}")

    # Example 2: Mentions API (source tracking)
    print("\n2. Mentions API: RSA-USA Diplomatic filter")
    mentions = client.query_sa_filter(
        filter_name="rsa_usa_diplomatic",
        start_date="2024-12-01",
        end_date="2024-12-07",
        max_records=30,
        api="mentions"
    )
    print(f"   Found {len(mentions)} mentions")
    for m in mentions[:3]:
        print(f"   {m.mention_time_date}: {m.mention_source_name} → {m.mention_identifier[:60]}")

    # Example 3: GKG API (themes + tone) - NOTE: API v2 currently 404
    print("\n3. GKG API: USA Visa Sanctions (will fallback to NGrams)")
    try:
        gkg = client.query_sa_filter(
            filter_name="usa_visa_sanctions",
            start_date="2024-12-01",
            end_date="2024-12-07",
            max_records=20,
            api="gkg"
        )
        print(f"   Found {len(gkg)} GKG records")
    except Exception as e:
        print(f"   Expected fallback: {type(e).__name__}")

    # Example 4: NGrams fallback (interim solution)
    print("\n4. NGrams Search: Witkruis Memorial (Sept 2026)")
    ngrams = client.ngrams_search_sa_filter(
        filter_name="witkruis_memorial",
        start_date="2026-09-20",
        end_date="2026-09-30",
        max_files=10
    )
    print(f"   Found {len(ngrams)} ngram matches")
    for n in ngrams[:3]:
        print(f"   {n['date']} | {n['term_matched']} | {n['title'][:70]}")

    # Example 5: Custom query
    print("\n5. Custom Events Query")
    from scripts.gdelt_api import EventQueryBuilder
    builder = EventQueryBuilder({
        "theme": "CRIME_VIOLENCE",
        "country": "SF",
        "actor": "AFRIFORUM"
    })
    custom_events = client.events_query(
        query=builder.build(),
        start_date="2024-11-01",
        end_date="2024-11-30",
        max_records=25
    )
    print(f"   Found {len(custom_events)} custom events")

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)

if __name__ == "__main__":
    main()