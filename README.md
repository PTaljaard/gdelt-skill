# GDELT 2.0 API Skill for Hermes

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)]()

A production-ready Python wrapper for the **GDELT 2.0 API** (Events, Mentions, Global Knowledge Graph) with specialized templates for **South African political event monitoring**. Designed for **Hermes Agent** integration with cron job scheduling, Neo4j graph synchronization, and BigQuery support for large-scale historical analysis.

## Features

| Feature | Description |
|---------|-------------|
| **Multi-API Access** | Events, Mentions, GKG APIs + Web NGrams fallback |
| **SA Politics Filters** | 5 pre-built templates for Afrikaner genocide, RSA-USA diplomatic, visa sanctions, Iran/Russia alignment, BRICS wart countries |
| **BigQuery Client** | Direct access to GDELT BigQuery tables for 40+ years of historical data |
| **Neo4j Sync** | Graph schema for Event→Actor→Location→Theme relationships (D7-ready) |
| **Cron Templates** | Hermes cron jobs for continuous monitoring, daily digests, escalation alerts |
| **Rate Limiting** | Built-in exponential backoff, 429 handling, configurable RPS |
| **PhD-Ready** | Partitioned BigQuery queries, provenance tracking, LLM-export hooks |

## Quick Start

### Installation

```bash
# Core dependencies
pip install requests

# Optional: BigQuery support
pip install google-cloud-bigquery

# Optional: Neo4j support
pip install neo4j
```

### Basic Usage

```python
from scripts.gdelt_api import GDELTClient, SA_FILTERS

client = GDELTClient(rate_limit=1.0)  # 1 req/sec (free tier)

# Query using pre-built SA filter
events = client.query_sa_filter(
    filter_name="afrikaner_genocide",
    start_date="2024-01-01",
    end_date="2024-01-31",
    max_records=250,
    api="events"
)

for event in events[:5]:
    print(f"{event.day}: {event.actor1_name} → {event.actor2_name} "
          f"[{event.event_code}] tone={event.avg_tone:.2f}")
```

### BigQuery Historical Analysis (Recommended for PhD/Research)

```python
from scripts.gdelt_api import GDELTBigQueryClient

# Requires: pip install google-cloud-bigquery
# Auth: gcloud auth application-default login

bq = GDELTBigQueryClient(project_id="your-gcp-project")

# Query 1986-1996 apartheid-era events in South Africa
events = bq.query_sa_filter(
    filter_name="afrikaner_genocide",
    start_date="1986-01-01",
    end_date="1996-12-31",
    max_records=10000,
    table="events"
)

# Query modern GKG (2015-present) with themes + tone
gkg_records = bq.query_sa_filter(
    filter_name="rsa_usa_diplomatic",
    start_date="2024-01-01",
    end_date="2024-12-31",
    max_records=5000,
    table="gkg"
)
```

## SA Politics Filter Templates

| Filter | Use Case | Key Themes/Actors |
|--------|----------|-------------------|
| `afrikaner_genocide` | Farm attacks, ethnic violence against Afrikaners/Boers | GENOCIDE, ETHNIC_VIOLENCE, FARM_ATTACK, AFRIKANER, BOER |
| `rsa_usa_diplomatic` | USA-South Africa diplomatic disputes, sanctions | DIPLOMATIC_DISPUTE, SANCTIONS, VISA_RESTRICTIONS |
| `usa_visa_sanctions` | US visa restrictions, Magnitsky sanctions on SA officials | VISA_RESTRICTIONS, MAGNITSKY, TRAVEL_BAN |
| `rsa_iran_russia_alignment` | RSA alignment with Iran/Russia/China/BRICS | MILITARY_COOPERATION, STRATEGIC_ALLIANCE |
| `brics_wart_countries` | BRICS+ "wart" countries cooperation, sanctions evasion | SANCTIONS_EVASION, ALLIANCE |

### NGrams-Only Filters (for API v2 migration period)

```python
# These use the Web NGrams dataset (interim solution)
client.ngrams_search_sa_filter("witkruis_memorial", start_date="2026-09-01", end_date="2026-10-01")
```

## Hermes Cron Job Integration

### Generate All Cron Jobs

```python
from scripts.cron_templates import create_all_sa_cron_jobs
import json

jobs = create_all_sa_cron_jobs(sync_neo4j=False)  # D7 offline
for job in jobs:
    print(json.dumps(job))
```

### Output (pipe to `hermes cronjob create`)

```json
{
  "name": "gdelt-sa-politics-monitor",
  "schedule": "0 */6 * * *",
  "command": "python -m scripts.gdelt_api --filter=afrikaner_genocide --filter=rsa_usa_diplomatic --filter=usa_visa_sanctions --filter=rsa_iran_russia_alignment --filter=brics_wart_countries",
  "description": "Monitor SA political events via GDELT...",
  "deliver": "origin"
}
```

## Neo4j Graph Schema

When D7 is online, the skill syncs to this schema:

```cypher
// Nodes
(Event)-[:ACTOR_IN]->(Person/Organization)
(Event)-[:LOCATED_IN]->(Location)
(Event)-[:HAS_TONE]->(ToneMetric)
(Event)-[:HAS_GOLDSTEIN]->(GoldsteinScale)
(Event)-[:HAS_THEME]->(Theme)
(Event)-[:MENTIONS]->(Mention)

// Key properties
Event: {global_event_id, date, event_code, goldstein_scale, avg_tone, action_geo_country}
Actor: {name, country_code, ethnic_code, type}
Location: {full_name, lat, long, country_code}
Theme: {name}
```

### Sync Example (when D7 available)

```python
from neo4j import GraphDatabase
from scripts.gdelt_api import GDELTClient

driver = GraphDatabase.driver("neo4j://d7:7687", auth=("neo4j", "password"))
client = GDELTClient()

events = client.query_sa_filter("afrikaner_genocide", start_date="2024-01-01")
result = client.sync_events_to_neo4j(events, driver=driver)
print(result)  # {"events": 250, "persons": 45, "organizations": 30, ...}
```

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  GDELT API v2   │     │  GDELT BigQuery  │     │  Web NGrams     │
│  (Events/Ment/  │     │  (Historical     │     │  (Interim       │
│   GKG)          │     │   1979-present)  │     │   Solution)     │
└────────┬────────┘     └────────┬─────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌────────────────────────┐
                    │    GDELTClient /       │
                    │    GDELTBigQueryClient │
                    └───────────┬────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
    ┌─────────────────┐ ┌───────────────┐ ┌───────────────┐
    │  Hermes Cron    │ │   Neo4j D7    │ │  LLM Export   │
    │  (6hr/daily/3hr)│ │   (Graph)     │ │  (Claims)     │
    └─────────────────┘ └───────────────┘ └───────────────┘
```

## Project Structure

```
gdelt-skill/
├── scripts/
│   ├── __init__.py          # Package exports
│   ├── gdelt_api.py         # Main client + BigQuery + NGrams
│   └── cron_templates.py    # Hermes cron job generators
├── docs/
│   ├── ARCHITECTURE.md      # System architecture
│   ├── BIGQUERY.md          # BigQuery query patterns
│   ├── NEO4J_SCHEMA.md      # Graph schema docs
│   └── NGRAMS_FALLBACK.md   # Web NGrams interim guide
├── examples/
│   ├── basic_usage.py       # Simple event queries
│   ├── bq_historical.py     # 1986-present historical analysis
│   ├── ngrams_search.py     # NGrams interim search
│   └── cron_setup.py        # Hermes cron job creation
├── tests/
│   └── test_gdelt_api.py    # Unit tests
├── pyproject.toml
├── requirements.txt
├── LICENSE
└── README.md
```

## Configuration

### Environment Variables

```bash
# Optional: GDELT API key for higher rate limits
export GDELT_API_KEY="your_key_here"

# BigQuery (uses Application Default Credentials by default)
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
# OR
export GCP_PROJECT="your-project-id"

# Neo4j (when D7 available)
export NEO4J_URI="neo4j://d7:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASS="password"
```

### Rate Limits

| Tier | Requests/Second | Notes |
|------|----------------|-------|
| Free (no key) | 1.0 | Default, enforced by GDELT |
| API Key | ~10-100 | Contact kalev.leetaru5@gmail.com |
| BigQuery | Unlimited* | 1 TB free/month, then $5/TB |

## PhD/Research Usage

This skill was designed for a doctoral project mapping **conflicting narratives** in South African rural violence (1986–present) using:

1. **BigQuery Events** (1986–2014): CAMEO-coded events, Goldstein scale, actor geography
2. **BigQuery GKG** (2015–present): V2Themes, V2Tone, persons, orgs, source URLs
3. **LLM Claim Extraction**: Feed `DocumentIdentifier` URLs to LLM for structured claim/stance/evidence extraction
4. **Neo4j Narrative Graph**: Event → Claim → Claimant → Evidence → Stance network

See `docs/PHD_METHODOLOGY.md` for the full methodological framework.

## GDELT API v2 Migration Note

> **Current Status**: GDELT API v2 is migrating to Google Spanner. The `/api/v2/events/events`, `/api/v2/mentions/mentions`, and `/api/v2/gkg/gkg` endpoints return **404** during migration.

This skill includes a **fallback to the Web NGrams dataset** (`ngrams_search()`) which provides minute-resolution ngram data from global news. For production historical work, **use BigQuery** (fully operational).

See: [GDELT Blog: Using the New Web NGrams Dataset](https://blog.gdeltproject.org/using-the-new-web-ngrams-dataset-to-find-relevant-coverage/)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure `ruff check .` and `mypy scripts/` pass
5. Submit a PR

## License

MIT License — see [LICENSE](LICENSE) for details.

## Citation

If you use this in academic work:

```bibtex
@software{gdelt_hermes_skill,
  title = {GDELT 2.0 API Skill for Hermes Agent},
  author = {Pieter Taljaard},
  year = {2025},
  url = {https://github.com/PTaljaard/gdelt-skill}
}
```

## Related Resources

- [GDELT Project](https://gdeltproject.org/)
- [GDELT BigQuery Tables](https://console.cloud.google.com/marketplace/details/gdelt-bq/gdelt)
- [CAMEO Codebook](http://data.gdeltproject.org/documentation/Event-Data-Codebook.pdf)
- [Hermes Agent](https://hermes-agent.nousresearch.com/)