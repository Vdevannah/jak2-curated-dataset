# Databricks notebook source
# MAGIC %md
# MAGIC # 00 · Setup
# MAGIC
# MAGIC Creates the Unity Catalog objects used by the JAK2 pipeline:
# MAGIC
# MAGIC | Object | Name | Purpose |
# MAGIC |---|---|---|
# MAGIC | Schema | `workspace.jak2` | Holds all pipeline tables |
# MAGIC | Volume | `workspace.jak2.raw` | File storage for the raw ChEMBL CSV |
# MAGIC
# MAGIC **Run this once.** Then upload `jak2_chembl_activities.csv` (created by `scripts/export_chembl_jak2.py`)
# MAGIC into the volume: **Catalog → workspace → jak2 → Volumes → raw → Upload to this volume**.

# COMMAND ----------

CATALOG = "workspace"
SCHEMA = "jak2"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA} "
          "COMMENT 'JAK2 curated dataset pipeline: bronze, silver and gold tables'")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.raw "
          "COMMENT 'Raw ChEMBL exports (bronze source files)'")

print(f"Ready. Upload the raw CSV to /Volumes/{CATALOG}/{SCHEMA}/raw/")

# COMMAND ----------

# Check the upload (re-run after uploading the file)
display(dbutils.fs.ls(f"/Volumes/{CATALOG}/{SCHEMA}/raw/"))
