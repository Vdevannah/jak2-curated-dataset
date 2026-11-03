# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Silver: curate measurements
# MAGIC
# MAGIC Applies the nine curation rules (see `docs/curation_rules.md`) in PySpark, standardizes structures
# MAGIC with RDKit, converts IC50 to pIC50, and records how many rows each rule removed in a
# MAGIC **data-quality log table**.
# MAGIC
# MAGIC | Output table | Contents |
# MAGIC |---|---|
# MAGIC | `silver_measurements` | Curated, exact enzyme IC50 measurements with pIC50 |
# MAGIC | `censored_measurements` | Limit values (">", "<") set aside, not averaged |
# MAGIC | `dq_log` | Rows before and after each rule, with the reason |

# COMMAND ----------

# MAGIC %pip install rdkit

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

from pyspark.sql import functions as F
import pandas as pd

CATALOG = "workspace"
SCHEMA = "jak2"
T = lambda name: f"{CATALOG}.{SCHEMA}.{name}"

dq_log = []

def log_step(step, rule, before_df, after_df):
    """Record how many rows a curation rule removed, and why."""
    n_before, n_after = before_df.count(), after_df.count()
    dq_log.append((step, rule, n_before, n_after, n_before - n_after))
    print(f"{step:<26} {n_before:>7,} -> {n_after:>7,}  ({n_before - n_after:,} removed)")
    return after_df

# COMMAND ----------

# MAGIC %md
# MAGIC ## Curation rules

# COMMAND ----------

df = spark.table(T("bronze_activities")).cache()

df = log_step("1 IC50 only", "standard_type == IC50", df, df.filter(F.col("standard_type") == "IC50"))
df = log_step("2 Biochemical assays", "assay_type == B", df, df.filter(F.col("assay_type") == "B"))
df = log_step("3 Human target", "target_organism == Homo sapiens", df,
              df.filter(F.col("target_organism") == "Homo sapiens"))

mutant = F.coalesce(F.col("assay_description"), F.lit("")).rlike(r"\bmutant\b|\b[A-Z]\d{2,4}[A-Z]\b")
df = log_step("4 Wild-type enzyme", "no mutant/variant in assay description", df, df.filter(~mutant))

df = log_step("5 No validity warning", "data_validity_comment is empty", df,
              df.filter(F.col("data_validity_comment").isNull()))

df = df.withColumn("standard_value", F.col("standard_value").cast("double"))
df = log_step("6 Valid nM values", "units == nM and value > 0", df,
              df.filter((F.col("standard_units") == "nM") & (F.col("standard_value") > 0)))

# Censored values are set aside in their own table, not averaged with exact values
censored = df.filter(F.col("standard_relation").isin(">", "<", ">=", "<=", "'>'", "'<'"))
censored.write.format("delta").mode("overwrite").option("overwriteSchema", True).saveAsTable(T("censored_measurements"))
print(f"Set aside {censored.count():,} censored measurements")

df = log_step("7 Exact values only", "standard_relation is '='", df,
              df.filter(F.col("standard_relation").isin("=", "'='")))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Structure standardization with RDKit
# MAGIC
# MAGIC Each distinct SMILES is standardized once to its **neutral parent** (salts and solvents removed,
# MAGIC charges neutralized), and the result is joined back to the measurements. The parent InChIKey becomes
# MAGIC the compound identifier. There are about 10,000 distinct structures, so this runs on the driver;
# MAGIC for millions of structures the same function would run as a pandas UDF across the cluster.

# COMMAND ----------

from rdkit import Chem, RDLogger
from rdkit.Chem.MolStandardize import rdMolStandardize

RDLogger.DisableLog("rdApp.*")
chooser = rdMolStandardize.LargestFragmentChooser()
uncharger = rdMolStandardize.Uncharger()

def standardize(smiles):
    """Return (parent SMILES, parent InChIKey), or (None, None) if the structure cannot be parsed."""
    if not isinstance(smiles, str):
        return None, None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None, None
    mol = uncharger.uncharge(chooser.choose(rdMolStandardize.Cleanup(mol)))
    return Chem.MolToSmiles(mol), Chem.MolToInchiKey(mol)

distinct = df.select("canonical_smiles").distinct().toPandas()
distinct[["parent_smiles", "parent_inchikey"]] = pd.DataFrame(
    distinct["canonical_smiles"].apply(standardize).tolist(), index=distinct.index)
lookup = spark.createDataFrame(distinct.dropna(subset=["parent_inchikey"]))

df = log_step("8 Valid structures", "structure parses in RDKit", df,
              df.join(lookup, on="canonical_smiles", how="inner"))

n_salts = df.filter(F.col("canonical_smiles").contains(".")).count()
print(f"Records whose salt or solvent fragment was removed: {n_salts:,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## pIC50 and write the silver table
# MAGIC
# MAGIC pIC50 = 9 − log10(IC50 in nM). Values outside a plausible range (3–12) are removed.

# COMMAND ----------

df = df.withColumn("pIC50", 9 - F.log10("standard_value"))
df = log_step("9 Plausible potency", "3 <= pIC50 <= 12", df, df.filter(F.col("pIC50").between(3, 12)))

silver = df.select("activity_id", "molecule_chembl_id", "parent_inchikey", "parent_smiles", "canonical_smiles",
                   "standard_value", "pIC50", "assay_chembl_id", "assay_description", "document_chembl_id")
silver.write.format("delta").mode("overwrite").option("overwriteSchema", True).saveAsTable(T("silver_measurements"))

spark.sql(f"COMMENT ON TABLE {T('silver_measurements')} IS "
          "'Curated exact human JAK2 enzyme IC50 measurements with standardized parent structures and pIC50.'")

print(f"silver_measurements: {silver.count():,} rows, "
      f"{silver.select('parent_inchikey').distinct().count():,} compounds")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Data-quality log

# COMMAND ----------

dq = (spark.createDataFrame(dq_log, "step string, rule string, rows_before long, rows_after long, rows_removed long")
      .withColumn("run_at", F.current_timestamp()))
dq.write.format("delta").mode("overwrite").option("overwriteSchema", True).saveAsTable(T("dq_log"))
spark.sql(f"COMMENT ON TABLE {T('dq_log')} IS 'Rows removed by each curation rule in the latest pipeline run.'")
display(dq)
