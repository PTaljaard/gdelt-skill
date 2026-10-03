# Neo4j Graph Schema for GDELT Events

This document defines the Neo4j graph schema used by the GDELT skill for syncing events, actors, locations, themes, and narrative claims.

## Node Labels & Properties

### Event
Core event node from GDELT Events or GKG.

| Property | Type | Source | Description |
|----------|------|--------|-------------|
| `gkg_id` | String | GKG | `GKGRECORDID` (e.g., `20240930123456_12345`) |
| `global_event_id` | String | Events | `GLOBALEVENTID` |
| `date` | Date | Both | Event date |
| `source_table` | String | Both | `events` \| `gkg` \| `mentions` (provenance) |
| `event_code` | String | Events | CAMEO event code (e.g., `1823`) |
| `event_base_code` | String | Events | Base CAMEO code |
| `event_root_code` | String | Events | Root CAMEO code (e.g., `18`) |
| `goldstein_scale` | Float | Events | -10 to +10 cooperation/conflict |
| `avg_tone` | Float | Events | Document-level tone |
| `num_mentions` | Integer | Events | Count of mentions |
| `num_sources` | Integer | Events | Unique sources |
| `num_articles` | Integer | Events | Article count |
| `source_url` | String | Events | `SOURCEURL` (modern) |
| `document_identifier` | String | GKG | Source article URL |
| `source_common_name` | String | GKG | Media outlet name |
| `v2_tone_raw` | String | GKG | Raw V2Tone string |

### Actor (Person / Organization)
Unified actor node with type discriminator.

| Property | Type | Source | Description |
|----------|------|--------|-------------|
| `name` | String | Both | Actor name |
| `type` | String | Both | `Person` \| `Organization` |
| `country_code` | String | Events | `Actor1CountryCode` / `Actor2CountryCode` |
| `ethnic_code` | String | Events | `Actor1EthnicCode` / `Actor2EthnicCode` |
| `known_group_code` | String | Events | `Actor1KnownGroupCode` |
| `religion1_code` | String | Events | `Actor1Religion1Code` |
| `type1_code` | String | Events | `Actor1Type1Code` (CAMEO actor type) |
| `gkg_source` | String | GKG | `V2Persons` \| `V2Organizations` |

### Location
Geographic location from ActionGeo (Events) or V2Locations (GKG).

| Property | Type | Source | Description |
|----------|------|--------|-------------|
| `name` | String | Both | Full location name |
| `country` | String | Both | Country name |
| `country_code` | String | Events | `ActionGeo_CountryCode` |
| `adm1_code` | String | Events | `ActionGeo_ADM1Code` |
| `lat` | Float | Both | Latitude |
| `long` | Float | Both | Longitude |
| `feature_id` | String | Events | `ActionGeo_FeatureID` |
| `gkg_source` | String | GKG | Raw V2Locations entry |

### Theme
GDELT theme (CAMEO theme or GKG V2Themes).

| Property | Type | Source | Description |
|----------|------|--------|-------------|
| `name` | String | Both | Theme name (e.g., `CRIME_VIOLENCE`) |
| `source` | String | Both | `CAMEO` \| `GKG_V1` \| `GKG_V2` |

### ToneMetric
Parsed V2Tone components (GKG only).

| Property | Type | Source | Description |
|----------|------|--------|-------------|
| `tone` | Float | GKG | Overall tone |
| `positive` | Float | GKG | Positive score |
| `negative` | Float | GKG | Negative score |
| `polarity` | Float | GKG | Polarity |
| `activity` | Float | GKG | Activity density |
| `density` | Float | GKG | Word density |
| `anxiety` | Float | GKG | Anxiety score |
| `frustration` | Float | GKG | Frustration score |
| `confidence` | Float | GKG | Confidence score |

### NarrativeClaim (PhD Extension)
LLM-extracted claims from source articles.

| Property | Type | Source | Description |
|----------|------|--------|-------------|
| `claim_text` | String | LLM | Summarized claim |
| `claimant` | String | LLM | Who makes the claim |
| `stance` | String | LLM | `GENOCIDE` \| `CRIMINALITY` \| `POLITICAL_VIOLENCE` \| `DISPUTED` |
| `evidence_cited` | String[] | LLM | URLs, reports, statistics |
| `certainty` | Float | LLM | 0.0–1.0 |
| `extracted_at` | DateTime | LLM | Extraction timestamp |
| `model` | String | LLM | LLM model used |

### MediaOutlet
News source metadata.

| Property | Type | Source | Description |
|----------|------|--------|-------------|
| `name` | String | GKG | `SourceCommonName` |
| `domain` | String | GKG | Extracted from URL |
| `country` | String | GKG | `SourceCountry` |
| `language` | String | GKG | `SourceLang` |

## Relationships

| Relationship | From | To | Properties |
|--------------|------|-----|------------|
| `ACTOR_IN` | Event | Actor | `role`: `ACTOR1` \| `ACTOR2`, `tone`: Float |
| `LOCATED_IN` | Event | Location | `geo_type`: `ActionGeo` \| `Actor1Geo` \| `Actor2Geo` |
| `HAS_THEME` | Event | Theme | `source`: `CAMEO` \| `GKG_V1` \| `GKG_V2` |
| `HAS_TONE` | Event | ToneMetric | (all tone properties on node) |
| `HAS_GOLDSTEIN` | Event | GoldsteinScale | `value`: Float |
| `MENTIONS` | Event | Mention | `mention_type`, `doc_tone`, `source_name` |
| `HAS_CLAIM` | Event | NarrativeClaim | `extraction_method`: `LLM` |
| `CLAIMED_BY` | NarrativeClaim | Actor | `role`: `CLAIMANT` |
| `CITES` | NarrativeClaim | MediaOutlet | `url`: String |
| `REPORTS_ON` | MediaOutlet | Event | `url`: String |
| `HAS_STANCE` | NarrativeClaim | Stance | (enum node) |

## Cypher Schema Creation

```cypher
// Constraints
CREATE CONSTRAINT event_gkg_id IF NOT EXISTS FOR (e:Event) REQUIRE e.gkg_id IS UNIQUE;
CREATE CONSTRAINT event_global_id IF NOT EXISTS FOR (e:Event) REQUIRE e.global_event_id IS UNIQUE;
CREATE CONSTRAINT actor_name_type IF NOT EXISTS FOR (a:Actor) REQUIRE (a.name, a.type) IS UNIQUE;
CREATE CONSTRAINT location_name_country IF NOT EXISTS FOR (l:Location) REQUIRE (l.name, l.country) IS UNIQUE;
CREATE CONSTRAINT theme_name IF NOT EXISTS FOR (t:Theme) REQUIRE t.name IS UNIQUE;
CREATE CONSTRAINT claim_id IF NOT EXISTS FOR (c:NarrativeClaim) REQUIRE c.claim_id IS UNIQUE;

// Indexes
CREATE INDEX event_date IF NOT EXISTS FOR (e:Event) ON (e.date);
CREATE INDEX event_country IF NOT EXISTS FOR (e:Event) ON (e.action_geo_country_code);
CREATE INDEX actor_country IF NOT EXISTS FOR (a:Actor) ON (a.country_code);
CREATE INDEX claim_stance IF NOT EXISTS FOR (c:NarrativeClaim) ON (c.stance);
```

## Sync Logic (Upsert Patterns)

### Event + Actors + Location (Events API)

```cypher
// For each GDELTEvent
MERGE (e:Event {global_event_id: $geid})
SET e.date = date($date),
    e.event_code = $event_code,
    e.goldstein_scale = $goldstein,
    e.avg_tone = $avg_tone,
    e.source_table = 'events'

// Actor 1
MERGE (a1:Actor {name: $actor1_name, type: 'Person'})
SET a1.country_code = $actor1_country, a1.ethnic_code = $actor1_ethnic
MERGE (e)-[:ACTOR_IN {role: 'ACTOR1', tone: $avg_tone}]->(a1)

// Actor 2
MERGE (a2:Actor {name: $actor2_name, type: 'Person'})
SET a2.country_code = $actor2_country, a2.ethnic_code = $actor2_ethnic
MERGE (e)-[:ACTOR_IN {role: 'ACTOR2', tone: $avg_tone}]->(a2)

// ActionGeo Location
MERGE (l:Location {name: $action_geo_full, country: $action_geo_country})
SET l.lat = $lat, l.long = $long, l.country_code = $action_geo_country
MERGE (e)-[:LOCATED_IN {geo_type: 'ActionGeo'}]->(l)
```

### GKG Record + Themes + Persons/Orgs + Tone

```cypher
// For each GDELTGKGRecord
MERGE (e:Event {gkg_id: $gkg_id})
SET e.date = date($date),
    e.document_identifier = $doc_id,
    e.source_common_name = $source,
    e.source_table = 'gkg',
    e.v2_tone_raw = $v2_tone

// Themes
UNWIND $themes AS theme
MERGE (t:Theme {name: theme})
MERGE (e)-[:HAS_THEME {source: 'GKG_V2'}]->(t)

// Tone (parsed from V2Tone: tone,pos,neg,pol,act,den,anx,frus,conf)
CREATE (tm:ToneMetric {tone: $tone[0], positive: $tone[1], negative: $tone[2],
                        polarity: $tone[3], activity: $tone[4], density: $tone[5],
                        anxiety: $tone[6], frustration: $tone[7], confidence: $tone[8]})
MERGE (e)-[:HAS_TONE]->(tm)

// Persons
UNWIND $persons AS person
MERGE (a:Actor {name: person, type: 'Person'})
MERGE (e)-[:MENTIONS]->(a)

// Organizations
UNWIND $orgs AS org
MERGE (a:Actor {name: org, type: 'Organization'})
MERGE (e)-[:MENTIONS]->(a)
```

## PhD Narrative Graph Extensions

### Stance Enum Nodes

```cypher
// Create stance nodes once
MERGE (s:Stance {name: 'GENOCIDE'}) SET s.description = 'Claims targeted ethnic cleansing';
MERGE (s:Stance {name: 'CRIMINALITY'}) SET s.description = 'Claims ordinary criminal activity';
MERGE (s:Stance {name: 'POLITICAL_VIOLENCE'}) SET s.description = 'Claims politically motivated violence';
MERGE (s:Stance {name: 'DISPUTED'}) SET s.description = 'Conflicting evidence, no consensus';
```

### Claim Extraction Pipeline Output

```cypher
// After LLM extraction, create claim nodes linked to Event
MERGE (c:NarrativeClaim {
    claim_id: $claim_id,
    event_gkg_id: $event_gkg_id
})
SET c.claim_text = $claim_text,
    c.claimant = $claimant,
    c.stance = $stance,
    c.evidence_cited = $evidence,
    c.certainty = $certainty,
    c.extracted_at = datetime(),
    c.model = $model

MERGE (e:Event {gkg_id: $event_gkg_id})
MERGE (e)-[:HAS_CLAIM]->(c)

MERGE (a:Actor {name: $claimant, type: 'Organization'})
MERGE (c)-[:CLAIMED_BY]->(a)

MERGE (s:Stance {name: $stance})
MERGE (c)-[:HAS_STANCE]->(s)

// Evidence sources
UNWIND $evidence_cited AS url
MERGE (m:MediaOutlet {domain: apoc.text.url.parseDomain(url)})
SET m.url = url
MERGE (c)-[:CITES {url: url}]->(m)
```

## Query Patterns

### Timeline of Violence Events

```cypher
MATCH (e:Event)-[:LOCATED_IN]->(l:Location)
WHERE l.country = 'South Africa' AND e.date >= date('1986-01-01')
RETURN e.date, e.event_code, e.goldstein_scale, e.avg_tone, 
       l.name AS location, e.global_event_id
ORDER BY e.date
```

### Actor Network (Who interacts with whom)

```cypher
MATCH (a1:Actor)<-[:ACTOR_IN]-(e:Event)-[:ACTOR_IN]->(a2:Actor)
WHERE a1 <> a2 AND e.date >= date('2020-01-01')
RETURN a1.name, a2.name, count(e) AS interactions, 
       avg(e.goldstein_scale) AS avg_goldstein
ORDER BY interactions DESC
LIMIT 50
```

### Narrative Conflict Map (PhD Core Query)

```cypher
MATCH (c:NarrativeClaim)-[:CLAIMED_BY]->(a:Actor)
      -[:HAS_STANCE]->(s:Stance)
      <-[:HAS_STANCE]-(c2:NarrativeClaim)
WHERE c <> c2 AND c.stance <> c2.stance
RETURN a.name AS claimant, c.stance AS stance1, c2.stance AS stance2,
       c.claim_text, c2.claim_text, c.certainty, c2.certainty
```

### Tone Evolution Over Time

```cypher
MATCH (e:Event)-[:LOCATED_IN]->(l:Location)
WHERE l.country = 'South Africa' AND e.avg_tone IS NOT NULL
RETURN e.date, avg(e.avg_tone) AS avg_tone, count(e) AS events
ORDER BY e.date
```

## Export for Analysis

```cypher
// Export to CSV for pandas/networkx
CALL apoc.export.csv.query(
  "MATCH (e:Event)-[:ACTOR_IN]->(a:Actor) RETURN e.global_event_id, e.date, a.name, a.type",
  "gdelt_actor_network.csv", {}
)
```