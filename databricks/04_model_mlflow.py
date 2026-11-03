# Databricks notebook source
# MAGIC %md
# MAGIC # 04 · Model: is the gold dataset usable?
# MAGIC
# MAGIC Trains a Random Forest on Morgan fingerprints with a **Bemis–Murcko scaffold split**, so the test set
# MAGIC contains only chemical series the model never saw. Parameters, metrics, the model, the parity plot,
# MAGIC and the gold table used for training are all recorded with **MLflow**, which links each model run
# MAGIC back to its data.

# COMMAND ----------

# MAGIC %pip install rdkit

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import numpy as np
import matplotlib.pyplot as plt
import mlflow
from rdkit import Chem, RDLogger
from rdkit.Chem import rdFingerprintGenerator
from rdkit.Chem.Scaffolds import MurckoScaffold
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

RDLogger.DisableLog("rdApp.*")
CATALOG = "workspace"
SCHEMA = "jak2"
GOLD = f"{CATALOG}.{SCHEMA}.gold_compounds"

PARAMS = {"n_estimators": 500, "fingerprint": "Morgan r=2, 2048 bits", "split": "Bemis-Murcko scaffold",
          "test_size": 0.2, "random_state": 42, "exclude_flag_inconsistent": True}

# COMMAND ----------

data = spark.table(GOLD).filter("NOT flag_inconsistent").toPandas()
mols = [Chem.MolFromSmiles(s) for s in data["parent_smiles"]]
fpgen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
X = np.array([fpgen.GetFingerprintAsNumPy(m) for m in mols])
y = data["pIC50_mean"].values
scaffolds = [MurckoScaffold.MurckoScaffoldSmiles(mol=m) for m in mols]

train_idx, test_idx = next(GroupShuffleSplit(test_size=PARAMS["test_size"], random_state=PARAMS["random_state"])
                           .split(X, y, groups=scaffolds))
print(f"Train: {len(train_idx):,} compounds | Test: {len(test_idx):,} compounds (unseen scaffolds)")

# COMMAND ----------

with mlflow.start_run(run_name="jak2_rf_scaffold_split") as run:
    mlflow.log_params(PARAMS)
    try:  # record which table version trained this model (lineage)
        mlflow.log_input(mlflow.data.load_delta(table_name=GOLD), context="training")
    except Exception as e:
        print(f"Dataset logging skipped: {e}")

    model = RandomForestRegressor(n_estimators=PARAMS["n_estimators"], n_jobs=-1,
                                  random_state=PARAMS["random_state"]).fit(X[train_idx], y[train_idx])
    pred = model.predict(X[test_idx])

    metrics = {
        "test_rmse": mean_squared_error(y[test_idx], pred) ** 0.5,
        "test_mae": mean_absolute_error(y[test_idx], pred),
        "test_r2": r2_score(y[test_idx], pred),
        "baseline_rmse": mean_squared_error(y[test_idx], np.full(len(test_idx), y[train_idx].mean())) ** 0.5,
        "n_train": len(train_idx),
        "n_test": len(test_idx),
    }
    mlflow.log_metrics(metrics)

    fig, ax = plt.subplots(figsize=(5.2, 5))
    ax.scatter(y[test_idx], pred, s=8, alpha=0.4, color="#2F5496")
    lims = [min(y.min(), pred.min()) - 0.3, max(y.max(), pred.max()) + 0.3]
    ax.plot(lims, lims, color="#9AA0A6", linestyle="--", linewidth=1)
    ax.set_xlim(lims); ax.set_ylim(lims)
    ax.set_xlabel("measured pIC50"); ax.set_ylabel("predicted pIC50")
    ax.set_title("Random Forest, scaffold split")
    ax.text(0.04, 0.95, f"RMSE {metrics['test_rmse']:.2f}\nMAE {metrics['test_mae']:.2f}\nR² {metrics['test_r2']:.2f}",
            transform=ax.transAxes, va="top", fontsize=9)
    mlflow.log_figure(fig, "model_parity.png")
    plt.show()

    mlflow.sklearn.log_model(model, name="model", input_example=X[:5])

print({k: round(v, 2) if isinstance(v, float) else v for k, v in metrics.items()})
print(f"MLflow run: {run.info.run_id}")
