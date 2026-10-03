#!/usr/bin/env python3
"""Generate Hermes cron job configurations for GDELT SA monitoring."""

import json
from scripts.cron_templates import (
    create_all_sa_cron_jobs,
    create_individual_filter_jobs,
    print_cron_jobs
)

def main():
    print("=" * 60)
    print("Hermes Cron Job Generator for GDELT SA Politics")
    print("=" * 60)

    # Option 1: All-in-one monitoring (recommended for D7 offline)
    print("\n1. Complete SA Politics Monitoring Suite (sync_neo4j=False)")
    jobs = create_all_sa_cron_jobs(
        monitors_schedule="0 */6 * * *",    # Every 6 hours
        digest_schedule="0 7 * * *",        # Daily at 7 AM
        alert_schedule="0 */3 * * *",       # Every 3 hours
        alert_threshold=-5.0,               # Alert on sharp tone drops
        sync_neo4j=False                    # D7 is offline
    )
    print_cron_jobs(jobs)

    # Save to file for Hermes
    with open("hermes_cron_jobs.json", "w") as f:
        json.dump(jobs, f, indent=2)
    print("\n   Saved to hermes_cron_jobs.json")

    # Option 2: Individual filter jobs (granular control)
    print("\n" + "=" * 60)
    print("2. Individual Filter Jobs (for different schedules/delivery)")
    print("=" * 60)
    individual_jobs = create_individual_filter_jobs(
        schedule="0 */12 * * *",  # Every 12 hours
        sync_neo4j=False
    )
    print_cron_jobs(individual_jobs)

    with open("hermes_cron_jobs_individual.json", "w") as f:
        json.dump(individual_jobs, f, indent=2)
    print("\n   Saved to hermes_cron_jobs_individual.json")

    # Option 3: Production config (when D7 is online)
    print("\n" + "=" * 60)
    print("3. Production Config (D7 Online - Neo4j Sync Enabled)")
    print("=" * 60)
    prod_jobs = create_all_sa_cron_jobs(
        monitors_schedule="0 */6 * * *",
        digest_schedule="0 7 * * *",
        alert_schedule="0 */3 * * *",
        alert_threshold=-5.0,
        sync_neo4j=True  # Enable when D7 available
    )
    print_cron_jobs(prod_jobs)

    with open("hermes_cron_jobs_production.json", "w") as f:
        json.dump(prod_jobs, f, indent=2)
    print("\n   Saved to hermes_cron_jobs_production.json")

    # Usage instructions
    print("\n" + "=" * 60)
    print("USAGE INSTRUCTIONS")
    print("=" * 60)
    print("""
To create cron jobs in Hermes:

# For current offline D7 setup:
cat hermes_cron_jobs.json | while read job; do
    hermes cronjob create "$job"
done

# Or individually:
hermes cronjob create "$(cat hermes_cron_jobs.json | jq -c '.[0]')"
hermes cronjob create "$(cat hermes_cron_jobs.json | jq -c '.[1]')"
hermes cronjob create "$(cat hermes_cron_jobs.json | jq -c '.[2]')"

# When D7 comes online (after office renovations):
# 1. Update sync_neo4j=True in create_all_sa_cron_jobs()
# 2. Set NEO4J_URI, NEO4J_USER, NEO4J_PASS environment variables
# 3. Recreate cron jobs with production config

To list cron jobs:
    hermes cronjob list

To view logs:
    hermes cronjob logs gdelt-sa-politics-monitor

To delete:
    hermes cronjob delete gdelt-sa-politics-monitor
""")

if __name__ == "__main__":
    main()