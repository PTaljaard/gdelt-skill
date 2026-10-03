#!/usr/bin/env python3
"""Web NGrams search example (interim solution during API v2 migration)."""

from scripts.gdelt_api import GDELTClient

def main():
    # Use lower rate limit for NGrams (be respectful)
    client = GDELTClient(rate_limit=0.2)  # 1 request per 5 seconds

    print("=" * 60)
    print("GDELT Web NGrams Search Examples")
    print("=" * 60)

    # Example 1: Pre-built SA filter
    print("\n1. NGrams: Afrikaner Genocide filter (last 7 days)")
    results = client.ngrams_search_sa_filter(
        filter_name="afrikaner_genocide",
        start_date="2024-12-01",
        end_date="2024-12-07",
        max_files=20  # ~5 hours of coverage
    )
    print(f"   Found {len(results)} matches")
    for r in results[:5]:
        print(f"   {r['date']} | {r['term_matched']:20s} | {r['title'][:70]}")
        print(f"      {r['url']}")

    # Example 2: Custom search terms
    print("\n2. NGrams: Custom terms (farm attacks + plaasmoorde)")
    custom_terms = [
        "farm attacks", "plaasmoorde", "farm murders", 
        "white farmers", "boer genocide", "kill the boer",
        "expropriation south africa", "ramaphosa farm"
    ]
    results = client.ngrams_search(
        terms=custom_terms,
        start_date="2024-11-01",
        end_date="2024-11-07",
        max_files=15
    )
    print(f"   Found {len(results)} matches")
    
    # Group by term
    from collections import defaultdict
    by_term = defaultdict(list)
    for r in results:
        by_term[r['term_matched']].append(r)
    
    for term, matches in sorted(by_term.items(), key=lambda x: -len(x[1])):
        print(f"   {term}: {len(matches)} matches")
        for m in matches[:2]:
            print(f"      {m['date']} | {m['title'][:70]}")

    # Example 3: Witkruis Memorial (specific event)
    print("\n3. NGrams: Witkruis Memorial (Sept 20-30, 2026)")
    results = client.ngrams_search_sa_filter(
        filter_name="witkruis_memorial",
        start_date="2026-09-20",
        end_date="2026-09-30",
        max_files=50  # ~12 hours
    )
    print(f"   Found {len(results)} matches")
    for r in results[:5]:
        print(f"   {r['date']} | {r['term_matched']} | {r['title'][:70]}")

    # Example 4: Export for LLM ingestion
    print("\n4. Export NGrams URLs for LLM processing")
    all_results = client.ngrams_search_sa_filter(
        filter_name="afrikaner_genocide",
        start_date="2024-12-01",
        end_date="2024-12-31",
        max_files=100
    )
    
    # Deduplicate by URL
    seen_urls = set()
    unique = []
    for r in all_results:
        url = r.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(r)
    
    print(f"   {len(unique)} unique articles from {len(all_results)} ngram matches")
    
    import json
    with open("ngrams_urls_for_llm.json", "w") as f:
        json.dump([{
            "doc_id": r['doc_id'],
            "term_matched": r['term_matched'],
            "quadgram": r['quadgram'],
            "count": r['count'],
            "url": r['url'],
            "title": r['title'],
            "date": r['date'],
            "lang": r['lang'],
            "ngrams_timestamp": r['ngrams_timestamp']
        } for r in unique], f, indent=2)
    
    print("   Saved to ngrams_urls_for_llm.json")

    print("\n" + "=" * 60)
    print("NGrams search complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()