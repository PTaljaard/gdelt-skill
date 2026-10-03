# Session Continuation Guide: GDELT + Hermes + Neo4j on R9/D7

## 📍 Where We Left Off

**Date**: October 3, 2026  
**Context**: Office renovations complete; connecting D7/R9/L7 stack next  
**GitHub**: `https://github.com/PTaljaard/gdelt-skill` (fully synced)

---

## ✅ What's Done & In Repo

| Component | Location | Status |
|-----------|----------|--------|
| **GDELT Skill** | `scripts/gdelt_api.py`, `scripts/cron_templates.py` | ✅ Production-ready |
| **BigQuery POC Query** | `examples/poc_gkg_white_cross.sql` | ✅ Tested (500 rows, 5.8 GB) |
| **POC Results** | `data/gdelt_poc_results.csv` | ✅ Sept 20-30, 2026 |
| **HITL URLs** | `data/hitl_review_urls.csv` | ✅ 8 URLs for stance validation |
| **Diplomatic Flashpoints** | `data/diplomatic_gkg_exact_days.csv` | ✅ 54 records, 9 dates |
| **Food Security/Geopolitics** | `data/expanded_food_security_geopolitics.csv` | ✅ 130 records, 18 dates |
| **PhD Knowledge Article** | `docs/PHD_KNOWLEDGE_ARTICLE.md` | ✅ Full feasibility analysis |
| **Extraction Scripts** | `data/*.py` | ✅ Reproducible |

---

## 🔧 R9 Setup Checklist

### 1. Clone & Install Skill
```bash
# On R9
git clone https://github.com/PTaljaard/gdelt-skill.git
cd gdelt-skill

# Install dependencies
pip install -r requirements.txt
pip install -e .[bigquery,neo4j,llm]  # Optional extras

# Verify import
python -c "from scripts.gdelt_api import GDELTClient, GDELTBigQueryClient; print('OK')"
```

### 2. Credentials (Environment Variables)
```bash
# ~/.bashrc or .env file
export GCP_PROJECT="your-gcp-project"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
# OR: gcloud auth application-default login

export NEO4J_URI="neo4j://d7:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASS="your-password"

# Optional: GDELT API key for higher rate limits
export GDELT_API_KEY="your-key"

# Optional: LLM for claim extraction
export OPENAI_API_KEY="..."  # or use local Ollama
```

### 3. Verify BigQuery Access
```bash
python data/run_bq_poc.py
# Should return 500 rows, save to gdelt_poc_results.csv
```

### 4. Verify Network: R9 → D7 (Neo4j)
```bash
# From R9
telnet d7 7687
# Or test with Python
python -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('neo4j://d7:7687', auth=('neo4j','pass'))
with driver.session() as s:
    print(s.run('RETURN 1').single())
driver.close()
"
```

---

## 📋 Next Steps on R9 (Priority Order)

### Phase 1: Baseline Ingestion (Week 1)
```bash
# 1. Run historical Events query (1986-2014) - monthly batches
python examples/bq_historical.py

# 2. Run modern GKG query (2015-present) - monthly batches
# Use the theme filters from expanded_food_security_geopolitics.csv

# 3. Ingest to Neo4j (when D7 online)
python -c "
from scripts.gdelt_api import GDELTBigQueryClient
from neo4j import GraphDatabase
# ... use sync_events_to_neo4j() with driver
"
```

### Phase 2: LLM Claim Extraction (Week 2-3)
```bash
# 1. Export URLs from Neo4j for LLM processing
python -c "
# Query Neo4j for Event nodes with DocumentIdentifier
# Export to JSON for LLM pipeline
"

# 2. Run claim extraction (see PHD_METHODOLOGY.md for prompt)
# Input: DocumentIdentifier URLs
# Output: NarrativeClaim nodes (stance, claimant, evidence, certainty)

# 3. Load claims back to Neo4j
```

### Phase 3: Analysis & Visualization (Week 3-4)
```bash
# Cypher queries from docs/NEO4J_SCHEMA.md:
# - Narrative conflict map
# - Stance networks by claimant
# - Tone evolution over time
# - CAMEO → Theme bridging (1986 vs 2024)
```

---

## 🎯 Research Scope Summary (What We're Building)

### Three-Layer Narrative Map

| Layer | Time Range | Source | Key Themes |
|-------|------------|--------|------------|
| **1. Domestic Farm Violence** | 1986–2014 | Events (CAMEO) | Assault (18), Threaten (19), Mass Violence (20), Ethnic codes |
| | 2015–present | GKG | RURAL_SAFETY, CRIME_VIOLENCE, ETHNIC_CONFLICT, AFRIKANER |
| **2. International Diplomatic** | 2020–present | GKG | SANCTIONS, GENOCIDE, VISA_RESTRICTIONS, HUMAN_RIGHTS, DIPLOMACY |
| **3. Food Security/Geopolitics** | 2022–present | GKG | FERTILIZER, ENERGY_SECURITY, SUPPLY_CHAIN, IRAN, RUSSIA_UKRAINE, ISRAEL_HAMAS |

### Actor Network (Claimants)
| Cluster | Actors | Stance |
|---------|--------|--------|
| **Genocide Claim** | AfriForum, Afrikaner orgs, US refugee policy, some Western media | `GENOCIDE` |
| **Criminality Frame** | SA Govt/DIRCO, SAPS, ISS, SACP, Polity, most SA media | `CRIMINALITY` |
| **Political Violence** | EFF, MKP, "Dubul' ibhunu", Malema, Zuma | `POLITICAL_VIOLENCE` |
| **Diplomatic Pressure** | US State Dept, Trump admin, EU, UK, BRICS (Russia/China/Iran) | `HUMAN_RIGHTS_CONCERN` / `SOVEREIGNTY` |

### Your Lived Experience → Query Dimensions
| Your Reality | GKG Dimension | Flashpoint Dates |
|--------------|---------------|------------------|
| Diesel prices (US-Iran) | `ENERGY_SECURITY`, `OIL_PRICES`, `DIESEL` | 2022-06-15 |
| Fertilizer (Russia-Ukraine) | `FERTILIZER`, `AGRICULTURE_INPUTS` | 2022-02-24, 2022-03-15 |
| Tunnel plastic (Israel-Hamas-Iran) | `PLASTICS`, `TRADE_RESTRICTIONS` | 2023-10-07, 2024-04-13, 2024-10-01 |
| EWC land collapse | `EXPROPRIATION`, `PROPERTY_RIGHTS`, `LAND_REFORM` | 2023-02-15 |
| "Dubul' ibhunu" / MKP/EFF | `HATE_SPEECH`, `INCITEMENT`, `POLITICAL_VIOLENCE` | 2024-01-15 |
| ANC decline / GNU | `ELECTION`, `COALITION_GOVERNMENT` | 2024-05-29 |

---

## 📚 Key Documents to Re-read

1. **`docs/PHD_KNOWLEDGE_ARTICLE.md`** — Full PhD feasibility, methodology, timeline
2. **`docs/PHD_METHODOLOGY.md`** — Pipeline architecture, validation, ethics
3. **`docs/BIGQUERY.md`** — Partitioned query patterns, cost optimization
4. **`docs/NEO4J_SCHEMA.md`** — Graph schema, Cypher queries, sync logic
5. **`docs/NGRAMS_FALLBACK.md`** — API v2 migration interim solution

---

## ⚠️ What's Missing / Open Questions

| Gap | Status | Decision Needed |
|-----|--------|-----------------|
| **Actor-filtered GKG queries** | Not yet run | Filter V2Persons/Orgs/Locs for Putin, Netanyahu, Khamenei, Hamas, IRGC, Zuma, Malema |
| **LLM prompt templates** | Drafted in PHD_METHODOLOGY | Finalize few-shot examples from HITL coding |
| **Validation set** | 2 polity articles coded | Need 50+ human-coded for IAA |
| **Neo4j sync implementation** | Placeholder in skill | Implement Cypher MERGE when D7 online |
| **Hermes cron jobs** | Templates ready | Deploy when stack connected |
| **Publication venues** | Not targeted | Identify: *Political Analysis*, *J. Peace Research*, *Big Data & Society* |

---

## 🚀 Quick Start on R9 (One-Liner)

```bash
cd ~/gdelt-skill && \
git pull origin main && \
pip install -e .[bigquery,neo4j] && \
python data/run_bq_poc.py && \
echo "✅ Baseline verified. Next: python examples/bq_historical.py"
```

---

## 💭 Philosophical Note

> **You're not building a database. You're building an *epistemological instrument*.**
> 
> The GKG themes are the index. The URLs are the corpus. The LLM extracts the claims. The graph maps the *structure of disagreement*. Your lived experience (diesel, fertilizer, plastic, EWC, "dubul' ibhunu") is the ground truth that validates the instrument.
> 
> **Scope is wide by design** — the forces driving you off your land (global commodity chains, geopolitical alignments, local rhetoric, policy capture) *are* the system. Mapping their media representations across 40 years is the contribution.

---

## 📞 Resume Prompt for R9

> "Continue from session continuation guide. GitHub synced. Need to: (1) verify R9→D7 Neo4j connectivity, (2) run historical Events monthly batches (1986-2014), (3) run modern GKG monthly batches (2015-present) with expanded themes, (4) implement Neo4j sync, (5) build LLM claim extraction pipeline with HITL validation."

---

*Generated: October 3, 2026 | GitHub: PTaljaard/gdelt-skill@45aed5e*