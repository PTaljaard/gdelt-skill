#!/usr/bin/env python3
"""
Cron job templates for GDELT SA politics monitoring.
Generates Hermes cronjob JSON configurations.
"""

import json
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any

# Ensure we can import gdelt_api whether run as module or script
_SCRIPTS_DIR = Path(__file__).parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from gdelt_api import (
    SA_FILTERS,
    build_sa_politics_cron_job,
    build_daily_digest_cron_job,
    build_escalation_alert_cron_job,
)


def create_all_sa_cron_jobs(
    monitors_schedule: str = "0 */6 * * *",
    digest_schedule: str = "0 7 * * *",
    alert_schedule: str = "0 */3 * * *",
    alert_threshold: float = -5.0,
    sync_neo4j: bool = False,  # False while D7 is offline
) -> List[Dict[str, Any]]:
    """
    Create all three cron jobs for comprehensive SA politics monitoring.
    
    Returns:
        List of cron job configs ready for Hermes cronjob create
    """
    jobs = []
    
    # 1. Continuous monitor (every 6 hours)
    jobs.append(build_sa_politics_cron_job(
        schedule=monitors_schedule,
        filters=list(SA_FILTERS.keys()),
        sync_neo4j=sync_neo4j,
    ))
    
    # 2. Daily digest (7 AM)
    jobs.append(build_daily_digest_cron_job(schedule=digest_schedule))
    
    # 3. Escalation alerts (every 3 hours)
    jobs.append(build_escalation_alert_cron_job(
        schedule=alert_schedule,
        threshold=alert_threshold,
    ))
    
    return jobs


def create_individual_filter_jobs(
    schedule: str = "0 */6 * * *",
    sync_neo4j: bool = False,
) -> List[Dict[str, Any]]:
    """
    Create separate cron jobs for each SA filter (granular monitoring).
    
    Useful if you want different schedules or delivery targets per filter.
    """
    jobs = []
    for filter_name in SA_FILTERS.keys():
        from .gdelt_api import build_sa_politics_cron_job
        job = build_sa_politics_cron_job(
            schedule=schedule,
            filters=[filter_name],
            sync_neo4j=sync_neo4j,
        )
        job["name"] = f"gdelt-sa-{filter_name.replace('_', '-')}"
        jobs.append(job)
    return jobs


def print_cron_jobs(jobs: List[Dict[str, Any]], pretty: bool = True) -> None:
    """Print cron jobs as JSON."""
    if pretty:
        print(json.dumps(jobs, indent=2))
    else:
        print(json.dumps(jobs))


# Example usage for Hermes cronjob create:
#
# python -c "
# from scripts.cron_templates import create_all_sa_cron_jobs
# jobs = create_all_sa_cron_jobs(sync_neo4j=False)
# for job in jobs:
#     import json
#     print(json.dumps(job))
# " | while read job; do
#     hermes cronjob create "$job"
# done