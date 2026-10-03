#!/usr/bin/env python3
"""Check table schema and try daily windows."""

import os
from google.cloud import bigquery

PROJECT = "gen-lang-client-0418790586"
client = bigquery.Client(project=PROJECT)

# Check table schema and partitioning
print("📋 Checking events table schema...")
table = client.get_table("gdelt-bq.gdeltv2.events")
print(f"Table: {table.table_id}")
print(f"Partitioning: {table.time_partitioning}")
print(f"Clustering: {table.clustering_fields}")
print(f"Num rows: {table.num_rows}")
print(f"Size: {table.num_bytes / 1e12:.2f} TB")
print(f"\nSchema fields:")
for field in table.schema[:20]:
    print(f"  {field.name}: {field.field_type} ({field.mode})")

# Check GKG table
print("\n📋 Checking GKG table schema...")
table2 = client.get_table("gdelt-bq.gdeltv2.gkg")
print(f"Table: {table2.table_id}")
print(f"Partitioning: {table2.time_partitioning}")
print(f"Clustering: {table2.clustering_fields}")
print(f"Num rows: {table2.num_rows}")
print(f"Size: {table2.num_bytes / 1e12:.2f} TB")

# Check GKG partitioned table
print("\n📋 Checking GKG partitioned table schema...")
table3 = client.get_table("gdelt-bq.gdeltv2.gkg_partitioned")
print(f"Table: {table3.table_id}")
print(f"Partitioning: {table3.time_partitioning}")
print(f"Clustering: {table3.clustering_fields}")
print(f"Num rows: {table3.num_rows}")
print(f"Size: {table3.num_bytes / 1e12:.2f} TB")