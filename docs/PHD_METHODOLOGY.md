# PhD Methodology: Computational Narrative Analysis of South African Rural Violence (1986–present)

This document outlines the methodological framework for a doctoral dissertation using the GDELT skill to map **competing narratives** about South African farm violence — not to adjudicate truth, but to model the *structure of disagreement* across global media ecosystems.

## Research Questions

### Primary
> **How do competing sociopolitical narratives about South African rural violence (1986–present) emerge, propagate, and solidify across global media ecosystems — and what does the *structure of their disagreement* reveal about the epistemology of "genocide" claims in post-colonial transitions?**

### Sub-Questions
1. **Historical Continuity**: How do CAMEO-coded event patterns (1986–2014) prefigure modern narrative clusters?
2. **Narrative Inflection**: What GKG theme/tone shifts (2015–present) mark narrative regime changes?
3. **Claimant Networks**: Which actors (AfriForum, DIRCO, ISS, US State Dept, etc.) make which claims, with what evidence, and how do they cite each other?
4. **Epistemic Polarization**: How does stance diversity (GENOCIDE vs CRIMINALITY vs POLITICAL_VIOLENCE) correlate with media geography, language, and ownership?
5. **Algorithmic Mediation**: How does GDELT's own coding schema (CAMEO, themes, tone) *shape* the narratives it captures?

## Theoretical Framework

| Tradition | Concept | Operationalization |
|-----------|---------|-------------------|
| **Constructivist IR** | Narratives as political artifacts | Stance detection on claims |
| **Computational Social Science** | Event data as proxy for conflict | CAMEO codes + Goldstein + Tone |
| **Digital Humanities** | Distant reading of media | GKG themes + V2Tone + source URLs |
| **Critical Data Studies** | Data violence / algorithmic bias | Source diversity metrics, Western media overrepresentation |
| **Science & Technology Studies** | Infrastructure as epistemology | GDELT schema as boundary object |

## Data Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA ACQUISITION LAYER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  BigQuery Events (1986–2014)     │  BigQuery GKG (2015–present)            │
│  - Partitioned by DATEADDED       │  - Partitioned by DATE                   │
│  - Filter: ActionGeo_Country=SF   │  - Filter: V2Themes/Location=SA         │
│  - CAMEO 18/19/20 + ethnic codes  │  - V2Themes, V2Tone, V2Persons/Orgs     │
│  - Monthly batches (free tier)    │  - DocumentIdentifier URLs              │
└──────────────┬────────────────────┴────────────────┬────────────────────────┘
               │                                      │
               ▼                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      TRANSFORMATION LAYER (Neo4j)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  Nodes: Event, Actor, Location, Theme, ToneMetric, MediaOutlet              │
│  Edges: ACTOR_IN, LOCATED_IN, HAS_THEME, HAS_TONE, MENTIONS, REPORTS_ON     │
│  Provenance: source_table (events/gkg), extraction_batch, query_hash        │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LLM CLAIM EXTRACTION LAYER (PhD Innovation)               │
├─────────────────────────────────────────────────────────────────────────────┤
│  For each Event with DocumentIdentifier:                                    │
│  1. Fetch article text (newspaper3k / trafilatura)                          │
│  2. LLM prompt → Structured claims:                                         │
│     - Claimant (entity)                                                     │
│     - Stance (GENOCIDE/CRIMINALITY/POLITICAL_VIOLENCE/DISPUTED)            │
│     - Claim text (verbatim/summarized)                                      │
│     - Evidence cited (URLs, reports, stats)                                 │
│     - Certainty (0.0–1.0)                                                   │
│  3. Store as NarrativeClaim nodes + CLAIMED_BY + HAS_STANCE + CITES edges  │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ANALYSIS LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. Temporal narrative regime detection (change-point on stance dist)      │
│  2. Claimant network analysis (bipartite: Claimant ↔ Stance ↔ Evidence)    │
│  3. Source diversity metrics (Gini on media outlet country/language)       │
│  4. Tone-stance coupling (does negative tone predict GENOCIDE stance?)     │
│  5. CAMEO→Theme bridging (do 1986 event codes predict 2024 themes?)        │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Operationalization Details

### 1. Historical Events (1986–2014): CAMEO Proxy for "Rural Violence"

Since GKG doesn't exist pre-2015, we use **Events table CAMEO codes** as a proxy:

| Concept | CAMEO Operationalization |
|---------|--------------------------|
| Farm attack | `EventRootCode=18` (Assault) + `ActionGeo_CountryCode=SF` + rural ADM1 |
| Threat/intimidation | `EventRootCode=19` (Threaten) + `Actor1EthnicCode=AFR/BUE` |
| Mass violence claim | `EventRootCode=20` (Unconventional Mass Violence) |
| Political coercion | `EventRootCode=17` (Coerce) + land reform themes |

**Validation**: Human-code 200-event sample (1990, 1994, 2000) for precision/recall of CAMEO proxy.

### 2. Modern GKG (2015–present): Narrative-Rich Data

| GKG Field | Narrative Utility |
|-----------|-------------------|
| `V2Themes` | Standardized theme taxonomy (WB_135_RURAL_SAFETY, CRIME_VIOLENCE, etc.) |
| `V2Tone` | 9-dim sentiment (anxiety, frustration, polarity) — *intensity metric* |
| `V2Persons` / `V2Organizations` | Claimant identification (AfriForum, Ramaphosa, Blinken, etc.) |
| `DocumentIdentifier` | Source URLs for LLM full-text extraction |
| `SourceCommonName` | Media outlet provenance (bias/geography analysis) |

### 3. LLM Claim Extraction Schema

```python
class NarrativeClaim(BaseModel):
    claimant: str                    # "AfriForum", "DIRCO", "ISS", "US State Dept"
    stance: Literal["GENOCIDE", "CRIMINALITY", "POLITICAL_VIOLENCE", "DISPUTED"]
    claim_text: str                  # "Farm murders constitute a targeted campaign..."
    evidence_cited: List[str]        # ["https://afriforum.co.za/report.pdf", "SAPS 2023 stats"]
    certainty: float                 # 0.0–1.0 (self-assessed)
    themes: List[str]                # GKG themes this claim maps to
```

**Prompt strategy**: Few-shot with 20 human-coded examples. Use `instructor` for structured output.

### 4. Validation Protocol

| Validation | Method | Target |
|------------|--------|--------|
| CAMEO proxy precision | Human coding of 200 events | >0.75 F1 |
| LLM stance accuracy | 3-coder Krippendorff's α on 200 claims | α > 0.80 |
| Source diversity | Gini coefficient on outlet countries | Report, not optimize |
| Narrative regime shifts | Bayesian change-point on stance distribution | Identify inflection years |

## Chapter Structure

1. **Introduction**: "Narrative Conflict in the Algorithmic Archive"
2. **Literature Review**: 
   - GDELT in computational politics (critiques: Ward et al. 2013; Schrodt 2021)
   - SA farm murder discourse (AfriForum vs ISS vs DIRCO epistemologies)
   - Knowledge graphs for contested histories
3. **Methodology**: Pipeline architecture, operationalization, validation, ethics
4. **Historical Backbone** (1986–1994): Apartheid-era rural violence in GDELT
5. **Transition Period** (1994–2010): TRC, farm attack emergence, early framing
6. **Polarization Era** (2010–2020): "Kill the Boer", AfriForum, BRICS, diplomatic incidents
7. **Algorithmic Narrative Map** (2015–present): GKG+LLM results — claimant networks, evidence flows, stance clusters
8. **Discussion**: What disagreement *structure* reveals about post-colonial truth regimes
9. **Conclusion**: Contributions, limitations, open code/data for other contested histories

## Ethics & Positionality

- **Data violence acknowledgment**: Reducing trauma to tone scores requires qualitative counterweight (Chapter 4 close reading)
- **Algorithmic legitimation risk**: Graph looks "objective" — mitigate with source diversity metrics as first-class properties
- **Stance ≠ Truth**: Every claim gets `claimant` + `certainty`; no ground-truth labels
- **Positionality statement**: Researcher background (SA upbringing, Afrikaner heritage) disclosed in preface
- **Open science**: All code, queries, and derived data (not raw GDELT) published under MIT

## Reproducibility Artifacts

| Artifact | Location | Purpose |
|----------|----------|---------|
| BigQuery SQL templates | `docs/BIGQUERY.md` | Exact partitioned queries |
| Neo4j schema + Cypher | `docs/NEO4J_SCHEMA.md` | Graph construction |
| LLM prompts + few-shots | `examples/llm_prompts/` | Claim extraction |
| Validation notebooks | `notebooks/validation/` | Human coding, IAA |
| Analysis notebooks | `notebooks/analysis/` | Regime detection, networks |
| Cron job configs | `examples/cron_setup.py` | Hermes scheduling |

## Timeline (3-Year PhD)

| Year | Milestone |
|------|-----------|
| Y1 Q1–Q2 | BigQuery historical pipeline (1986–2014), CAMEO validation |
| Y1 Q3–Q4 | GKG modern pipeline (2015–2023), Neo4j schema, LLM prompt dev |
| Y2 Q1–Q2 | Full claim extraction run, claimant network construction |
| Y2 Q3–Q4 | Narrative regime detection, stance-tone coupling analysis |
| Y3 Q1 | Chapter drafting (historical + modern) |
| Y3 Q2 | Discussion, ethics, conclusion |
| Y3 Q3 | Defense prep, open-source release |

## Expected Contributions

1. **Methodological**: Reusable OSINT→KG→LLM pipeline for contested narrative analysis
2. **Empirical**: First 40-year computational map of SA rural violence narratives
3. **Theoretical**: "Disagreement structure" as analytic object in computational politics
4. **Infrastructural**: Open-source Hermes skill + Neo4j schema for GDELT research
5. **Critical**: Demonstration of GDELT's Western bias via source diversity metrics