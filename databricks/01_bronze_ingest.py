# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Bronze: ingest raw ChEMBL data
# MAGIC
# MAGIC Loads the raw CSV from the volume into a Delta table **exactly as it is**, adding only ingestion
# MAGIC metadata (source file and load time). The bronze table is never edited; every downstream table is
# MAGIC rebuilt from it, which makes the pipeline reproducible and traceable.

# COMMAND ----------

from pyspark.sql import functions as F

CATALOG = "workspace"
SCHEMA = "jak2"
SOURCE = f"/Volumes/{CATALOG}/{SCHEMA}/raw/jak2_chembl_activities.csv"
BRONZE = f"{CATALOG}.{SCHEMA}.bronze_activities"

# COMMAND ----------

bronze = (spark.read
          .option("header", True)
          .option("multiLine", True)   # assay descriptions can contain line breaks
          .option("quote", '"')
          .option("escape", '"')       # SMILES can contain backslashes, so only '"' is an escape character
          .option("inferSchema", True)
          .csv(SOURCE)
          .withColumn("_source_file", F.lit(SOURCE))
          .withColumn("_ingested_at", F.current_timestamp()))

(bronze.write.format("delta").mode("overwrite")
       .option("overwriteSchema", True).saveAsTable(BRONZE))

spark.sql(f"COMMENT ON TABLE {BRONZE} IS "
          "'Raw ChEMBL activity records for human JAK2 (CHEMBL2971), untouched. Source: ChEMBL, CC BY-SA 3.0.'")

print(f"{BRONZE}: {spark.table(BRONZE).count():,} rows")

# COMMAND ----------

display(spark.table(BRONZE).groupBy("standard_type").count().orderBy(F.desc("count")).limit(10))
