"""
GDELT 2.0 API Skill for Hermes.

Provides Events, Mentions, and GKG API access with SA politics filter templates.
"""

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from gdelt_api import (
    GDELTClient,
    GDELTBigQueryClient,
    GDELTEvent,
    GDELTMention,
    GDELTGKGRecord,
    GDELTError,
    GDELTAPIError,
    GDELTRateLimitError,
    GDELTValidationError,
    GDELTAPIUnavailableError,
    EventQueryBuilder,
    MentionQueryBuilder,
    GKGQueryBuilder,
    SA_FILTERS,
    SA_NGRAM_SEARCH_TERMS,
    FILTER_AFRIKANER_GENOCIDE,
    FILTER_RSA_USA_DIPLOMATIC,
    FILTER_USA_VISA_SANCTIONS,
    FILTER_RSA_IRAN_RUSSIA_ALIGNMENT,
    FILTER_BRICS_WART_COUNTRIES,
    build_sa_politics_cron_job,
    build_daily_digest_cron_job,
    build_escalation_alert_cron_job,
)

from cron_templates import (
    create_all_sa_cron_jobs,
    create_individual_filter_jobs,
    print_cron_jobs,
)

__all__ = [
    # Clients
    "GDELTClient",
    "GDELTBigQueryClient",
    # Data classes
    "GDELTEvent",
    "GDELTMention",
    "GDELTGKGRecord",
    # Exceptions
    "GDELTError",
    "GDELTAPIError",
    "GDELTRateLimitError",
    "GDELTValidationError",
    "GDELTAPIUnavailableError",
    # Query builders
    "EventQueryBuilder",
    "MentionQueryBuilder",
    "GKGQueryBuilder",
    # SA filter templates
    "SA_FILTERS",
    "SA_NGRAM_SEARCH_TERMS",
    "FILTER_AFRIKANER_GENOCIDE",
    "FILTER_RSA_USA_DIPLOMATIC",
    "FILTER_USA_VISA_SANCTIONS",
    "FILTER_RSA_IRAN_RUSSIA_ALIGNMENT",
    "FILTER_BRICS_WART_COUNTRIES",
    # Cron job builders
    "build_sa_politics_cron_job",
    "build_daily_digest_cron_job",
    "build_escalation_alert_cron_job",
    # Cron template helpers
    "create_all_sa_cron_jobs",
    "create_individual_filter_jobs",
    "print_cron_jobs",
]

__version__ = "0.1.0"