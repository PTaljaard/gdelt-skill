# Web NGrams Dataset — Interim Fallback Guide

## Context: GDELT API v2 Migration

As of 2025, **GDELT API v2 is migrating from BigQuery to Google Spanner**. During this migration:

- `https://api.gdeltproject.org/api/v2/events/events` → **404**
- `https://api.gdeltproject.org/api/v2/mentions/mentions` → **404**
- `https://api.gdeltproject.org/api/v2/gkg/gkg` → **404**

**BigQuery tables remain fully operational** and are the recommended path for all historical and production work.

The **Web NGrams dataset** is GDELT's interim solution providing minute-resolution ngram data from global news.

## NGrams Dataset Overview

| Aspect | Details |
|--------|---------|
| **Coverage** | Global news, 100+ languages |
| **Granularity** | 1-minute files (with 15-min heartbeat gaps) |
| **Format** | Gzipped TSV (ngrams) + JSON Lines (TOC) |
| **URL Pattern** | `https://data.gdeltproject.org/gdeltv5/weblegacy/ngrams/YYYYMMDDHHMM00.ngrams.txt.gz` |
| **TOC URL** | `https://data.gdeltproject.org/gdeltv5/weblegacy/ngrams/YYYYMMDDHHMM00.toc.json.gz` |
| **Ngram Type** | Quadgrams (4-word sequences) with counts |

### NGrams File Format (TSV)

```
doc_id	quadgram	count
12345	"south africa farm attacks"	3
12345	"farm attacks south africa"	2
```

### TOC File Format (JSON Lines)

```json
{"ID": 12345, "url": "https://example.com/article", "title": "Article Title", "date": "20240930", "lang": "en"}
```

## Search Strategy

Since NGrams are quadgrams, searching for arbitrary phrases requires:

1. **Tokenize query into quadgrams** — "farm murders south africa" → `["farm murders south africa"]` (if 4 words) or sliding window
2. **Fetch files for time range** — Every 15 minutes (heartbeat pattern)
3. **Match quadgrams against index** — Case-insensitive substring match
4. **Join with TOC** — Get URL, title, date, language

## Rate Limits & Best Practices

| Limit | Value |
|-------|-------|
| Requests/second | 1 (same as API) |
| File size | ~10-50 MB compressed |
| Retention | Rolling window (not full archive) |

**Best practices:**
- Process files sequentially with 5-second delays
- Cache TOC lookups locally
- Use `HEAD` requests to check file existence before downloading
- Process in 15-minute blocks (GDELT heartbeat interval)

## Python Usage (Built into Skill)

```python
from scripts.gdelt_api import GDELTClient

client = GDELTClient(rate_limit=0.2)  # Be gentle: 1 req/5 sec

# Search using pre-built SA filter terms
results = client.ngrams_search_sa_filter(
    filter_name="afrikaner_genocide",
    start_date="2024-01-01",
    end_date="2024-01-31",
    max_files=100  # ~25 hours of coverage
)

# Or custom terms
results = client.ngrams_search(
    terms=["farm attacks", "plaasmoorde", "white genocide"],
    start_date="2024-01-01",
    end_date="2024-01-07",
    max_files=50
)

for r in results[:10]:
    print(f"{r['date']} | {r['term_matched']} | {r['title'][:60]} | {r['url']}")
```

## Output Structure

```python
{
    "doc_id": "12345",
    "term_matched": "farm attacks",
    "quadgram": "farm attacks south africa",
    "count": 3,
    "url": "https://news.example.com/article",
    "title": "Farm Attacks Spike in South Africa",
    "date": "20240930",
    "lang": "en",
    "ngrams_timestamp": "2024-09-30T12:30:00"
}
```

## Limitations vs. Full API

| Feature | API v2 / BigQuery | NGrams Fallback |
|---------|-------------------|-----------------|
| Event codes (CAMEO) | ✅ Full | ❌ Not available |
| Actor coding | ✅ Full | ❌ Not available |
| Goldstein scale | ✅ | ❌ |
| AvgTone | ✅ | ❌ (no tone) |
| Themes | ✅ GKG V2Themes | ⚠️ Keyword-only |
| Geography | ✅ Precise lat/long | ❌ |
| Historical depth | 1979–present | Rolling ~30 days |
| Query flexibility | SQL / filters | Keyword quadgrams |

## When to Use NGrams

- ✅ **Real-time monitoring** during API migration
- ✅ **Keyword presence detection** ("is 'farm murders' trending?")
- ✅ **Source URL discovery** for LLM ingestion
- ✅ **Complementary signal** alongside BigQuery

## When NOT to Use NGrams

- ❌ **Historical research** (use BigQuery)
- ❌ **Quantitative event counts** (no CAMEO codes)
- ❌ **Sentiment analysis** (no tone data)
- ❌ **Actor/network analysis** (no actor coding)

## Migration Timeline

GDELT has not announced a completion date for the Spanner migration. Monitor:
- [GDELT Blog](https://blog.gdeltproject.org/)
- [GDELT API Status](https://api.gdeltproject.org/)

**Recommendation**: Build all production pipelines on **BigQuery**. Use NGrams only for real-time alerting during the migration window.