#!/usr/bin/env python3
"""
GDELT 2.0 API Client for Hermes.
Provides Events, Mentions, and GKG API access with SA politics filter templates.
Neo4j sync uses placeholder when D7 is unavailable.

NOTE: GDELT API v2 is currently migrating to Spanner and endpoints return 404.
This client includes fallback to the Web NGrams dataset (interim solution).
See: https://blog.gdeltproject.org/using-the-new-web-ngrams-dataset-to-find-relevant-coverage/

GDELT BigQuery tables (recommended for large-scale queries):
- gdelt-bq.gdeltv2.events (Events table)
- gdelt-bq.gdeltv2.mentions (Mentions table)  
- gdelt-bq.gdeltv2.gkg (GKG table)
"""

import os
import time
import logging
import json
import gzip
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Iterator
from urllib.parse import urlencode, quote_plus
from datetime import datetime, timedelta
import requests

logger = logging.getLogger(__name__)

# Optional BigQuery imports
try:
    from google.cloud import bigquery
    from google.oauth2 import service_account
    BIGQUERY_AVAILABLE = True
except ImportError:
    BIGQUERY_AVAILABLE = False
    bigquery = None
    service_account = None


# =============================================================================
# Exceptions
# =============================================================================

class GDELTError(Exception):
    """Base exception for GDELT errors."""
    pass


class GDELTAPIError(GDELTError):
    """API returned an error response."""
    def __init__(self, message: str, status_code: int, response_text: str = ""):
        super().__init__(f"GDELT API error ({status_code}): {message}")
        self.status_code = status_code
        self.response_text = response_text


class GDELTRateLimitError(GDELTAPIError):
    """Rate limit exceeded (429)."""
    def __init__(self, retry_after: int = 60):
        super().__init__("Rate limit exceeded", 429)
        self.retry_after = retry_after


class GDELTValidationError(GDELTError):
    """Invalid request parameters."""
    pass


class GDELTAPIUnavailableError(GDELTError):
    """GDELT API v2 is currently unavailable (migration to Spanner)."""
    pass


# =============================================================================
# Filter Templates for SA Politics Monitoring
# =============================================================================

# Theme codes from GDELT: https://gdeltproject.org/data/lookups/CAMEO.themes.txt
# Actor codes: https://gdeltproject.org/data/lookups/CAMEO.actors.txt

FILTER_AFRIKANER_GENOCIDE = {
    "theme": "GENOCIDE,ETHNIC_VIOLENCE,WHITE_FARMERS,AFRIKANER,BOER,FARM_ATTACK",
    "country": "ZA",
    "sourcelang": "english",
}

FILTER_RSA_USA_DIPLOMATIC = {
    "actor": "USA,UNITED_STATES,SOUTH_AFRICA",
    "theme": "DIPLOMATIC_DISPUTE,SANCTIONS,VISA_RESTRICTIONS,DIPLOMATIC_ROW",
    "country": "ZA,US",
    "sourcelang": "english",
}

FILTER_USA_VISA_SANCTIONS = {
    "theme": "VISA_RESTRICTIONS,SANCTIONS,TRAVEL_BAN,MAGNITSKY,SANCTIONS_EVASION",
    "actor": "USA,SOUTH_AFRICA",
    "country": "ZA,US",
    "sourcelang": "english",
}

FILTER_RSA_IRAN_RUSSIA_ALIGNMENT = {
    "actor": "IRAN,RUSSIA,CHINA,BRICS,SOUTH_AFRICA",
    "theme": "MILITARY_COOPERATION,ECONOMIC_PARTNERSHIP,DIPLOMATIC_SUPPORT,STRATEGIC_ALLIANCE",
    "country": "ZA,IR,RU,CN",
    "sourcelang": "english",
}

FILTER_BRICS_WART_COUNTRIES = {
    "actor": "RUSSIA,CHINA,IRAN,NORTH_KOREA,VENEZUELA,SYRIA,BELARUS,SOUTH_AFRICA",
    "theme": "ALLIANCE,SANCTIONS_EVASION,MILITARY_COOPERATION,ECONOMIC_COOPERATION",
    "sourcelang": "english",
}

# Convenience list of all SA filters
SA_FILTERS = {
    "afrikaner_genocide": FILTER_AFRIKANER_GENOCIDE,
    "rsa_usa_diplomatic": FILTER_RSA_USA_DIPLOMATIC,
    "usa_visa_sanctions": FILTER_USA_VISA_SANCTIONS,
    "rsa_iran_russia_alignment": FILTER_RSA_IRAN_RUSSIA_ALIGNMENT,
    "brics_wart_countries": FILTER_BRICS_WART_COUNTRIES,
}


# SA-specific search terms for NGrams fallback
SA_NGRAM_SEARCH_TERMS = {
    "afrikaner_genocide": [
        "afrikaner genocide", "farm attacks", "farm murders", "white farmers",
        "boer genocide", "plaasmoorde", "kill the boer", "expropriation",
        "south africa farm", "south africa expropriation", "ramaphosa farm",
    ],
    "rsa_usa_diplomatic": [
        "south africa usa diplomatic", "south africa united states tension",
        "ramaphosa biden", "south africa usa relations",
        "south africa washington", "pretoria washington",
    ],
    "usa_visa_sanctions": [
        "south africa visa restrictions", "south africa sanctions",
        "magnitsky south africa", "usa travel ban south africa",
        "south africa visa ban", "sanctions south africa",
    ],
    "rsa_iran_russia_alignment": [
        "south africa iran", "south africa russia", "south africa china brics",
        "ramaphosa putin", "south africa iran military", "brics south africa",
        "south africa russia china", "pretoria moscow beijing",
    ],
    "brics_wart_countries": [
        "south africa russia china iran", "brics sanctions evasion",
        "south africa north korea", "south africa venezuela",
        "brics alliance", "south africa brics",
    ],
    "witkruis_memorial": [
        "witkruis", "witkruis memorial", "white cross memorial",
        "washington mall memorial", "south africa washington memorial",
        "afrikaner memorial washington", "crosses washington mall",
    ],
}

# Combined search terms for all SA filters
ALL_SA_NGRAM_TERMS = list(set(
    term for terms in SA_NGRAM_SEARCH_TERMS.values() for term in terms
))


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class GDELTEvent:
    """Parsed GDELT Event record."""
    global_event_id: str
    day: int
    month_year: int
    year: int
    fraction_date: float
    actor1_code: str
    actor1_name: str
    actor1_country_code: str
    actor1_known_group_code: str
    actor1_ethnic_code: str
    actor1_religion1_code: str
    actor1_religion2_code: str
    actor1_type1_code: str
    actor1_type2_code: str
    actor1_type3_code: str
    actor2_code: str
    actor2_name: str
    actor2_country_code: str
    actor2_known_group_code: str
    actor2_ethnic_code: str
    actor2_religion1_code: str
    actor2_religion2_code: str
    actor2_type1_code: str
    actor2_type2_code: str
    actor2_type3_code: str
    is_root_event: int
    event_code: str
    event_base_code: str
    event_root_code: str
    quad_class: int
    goldstein_scale: float
    num_mentions: int
    num_sources: int
    num_articles: int
    avg_tone: float
    actor1_geo_type: int
    actor1_geo_fullname: str
    actor1_geo_country_code: str
    actor1_geo_adm1_code: str
    actor1_geo_lat: float
    actor1_geo_lon: float
    actor1_geo_feature_id: str
    actor2_geo_type: int
    actor2_geo_fullname: str
    actor2_geo_country_code: str
    actor2_geo_adm1_code: str
    actor2_geo_lat: float
    actor2_geo_lon: float
    actor2_geo_feature_id: str
    action_geo_type: int
    action_geo_fullname: str
    action_geo_country_code: str
    action_geo_adm1_code: str
    action_geo_lat: float
    action_geo_lon: float
    action_geo_feature_id: str
    date_added: int
    source_url: str

    @classmethod
    def from_tsv_row(cls, row: List[str]) -> "GDELTEvent":
        """Parse a TSV row from GDELT Events API."""
        # GDELT Events TSV has 61 columns
        # See: http://data.gdeltproject.org/documentation/Event-Data-Codebook.pdf
        return cls(
            global_event_id=row[0] if len(row) > 0 else "",
            day=int(row[1]) if len(row) > 1 and row[1] else 0,
            month_year=int(row[2]) if len(row) > 2 and row[2] else 0,
            year=int(row[3]) if len(row) > 3 and row[3] else 0,
            fraction_date=float(row[4]) if len(row) > 4 and row[4] else 0.0,
            actor1_code=row[5] if len(row) > 5 else "",
            actor1_name=row[6] if len(row) > 6 else "",
            actor1_country_code=row[7] if len(row) > 7 else "",
            actor1_known_group_code=row[8] if len(row) > 8 else "",
            actor1_ethnic_code=row[9] if len(row) > 9 else "",
            actor1_religion1_code=row[10] if len(row) > 10 else "",
            actor1_religion2_code=row[11] if len(row) > 11 else "",
            actor1_type1_code=row[12] if len(row) > 12 else "",
            actor1_type2_code=row[13] if len(row) > 13 else "",
            actor1_type3_code=row[14] if len(row) > 14 else "",
            actor2_code=row[15] if len(row) > 15 else "",
            actor2_name=row[16] if len(row) > 16 else "",
            actor2_country_code=row[17] if len(row) > 17 else "",
            actor2_known_group_code=row[18] if len(row) > 18 else "",
            actor2_ethnic_code=row[19] if len(row) > 19 else "",
            actor2_religion1_code=row[20] if len(row) > 20 else "",
            actor2_religion2_code=row[21] if len(row) > 21 else "",
            actor2_type1_code=row[22] if len(row) > 22 else "",
            actor2_type2_code=row[23] if len(row) > 23 else "",
            actor2_type3_code=row[24] if len(row) > 24 else "",
            is_root_event=int(row[25]) if len(row) > 25 and row[25] else 0,
            event_code=row[26] if len(row) > 26 else "",
            event_base_code=row[27] if len(row) > 27 else "",
            event_root_code=row[28] if len(row) > 28 else "",
            quad_class=int(row[29]) if len(row) > 29 and row[29] else 0,
            goldstein_scale=float(row[30]) if len(row) > 30 and row[30] else 0.0,
            num_mentions=int(row[31]) if len(row) > 31 and row[31] else 0,
            num_sources=int(row[32]) if len(row) > 32 and row[32] else 0,
            num_articles=int(row[33]) if len(row) > 33 and row[33] else 0,
            avg_tone=float(row[34]) if len(row) > 34 and row[34] else 0.0,
            actor1_geo_type=int(row[35]) if len(row) > 35 and row[35] else 0,
            actor1_geo_fullname=row[36] if len(row) > 36 else "",
            actor1_geo_country_code=row[37] if len(row) > 37 else "",
            actor1_geo_adm1_code=row[38] if len(row) > 38 else "",
            actor1_geo_lat=float(row[39]) if len(row) > 39 and row[39] else 0.0,
            actor1_geo_lon=float(row[40]) if len(row) > 40 and row[40] else 0.0,
            actor1_geo_feature_id=row[41] if len(row) > 41 else "",
            actor2_geo_type=int(row[42]) if len(row) > 42 and row[42] else 0,
            actor2_geo_fullname=row[43] if len(row) > 43 else "",
            actor2_geo_country_code=row[44] if len(row) > 44 else "",
            actor2_geo_adm1_code=row[45] if len(row) > 45 else "",
            actor2_geo_lat=float(row[46]) if len(row) > 46 and row[46] else 0.0,
            actor2_geo_lon=float(row[47]) if len(row) > 47 and row[47] else 0.0,
            actor2_geo_feature_id=row[48] if len(row) > 48 else "",
            action_geo_type=int(row[49]) if len(row) > 49 and row[49] else 0,
            action_geo_fullname=row[50] if len(row) > 50 else "",
            action_geo_country_code=row[51] if len(row) > 51 else "",
            action_geo_adm1_code=row[52] if len(row) > 52 else "",
            action_geo_lat=float(row[53]) if len(row) > 53 and row[53] else 0.0,
            action_geo_lon=float(row[54]) if len(row) > 54 and row[54] else 0.0,
            action_geo_feature_id=row[55] if len(row) > 55 else "",
            date_added=int(row[56]) if len(row) > 56 and row[56] else 0,
            source_url=row[57] if len(row) > 57 else "",
        )


@dataclass
class GDELTMention:
    """Parsed GDELT Mention record."""
    global_event_id: str
    event_time_date: int
    mention_time_date: int
    mention_type: int
    mention_source_name: str
    mention_identifier: str
    mention_doc_tone: float
    mention_doc_translation_info: str
    mention_doc_extras: str

    @classmethod
    def from_tsv_row(cls, row: List[str]) -> "GDELTMention":
        return cls(
            global_event_id=row[0] if len(row) > 0 else "",
            event_time_date=int(row[1]) if len(row) > 1 and row[1] else 0,
            mention_time_date=int(row[2]) if len(row) > 2 and row[2] else 0,
            mention_type=int(row[3]) if len(row) > 3 and row[3] else 0,
            mention_source_name=row[4] if len(row) > 4 else "",
            mention_identifier=row[5] if len(row) > 5 else "",
            mention_doc_tone=float(row[6]) if len(row) > 6 and row[6] else 0.0,
            mention_doc_translation_info=row[7] if len(row) > 7 else "",
            mention_doc_extras=row[8] if len(row) > 8 else "",
        )


@dataclass
class GDELTGKGRecord:
    """Parsed GDELT GKG record."""
    gkg_record_id: str
    date: int
    source_collection_id: int
    source_common_name: str
    document_identifier: str
    v1_counts: str
    v1_themes: str
    v1_locations: str
    v1_persons: str
    v1_organizations: str
    v1_tone: str
    v1_dates: str
    v1_gcam: str
    v2_1_allnames: str
    v2_1_amounts: str
    v2_2_allnames: str
    v2_2_amounts: str
    v2_3_allnames: str
    v2_3_amounts: str
    v2_4_allnames: str
    v2_4_amounts: str
    v2_5_allnames: str
    v2_5_amounts: str
    v2_6_allnames: str
    v2_6_amounts: str
    v2_7_allnames: str
    v2_7_amounts: str
    v2_8_allnames: str
    v2_8_amounts: str
    v2_9_allnames: str
    v2_9_amounts: str
    v2_10_allnames: str
    v2_10_amounts: str

    @classmethod
    def from_tsv_row(cls, row: List[str]) -> "GDELTGKGRecord":
        return cls(
            gkg_record_id=row[0] if len(row) > 0 else "",
            date=int(row[1]) if len(row) > 1 and row[1] else 0,
            source_collection_id=int(row[2]) if len(row) > 2 and row[2] else 0,
            source_common_name=row[3] if len(row) > 3 else "",
            document_identifier=row[4] if len(row) > 4 else "",
            v1_counts=row[5] if len(row) > 5 else "",
            v1_themes=row[6] if len(row) > 6 else "",
            v1_locations=row[7] if len(row) > 7 else "",
            v1_persons=row[8] if len(row) > 8 else "",
            v1_organizations=row[9] if len(row) > 9 else "",
            v1_tone=row[10] if len(row) > 10 else "",
            v1_dates=row[11] if len(row) > 11 else "",
            v1_gcam=row[12] if len(row) > 12 else "",
            v2_1_allnames=row[13] if len(row) > 13 else "",
            v2_1_amounts=row[14] if len(row) > 14 else "",
            v2_2_allnames=row[15] if len(row) > 15 else "",
            v2_2_amounts=row[16] if len(row) > 16 else "",
            v2_3_allnames=row[17] if len(row) > 17 else "",
            v2_3_amounts=row[18] if len(row) > 18 else "",
            v2_4_allnames=row[19] if len(row) > 19 else "",
            v2_4_amounts=row[20] if len(row) > 20 else "",
            v2_5_allnames=row[21] if len(row) > 21 else "",
            v2_5_amounts=row[22] if len(row) > 22 else "",
            v2_6_allnames=row[23] if len(row) > 23 else "",
            v2_6_amounts=row[24] if len(row) > 24 else "",
            v2_7_allnames=row[25] if len(row) > 25 else "",
            v2_7_amounts=row[26] if len(row) > 26 else "",
            v2_8_allnames=row[27] if len(row) > 27 else "",
            v2_8_amounts=row[28] if len(row) > 28 else "",
            v2_9_allnames=row[29] if len(row) > 29 else "",
            v2_9_amounts=row[30] if len(row) > 30 else "",
            v2_10_allnames=row[31] if len(row) > 31 else "",
            v2_10_amounts=row[32] if len(row) > 32 else "",
        )


# =============================================================================
# Query Builders
# =============================================================================

class EventQueryBuilder:
    """Builds GDELT Events API query strings."""

    def __init__(self, filters: Optional[Dict[str, str]] = None):
        self.filters = filters or {}

    def add_filter(self, key: str, value: str) -> "EventQueryBuilder":
        self.filters[key] = value
        return self

    def build(self) -> str:
        """Build query string for GDELT Events API."""
        parts = []
        for key, value in self.filters.items():
            if value:
                parts.append(f"{key}:{value}")
        return " ".join(parts)


class MentionQueryBuilder:
    """Builds GDELT Mentions API query strings."""

    def __init__(self, filters: Optional[Dict[str, str]] = None):
        self.filters = filters or {}

    def add_filter(self, key: str, value: str) -> "MentionQueryBuilder":
        self.filters[key] = value
        return self

    def build(self) -> str:
        parts = []
        for key, value in self.filters.items():
            if value:
                parts.append(f"{key}:{value}")
        return " ".join(parts)


class GKGQueryBuilder:
    """Builds GDELT GKG API query strings."""

    def __init__(self, filters: Optional[Dict[str, str]] = None):
        self.filters = filters or {}

    def add_filter(self, key: str, value: str) -> "GKGQueryBuilder":
        self.filters[key] = value
        return self

    def build(self) -> str:
        parts = []
        for key, value in self.filters.items():
            if value:
                parts.append(f"{key}:{value}")
        return " ".join(parts)


# =============================================================================
# API Endpoints
# =============================================================================

class Endpoints:
    EVENTS = "https://api.gdeltproject.org/api/v2/events/events"
    MENTIONS = "https://api.gdeltproject.org/api/v2/mentions/mentions"
    GKG = "https://api.gdeltproject.org/api/v2/gkg/gkg"
    # Web NGrams dataset (interim solution while API v2 migrates to Spanner)
    NGRAMS_BASE = "https://data.gdeltproject.org/gdeltv5/weblegacy/ngrams"
    NGRAMS_TOC_BASE = "https://data.gdeltproject.org/gdeltv5/weblegacy/ngrams"


# =============================================================================
# Main Client
# =============================================================================

class GDELTClient:
    """
    GDELT 2.0 API Client.
    
    Provides access to Events, Mentions, and GKG APIs with built-in
    SA politics filter templates, rate limiting, and Neo4j sync.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        rate_limit: float = 1.0,  # requests per second
        max_retries: int = 3,
        timeout: int = 30,
    ):
        """
        Initialize GDELT client.
        
        Args:
            api_key: Optional GDELT API key for higher rate limits
            rate_limit: Max requests per second (default 1.0 for free tier)
            max_retries: Max retry attempts for failed requests
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("GDELT_API_KEY")
        self.rate_limit = rate_limit
        self.max_retries = max_retries
        self.timeout = timeout
        self._last_request_time = 0.0
        self._session = requests.Session()
        if self.api_key:
            self._session.headers.update({"Authorization": f"Bearer {self.api_key}"})

    def _rate_limit_wait(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        min_interval = 1.0 / self.rate_limit
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)

    def _request(self, url: str, params: Dict[str, Any]) -> requests.Response:
        """Make HTTP request with retry logic and rate limiting."""
        self._rate_limit_wait()
        
        for attempt in range(self.max_retries + 1):
            try:
                self._last_request_time = time.time()
                response = self._session.get(url, params=params, timeout=self.timeout)
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    if attempt < self.max_retries:
                        logger.warning(f"Rate limited, waiting {retry_after}s (attempt {attempt + 1}/{self.max_retries})")
                        time.sleep(retry_after)
                        continue
                    raise GDELTRateLimitError(retry_after)
                
                if response.status_code >= 500:
                    if attempt < self.max_retries:
                        wait_time = 2 ** attempt
                        logger.warning(f"Server error {response.status_code}, retrying in {wait_time}s")
                        time.sleep(wait_time)
                        continue
                    raise GDELTAPIError(
                        f"Server error: {response.status_code}",
                        response.status_code,
                        response.text
                    )
                
                if response.status_code >= 400:
                    raise GDELTAPIError(
                        f"Client error: {response.status_code}",
                        response.status_code,
                        response.text
                    )
                
                return response
                
            except requests.Timeout:
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    logger.warning(f"Timeout, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                raise GDELTAPIError("Request timeout", 408)
            
            except requests.RequestException as e:
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    logger.warning(f"Request failed: {e}, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                raise GDELTAPIError(f"Request failed: {e}", 0)

    def _fetch_tsv(self, url: str, params: Dict[str, Any]) -> Iterator[List[str]]:
        """Fetch TSV data and yield parsed rows."""
        response = self._request(url, params)
        for line in response.iter_lines(decode_unicode=True):
            if line.strip():
                yield line.split("\t")

    # -------------------------------------------------------------------------
    # Events API
    # -------------------------------------------------------------------------

    def events_query(
        self,
        query: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_records: int = 250,
        format: str = "tsv",
    ) -> List[GDELTEvent]:
        """
        Query GDELT Events API.
        
        Args:
            query: GDELT query string (use EventQueryBuilder or raw)
            start_date: YYYYMMDD format
            end_date: YYYYMMDD format
            max_records: Maximum records to return (max 250 per request)
            format: Output format (tsv, json, csv)
        
        Returns:
            List of GDELTEvent objects
        """
        params = {
            "query": query,
            "format": format,
            "maxrecords": str(max_records),
        }
        if start_date:
            params["startdatetime"] = start_date.replace("-", "")
        if end_date:
            params["enddatetime"] = end_date.replace("-", "")
        
        events = []
        for row in self._fetch_tsv(Endpoints.EVENTS, params):
            if len(row) >= 58:  # Minimum viable row
                events.append(GDELTEvent.from_tsv_row(row))
        return events

    # -------------------------------------------------------------------------
    # Mentions API
    # -------------------------------------------------------------------------

    def mentions_query(
        self,
        query: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_records: int = 250,
        format: str = "tsv",
    ) -> List[GDELTMention]:
        """Query GDELT Mentions API."""
        params = {
            "query": query,
            "format": format,
            "maxrecords": str(max_records),
        }
        if start_date:
            params["startdatetime"] = start_date.replace("-", "")
        if end_date:
            params["enddatetime"] = end_date.replace("-", "")
        
        mentions = []
        for row in self._fetch_tsv(Endpoints.MENTIONS, params):
            if len(row) >= 9:
                mentions.append(GDELTMention.from_tsv_row(row))
        return mentions

    # -------------------------------------------------------------------------
    # GKG API
    # -------------------------------------------------------------------------

    def gkg_query(
        self,
        query: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_records: int = 250,
        format: str = "tsv",
    ) -> List[GDELTGKGRecord]:
        """Query GDELT Global Knowledge Graph API."""
        params = {
            "query": query,
            "format": format,
            "maxrecords": str(max_records),
        }
        if start_date:
            params["startdatetime"] = start_date.replace("-", "")
        if end_date:
            params["enddatetime"] = end_date.replace("-", "")
        
        records = []
        for row in self._fetch_tsv(Endpoints.GKG, params):
            if len(row) >= 33:
                records.append(GDELTGKGRecord.from_tsv_row(row))
        return records

    # -------------------------------------------------------------------------
    # Web NGrams Dataset (Interim Solution)
    # -------------------------------------------------------------------------

    def _build_ngrams_url(self, timestamp: datetime) -> str:
        """Build NGrams URL for a given timestamp (rounded to nearest minute)."""
        # NGrams files are named YYYYMMHHMM00
        ts_str = timestamp.strftime("%Y%m%d%H%M00")
        return f"{Endpoints.NGRAMS_BASE}/{ts_str}.ngrams.txt.gz"

    def _build_toc_url(self, timestamp: datetime) -> str:
        """Build TOC URL for a given timestamp."""
        ts_str = timestamp.strftime("%Y%m%d%H%M00")
        return f"{Endpoints.NGRAMS_TOC_BASE}/{ts_str}.toc.json.gz"

    def _fetch_gzipped_json(self, url: str) -> Dict[str, Any]:
        """Fetch and decompress a gzipped JSON file (JSON Lines format)."""
        response = self._request(url, {})
        content = gzip.decompress(response.content)
        # TOC is JSON Lines - one JSON object per line
        result = {}
        for line in content.decode("utf-8").splitlines():
            if line.strip():
                obj = json.loads(line)
                result[obj["ID"]] = obj
        return result

    def _fetch_gzipped_tsv(self, url: str) -> Iterator[List[str]]:
        """Fetch and decompress a gzipped TSV file, yield parsed rows."""
        response = self._request(url, {})
        content = gzip.decompress(response.content)
        for line in content.decode("utf-8").splitlines():
            if line.strip():
                yield line.split("\t")

    def ngrams_search(
        self,
        terms: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_files: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Search GDELT Web NGrams dataset for terms.
        
        This is the interim solution while GDELT API v2 migrates to Spanner.
        NGrams are released every minute (with 15-min heartbeat gaps).
        
        Args:
            terms: List of search terms (case-insensitive)
            start_date: YYYY-MM-DD (defaults to 2 weeks ago)
            end_date: YYYY-MM-DD (defaults to today)
            max_files: Maximum NGrams files to process
        
        Returns:
            List of matching records with doc_id, term, count, url, title, date
        """
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        # Normalize search terms to lowercase
        search_terms = [t.lower() for t in terms]
        
        results = []
        files_processed = 0
        current = start_dt
        
        while current <= end_dt and files_processed < max_files:
            # NGrams released every minute but only every 15 minutes in practice
            # Try current minute, then +1, +2... up to +14 to find available files
            for offset in range(15):
                try_ts = current + timedelta(minutes=offset)
                try_url = self._build_ngrams_url(try_ts)
                toc_url = self._build_toc_url(try_ts)
                
                try:
                    # Check if file exists with HEAD request
                    head = self._session.head(try_url, timeout=10)
                    if head.status_code != 200:
                        continue
                    
                    # Fetch TOC for URL mapping
                    toc_data = {}
                    try:
                        toc_data = self._fetch_gzipped_json(toc_url)
                    except Exception:
                        pass
                    
                    # Search NGrams
                    for row in self._fetch_gzipped_tsv(try_url):
                        if len(row) >= 3:
                            doc_id, quadgram, count = row[0], row[1], row[2]
                            quadgram_lower = quadgram.lower()
                            
                            # Check if any search term appears in the quadgram
                            for term in search_terms:
                                if term in quadgram_lower:
                                    # Convert doc_id to int for TOC lookup (TOC IDs are integers)
                                    try:
                                        toc_key = int(doc_id)
                                    except ValueError:
                                        toc_key = doc_id
                                    toc_entry = toc_data.get(toc_key, {})
                                    results.append({
                                        "doc_id": doc_id,
                                        "term_matched": term,
                                        "quadgram": quadgram,
                                        "count": int(count),
                                        "url": toc_entry.get("url", ""),
                                        "title": toc_entry.get("title", ""),
                                        "date": toc_entry.get("date", ""),
                                        "lang": toc_entry.get("lang", ""),
                                        "ngrams_timestamp": try_ts.isoformat(),
                                    })
                                    break  # Don't double-count same quadgram
                    
                    files_processed += 1
                    logger.info(f"Processed NGrams file: {try_ts.isoformat()}")
                    break  # Found valid file for this time slot
                    
                except Exception as e:
                    logger.debug(f"NGrams file not available for {try_ts}: {e}")
                    continue
            
            # Move to next 15-minute block (GDELT heartbeat)
            current += timedelta(minutes=15)
        
        logger.info(f"NGrams search complete: {len(results)} matches from {files_processed} files")
        return results

    def ngrams_search_sa_filter(
        self,
        filter_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_files: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Search NGrams using pre-built SA filter search terms.
        
        Args:
            filter_name: One of SA_NGRAM_SEARCH_TERMS keys
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD
            max_files: Maximum NGrams files to process
        
        Returns:
            List of matching records
        """
        if filter_name not in SA_NGRAM_SEARCH_TERMS:
            raise GDELTValidationError(f"Unknown NGrams filter: {filter_name}. Available: {list(SA_NGRAM_SEARCH_TERMS.keys())}")
        
        terms = SA_NGRAM_SEARCH_TERMS[filter_name]
        return self.ngrams_search(terms, start_date, end_date, max_files)

    def query_sa_filter(
        self,
        filter_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_records: int = 250,
        api: str = "events",
    ) -> List[Any]:
        """
        Query using a pre-built SA politics filter.
        
        Tries API v2 first, falls back to NGrams if unavailable.
        
        Args:
            filter_name: One of SA_FILTERS keys or SA_NGRAM_SEARCH_TERMS keys
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD
            max_records: Max records (for API v2)
            api: "events", "mentions", "gkg", or "ngrams"
        
        Returns:
            List of parsed records (GDELTEvent/GDELTMention/GDELTGKGRecord for API,
            or dict for NGrams)
        """
        # Check both filter dictionaries
        all_filters = {**SA_FILTERS, **SA_NGRAM_SEARCH_TERMS}
        if filter_name not in all_filters:
            raise GDELTValidationError(f"Unknown filter: {filter_name}. Available: {list(all_filters.keys())}")
        
        # If explicitly requesting NGrams or API unavailable, use NGrams
        if api == "ngrams":
            return self.ngrams_search_sa_filter(filter_name, start_date, end_date, max_files=max_records//10 + 1)
        
        # Try API v2 (only for SA_FILTERS, not NGRAM-only filters)
        if filter_name in SA_FILTERS:
            filter_dict = SA_FILTERS[filter_name]
            builder = EventQueryBuilder(filter_dict)
            query = builder.build()
            
            try:
                if api == "events":
                    return self.events_query(query, start_date, end_date, max_records)
                elif api == "mentions":
                    return self.mentions_query(query, start_date, end_date, max_records)
                elif api == "gkg":
                    return self.gkg_query(query, start_date, end_date, max_records)
                else:
                    raise GDELTValidationError(f"Unknown API: {api}")
            except GDELTAPIError as e:
                if e.status_code == 404:
                    logger.warning(f"GDELT API v2 unavailable (404), falling back to NGrams for {filter_name}")
                    return self.ngrams_search_sa_filter(filter_name, start_date, end_date, max_files=max_records//10 + 1)
                raise
        else:
            # NGrams-only filter, use NGrams
            return self.ngrams_search_sa_filter(filter_name, start_date, end_date, max_files=max_records//10 + 1)

    # -------------------------------------------------------------------------
    # Neo4j Sync (Placeholder for D7 offline)
    # -------------------------------------------------------------------------

    def sync_events_to_neo4j(
        self,
        events: List[GDELTEvent],
        driver: Optional[Any] = None,
        batch_size: int = 100,
    ) -> Dict[str, int]:
        """
        Sync events to Neo4j graph database.
        
        Placeholder implementation for when D7/Neo4j is unavailable.
        When D7 is online, provide a neo4j.Driver instance.
        
        Args:
            events: List of GDELTEvent objects
            driver: Optional neo4j.Driver instance (when D7 available)
            batch_size: Batch size for writes
        
        Returns:
            Dict with counts of nodes/relationships created
        """
        if driver is None:
            logger.warning("Neo4j driver not provided - skipping sync (D7 offline)")
            # Return mock counts for testing
            return {
                "events": len(events),
                "persons": 0,
                "organizations": 0,
                "locations": 0,
                "themes": 0,
                "relationships": 0,
                "skipped": True,
                "reason": "No Neo4j driver provided (D7 offline)"
            }
        
        # TODO: Implement actual Neo4j sync when D7 is available
        # This would use the driver to run Cypher MERGE statements
        # for Event, Person, Organization, Location, Theme nodes
        # and ACTOR_IN, LOCATED_IN, HAS_TONE, HAS_GOLDSTEIN relationships
        
        return {
            "events": 0,
            "persons": 0,
            "organizations": 0,
            "locations": 0,
            "themes": 0,
            "relationships": 0,
            "skipped": True,
            "reason": "Neo4j sync not yet implemented"
        }


# =============================================================================
# BigQuery Client (Recommended for large-scale GDELT queries)
# =============================================================================

class GDELTBigQueryClient:
    """
    Google BigQuery client for GDELT 2.0 datasets.
    
    GDELT maintains public BigQuery tables:
    - gdelt-bq.gdeltv2.events (Events table)
    - gdelt-bq.gdeltv2.mentions (Mentions table)
    - gdelt-bq.gdeltv2.gkg (GKG table)
    
    Requires: pip install google-cloud-bigquery
    Auth: GOOGLE_APPLICATION_CREDENTIALS or service account key
    """
    
    # GDELT BigQuery table references
    TABLES = {
        "events": "gdelt-bq.gdeltv2.events",
        "mentions": "gdelt-bq.gdeltv2.mentions", 
        "gkg": "gdelt-bq.gdeltv2.gkg",
    }
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        credentials_path: Optional[str] = None,
        location: str = "US",
    ):
        """
        Initialize BigQuery client.
        
        Args:
            project_id: GCP project ID (optional, uses default if not provided)
            credentials_path: Path to service account JSON key file
            location: BigQuery location (default US)
        """
        if not BIGQUERY_AVAILABLE:
            raise GDELTError("google-cloud-bigquery not installed. Run: pip install google-cloud-bigquery")
        
        if credentials_path:
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            self.client = bigquery.Client(project=project_id, credentials=credentials, location=location)
        else:
            # Uses GOOGLE_APPLICATION_CREDENTIALS or default credentials
            self.client = bigquery.Client(project=project_id, location=location)
        
        self.project_id = project_id or self.client.project
        self.location = location
    
    def _build_where_clause(self, filters: Dict[str, str], table: str = "events") -> str:
        """Build WHERE clause from filter dictionary."""
        conditions = []
        
        # Map filter keys to BigQuery column names (per table)
        if table == "events":
            column_map = {
                "actor": "Actor1Name",
                "country": "ActionGeo_CountryCode",
            }
        elif table == "mentions":
            column_map = {
                "actor": "MentionSourceName",
            }
        elif table == "gkg":
            column_map = {
                "theme": "Themes",
                "country": "Locations",
            }
        else:
            column_map = {}
        
        for key, value in filters.items():
            if not value:
                continue
            
            if key == "theme" and table == "gkg":
                # Multiple themes separated by commas - match any in Themes
                themes = [t.strip() for t in value.split(",")]
                theme_conditions = " OR ".join([f"Themes LIKE '%{t}%'" for t in themes])
                conditions.append(f"({theme_conditions})")
            elif key == "actor" and table == "events":
                # Match in either Actor1Name or Actor2Name
                actors = [a.strip() for a in value.split(",")]
                actor_conditions = []
                for a in actors:
                    actor_conditions.append(f"(Actor1Name LIKE '%{a}%' OR Actor2Name LIKE '%{a}%')")
                conditions.append(f"({' OR '.join(actor_conditions)})")
            elif key == "actor" and table == "mentions":
                actors = [a.strip() for a in value.split(",")]
                actor_conditions = " OR ".join([f"MentionSourceName LIKE '%{a}%'" for a in actors])
                conditions.append(f"({actor_conditions})")
            elif key == "country" and table == "events":
                countries = [c.strip() for c in value.split(",")]
                country_conditions = " OR ".join([f"ActionGeo_CountryCode = '{c}'" for c in countries])
                conditions.append(f"({country_conditions})")
            elif key == "country" and table == "gkg":
                countries = [c.strip() for c in value.split(",")]
                country_conditions = " OR ".join([f"V1Locations LIKE '%{c}%'" for c in countries])
                conditions.append(f"({country_conditions})")
            elif key == "sourcelang":
                # Not available in BigQuery events table
                logger.warning(f"'sourcelang' filter not supported in BigQuery {table} table, ignoring")
                continue
        
        return " AND ".join(conditions) if conditions else "1=1"
    
    def _build_date_filter(self, start_date: Optional[str], end_date: Optional[str], table: str = "events") -> str:
        """Build date filter for BigQuery."""
        conditions = []
        if table in ("events", "mentions"):
            # DATEADDED is integer YYYYMMDDHHMMSS
            if start_date:
                start_int = int(start_date.replace("-", "") + "000000")
                conditions.append(f"DATEADDED >= {start_int}")
            if end_date:
                end_int = int(end_date.replace("-", "") + "235959")
                conditions.append(f"DATEADDED <= {end_int}")
        elif table == "gkg":
            # GKG uses DATE field which is also integer YYYYMMDD
            if start_date:
                start_int = int(start_date.replace("-", ""))
                conditions.append(f"DATE >= {start_int}")
            if end_date:
                end_int = int(end_date.replace("-", ""))
                conditions.append(f"DATE <= {end_int}")
        return " AND ".join(conditions) if conditions else "1=1"
    
    def events_query(
        self,
        filters: Optional[Dict[str, str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_records: int = 1000,
        select_fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query GDELT Events table via BigQuery.
        
        Args:
            filters: Dict with theme, actor, country, sourcelang
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD
            max_records: Maximum records to return
            select_fields: Specific fields to select (default: key fields)
        
        Returns:
            List of event dictionaries
        """
        if select_fields is None:
            select_fields = [
                "GLOBALEVENTID", "DATEADDED", "Actor1Name", "Actor2Name",
                "Actor1CountryCode", "Actor2CountryCode", "ActionGeo_CountryCode",
                "ActionGeo_Lat", "ActionGeo_Long", "EventCode", "EventBaseCode",
                "EventRootCode", "QuadClass", "GoldsteinScale", "NumMentions",
                "NumSources", "NumArticles", "AvgTone", "SOURCEURL"
            ]
        
        where_clause = self._build_where_clause(filters or {}, "events")
        date_clause = self._build_date_filter(start_date, end_date, "events")
        
        query = f"""
        SELECT {', '.join(select_fields)}
        FROM `{self.TABLES['events']}`
        WHERE {where_clause} AND {date_clause}
        ORDER BY DATEADDED DESC
        LIMIT {max_records}
        """
        
        logger.info(f"Executing BigQuery Events query: {max_records} records max")
        query_job = self.client.query(query)
        results = query_job.result()
        
        return [dict(row) for row in results]
    
    def mentions_query(
        self,
        filters: Optional[Dict[str, str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_records: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Query GDELT Mentions table via BigQuery."""
        where_clause = self._build_where_clause(filters or {}, "mentions")
        date_clause = self._build_date_filter(start_date, end_date, "mentions")
        
        query = f"""
        SELECT GLOBALEVENTID, MentionTimeDate, MentionType, MentionSourceName,
               MentionIdentifier, MentionDocTone
        FROM `{self.TABLES['mentions']}`
        WHERE {where_clause} AND {date_clause}
        ORDER BY MentionTimeDate DESC
        LIMIT {max_records}
        """
        
        logger.info(f"Executing BigQuery Mentions query: {max_records} records max")
        query_job = self.client.query(query)
        results = query_job.result()
        
        return [dict(row) for row in results]
    
    def gkg_query(
        self,
        filters: Optional[Dict[str, str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_records: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Query GDELT GKG table via BigQuery."""
        # GKG uses different column names
        conditions = []
        if filters:
            if "theme" in filters:
                themes = [t.strip() for t in filters["theme"].split(",")]
                theme_conditions = " OR ".join([f"Themes LIKE '%{t}%'" for t in themes])
                conditions.append(f"({theme_conditions})")
            if "country" in filters:
                countries = [c.strip() for c in filters["country"].split(",")]
                country_conditions = " OR ".join([f"Locations LIKE '%{c}%'" for c in countries])
                conditions.append(f"({country_conditions})")
        
        date_conditions = []
        if start_date:
            date_conditions.append(f"DATE(GKGRECORDID) >= '{start_date}'")
        if end_date:
            date_conditions.append(f"DATE(GKGRECORDID) <= '{end_date}'")
        
        where_clause = " AND ".join(conditions + date_conditions) if (conditions or date_conditions) else "1=1"
        
        query = f"""
        SELECT GKGRECORDID, DATE, SourceCommonName, DocumentIdentifier,
               Themes, Locations, Persons, Organizations, V2Tone
        FROM `{self.TABLES['gkg']}`
        WHERE {where_clause}
        ORDER BY DATE DESC
        LIMIT {max_records}
        """
        
        logger.info(f"Executing BigQuery GKG query: {max_records} records max")
        query_job = self.client.query(query)
        results = query_job.result()
        
        return [dict(row) for row in results]
    
    def query_sa_filter(
        self,
        filter_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_records: int = 1000,
        table: str = "events",
    ) -> List[Dict[str, Any]]:
        """
        Query using pre-built SA filter via BigQuery.
        
        Args:
            filter_name: One of SA_FILTERS keys
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD
            max_records: Max records
            table: "events", "mentions", or "gkg"
        
        Returns:
            List of result dictionaries
        """
        if filter_name not in SA_FILTERS:
            raise GDELTValidationError(f"Unknown filter: {filter_name}. Available: {list(SA_FILTERS.keys())}")
        
        # BigQuery requires SA_FILTERS format (dict with theme/actor/country keys)
        filter_dict = SA_FILTERS[filter_name]
        
        if table == "events":
            return self.events_query(filter_dict, start_date, end_date, max_records)
        elif table == "mentions":
            return self.mentions_query(filter_dict, start_date, end_date, max_records)
        elif table == "gkg":
            return self.gkg_query(filter_dict, start_date, end_date, max_records)
        else:
            raise GDELTValidationError(f"Unknown table: {table}")
    
    def get_table_schema(self, table: str) -> List[bigquery.SchemaField]:
        """Get BigQuery table schema."""
        if table not in self.TABLES:
            raise GDELTValidationError(f"Unknown table: {table}")
        table_ref = self.client.get_table(self.TABLES[table])
        return table_ref.schema
    
    def estimate_query_cost(self, query: str) -> float:
        """Estimate query cost in TB processed."""
        job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
        query_job = self.client.query(query, job_config=job_config)
        return query_job.total_bytes_processed / (1024 ** 4)  # TB


# =============================================================================
# Cron Job Templates
# =============================================================================

def build_sa_politics_cron_job(
    schedule: str = "0 */6 * * *",
    filters: Optional[List[str]] = None,
    sync_neo4j: bool = True,
) -> Dict[str, Any]:
    """
    Build a Hermes cron job for continuous SA politics monitoring.
    
    Args:
        schedule: Cron schedule (default every 6 hours)
        filters: List of filter names to run (default: all SA filters)
        sync_neo4j: Whether to sync to Neo4j
    
    Returns:
        Cron job configuration dict
    """
    if filters is None:
        filters = list(SA_FILTERS.keys())
    
    filter_args = " ".join(f"--filter={f}" for f in filters)
    neo4j_flag = "--sync-neo4j" if sync_neo4j else ""
    
    return {
        "name": "gdelt-sa-politics-monitor",
        "schedule": schedule,
        "command": f"python -m scripts.gdelt_api {filter_args} {neo4j_flag}".strip(),
        "description": "Monitor SA political events via GDELT (Afrikaner genocide, RSA-USA diplomatic, visa sanctions, Iran/Russia alignment, BRICS wart countries)",
        "deliver": "origin",
    }


def build_daily_digest_cron_job(
    schedule: str = "0 7 * * *",
) -> Dict[str, Any]:
    """
    Build a cron job for daily tone shift digest.
    
    Runs at 7 AM daily, summarizes tone shifts for all SA filters.
    """
    return {
        "name": "gdelt-sa-daily-digest",
        "schedule": schedule,
        "command": "python -m scripts.gdelt_api --daily-digest",
        "description": "Daily digest of SA political event tone shifts from GDELT",
        "deliver": "origin",
    }


def build_escalation_alert_cron_job(
    schedule: str = "0 */3 * * *",
    threshold: float = -5.0,
) -> Dict[str, Any]:
    """
    Build a cron job for escalation alerts on sharp tone drops.
    
    Runs every 3 hours, alerts when AvgTone drops below threshold.
    """
    return {
        "name": "gdelt-sa-escalation-alert",
        "schedule": schedule,
        "command": f"python -m scripts.gdelt_api --escalation-alert --threshold={threshold}",
        "description": f"Alert on SA political event tone escalation (threshold: {threshold})",
        "deliver": "origin",
    }


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    """CLI entry point for cron jobs and manual testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="GDELT SA Politics Monitor")
    parser.add_argument("--filter", action="append", choices=list(SA_FILTERS.keys()) + ["witkruis_memorial"],
                        help="SA filter to run (can specify multiple)")
    parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    parser.add_argument("--max-records", type=int, default=250)
    parser.add_argument("--api", choices=["events", "mentions", "gkg", "ngrams", "bigquery"], default="events")
    parser.add_argument("--bq-project", help="GCP project ID for BigQuery")
    parser.add_argument("--bq-credentials", help="Path to GCP service account JSON key")
    parser.add_argument("--bq-table", choices=["events", "mentions", "gkg"], default="events", help="BigQuery table to query")
    parser.add_argument("--sync-neo4j", action="store_true", help="Sync to Neo4j")
    parser.add_argument("--daily-digest", action="store_true", help="Generate daily digest")
    parser.add_argument("--escalation-alert", action="store_true", help="Check for escalation")
    parser.add_argument("--threshold", type=float, default=-5.0, help="Escalation threshold")
    parser.add_argument("--output", choices=["json", "summary"], default="summary")
    
    args = parser.parse_args()
    
    # Initialize appropriate client based on API
    if args.api == "bigquery":
        if not BIGQUERY_AVAILABLE:
            print("ERROR: google-cloud-bigquery not installed. Run: pip install google-cloud-bigquery")
            return
        client = GDELTBigQueryClient(
            project_id=args.bq_project,
            credentials_path=args.bq_credentials,
        )
    else:
        client = GDELTClient()
    
    if args.daily_digest:
        # TODO: Implement daily digest
        print("Daily digest not yet implemented")
        return
    
    if args.escalation_alert:
        # TODO: Implement escalation alert
        print("Escalation alert not yet implemented")
        return
    
    filters = args.filter or list(SA_FILTERS.keys())
    
    all_events = []
    for filter_name in filters:
        print(f"Querying filter: {filter_name}...")
        if args.api == "bigquery":
            events = client.query_sa_filter(
                filter_name,
                start_date=args.start_date,
                end_date=args.end_date,
                max_records=args.max_records,
                table=args.bq_table,
            )
        else:
            events = client.query_sa_filter(
                filter_name,
                start_date=args.start_date,
                end_date=args.end_date,
                max_records=args.max_records,
                api=args.api,
            )
        print(f"  Found {len(events)} events")
        all_events.extend(events)
    
    if args.sync_neo4j:
        result = client.sync_events_to_neo4j(all_events)
        print(f"Neo4j sync result: {result}")
    
    if args.output == "json":
        # Handle both GDELTEvent objects (with __dict__) and dict results from NGrams
        if all_events and hasattr(all_events[0], '__dict__'):
            print(json.dumps([e.__dict__ for e in all_events], indent=2, default=str))
        else:
            print(json.dumps(all_events, indent=2, default=str))
    else:
        # Summary output - handle both object and dict types
        print(f"\nTotal events: {len(all_events)}")
        if all_events:
            # Check if we have GDELTEvent objects or dicts
            if hasattr(all_events[0], 'avg_tone'):
                # GDELTEvent objects
                tones = [e.avg_tone for e in all_events if e.avg_tone != 0]
                goldsteins = [e.goldstein_scale for e in all_events if e.goldstein_scale != 0]
                if tones:
                    print(f"Avg tone: {sum(tones)/len(tones):.2f} (min: {min(tones):.2f}, max: {max(tones):.2f})")
                if goldsteins:
                    print(f"Avg Goldstein: {sum(goldsteins)/len(goldsteins):.2f}")
                
                # Top actors
                actors = {}
                for e in all_events:
                    for actor_name in [e.actor1_name, e.actor2_name]:
                        if actor_name:
                            actors[actor_name] = actors.get(actor_name, 0) + 1
            else:
                # Dict results from NGrams
                # Show term matches
                terms_matched = {}
                for e in all_events:
                    term = e.get('term_matched', '')
                    if term:
                        terms_matched[term] = terms_matched.get(term, 0) + 1
                print("\nTop matched terms:")
                for term, count in sorted(terms_matched.items(), key=lambda x: -x[1])[:10]:
                    print(f"  {term}: {count}")
                
                # Show sample URLs
                print("\nSample articles:")
                for e in all_events[:5]:
                    title = e.get('title', 'N/A')[:80]
                    url = e.get('url', 'N/A')
                    print(f"  {title}")
                    print(f"    {url}")
                
                actors = {}  # Empty for NGrams
            
            print("\nTop actors:")
            for name, count in sorted(actors.items(), key=lambda x: -x[1])[:10]:
                print(f"  {name}: {count}")


if __name__ == "__main__":
    main()