# Databricks notebook source
# MAGIC %md
# MAGIC # 03 · Gold: one row per compound
# MAGIC
# MAGIC Aggregates replicate measurements of each parent compound on the pIC50 (log) scale. The number of
# MAGIC measurements, source documents and spread are kept, so users can judge reliability. Compounds whose
# MAGIC measurements disagree by more than 1 log unit (10-fold) are **flagged, not deleted**.
# MAGIC
# MAGIC Every column gets a description in Unity Catalog, so the table documents itself.

# COMMAND ----------

from pyspark.sql import functions as F

CATALOG = "workspace"
SCHEMA = "jak2"
T = lambda name: f"{CATALOG}.{SCHEMA}.{name}"
GOLD = T("gold_compounds")

# COMMAND ----------

silver = spark.table(T("silver_measurements"))

gold = (silver.groupBy("parent_inchikey")
        .agg(F.first("parent_smiles").alias("parent_smiles"),
             F.concat_ws(";", F.array_sort(F.collect_set("molecule_chembl_id"))).alias("chembl_ids"),
             F.round(F.mean("pIC50"), 2).alias("pIC50_mean"),
             F.round(F.coalesce(F.stddev("pIC50"), F.lit(0.0)), 2).alias("pIC50_std"),
             F.round(F.min("pIC50"), 2).alias("pIC50_min"),
             F.round(F.max("pIC50"), 2).alias("pIC50_max"),
             F.count("*").alias("n_measurements"),
             F.countDistinct("document_chembl_id").alias("n_documents"))
        .withColumn("flag_inconsistent", (F.col("pIC50_max") - F.col("pIC50_min")) > 1.0))

gold.write.format("delta").mode("overwrite").option("overwriteSchema", True).saveAsTable(GOLD)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Table and column descriptions (metadata)

# COMMAND ----------

spark.sql(f"COMMENT ON TABLE {GOLD} IS 'Curated human JAK2 potency, one row per standardized parent compound. "
          "Built from silver_measurements; model-ready.'")

column_docs = {
    "parent_inchikey": "InChIKey of the standardized neutral parent structure (compound identifier)",
    "parent_smiles": "Standardized parent structure (salts removed, charges neutralized)",
    "chembl_ids": "ChEMBL molecule IDs mapped to this parent (salt forms included)",
    "pIC50_mean": "Mean pIC50 across exact enzyme IC50 measurements (log scale)",
    "pIC50_std": "Standard deviation of pIC50 across measurements (0 if measured once)",
    "pIC50_min": "Lowest measured pIC50",
    "pIC50_max": "Highest measured pIC50",
    "n_measurements": "Number of curated IC50 measurements",
    "n_documents": "Number of distinct source publications or patents",
    "flag_inconsistent": "True if measurements differ by more than 1 log unit (10-fold)",
}
for col, doc in column_docs.items():
    spark.sql(f"ALTER TABLE {GOLD} ALTER COLUMN {col} COMMENT '{doc}'")

# COMMAND ----------

g = spark.table(GOLD)
print(f"gold_compounds: {g.count():,} compounds")
print(f"Measured more than once: {g.filter('n_measurements > 1').count():,}")
print(f"Flagged inconsistent: {g.filter('flag_inconsistent').count():,}")
display(g.orderBy(F.desc("pIC50_mean")).limit(20))
