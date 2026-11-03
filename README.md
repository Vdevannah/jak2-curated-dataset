# JAK2 Curated Dataset

Turning raw public JAK2 bioactivity data from ChEMBL into a clean, documented, model-ready dataset,
using medicinal chemistry judgment to decide which measurements are comparable.

## Why this project

Public bioactivity data cannot be used as downloaded. The same compound appears as different salt forms,
IC50, Ki and cell-assay results sit in the same table, units and conditions vary, some values are only
limits (">10 µM"), and replicate measurements disagree. Models and SAR conclusions built on raw data are
unreliable. This project shows how each of those issues is resolved, and records every decision.

## Pipeline

| Layer | Contents | Output |
|---|---|---|
| Bronze | Raw ChEMBL activity records, untouched | `data/raw/jak2_chembl_activities.csv` |
| Silver | Filtered, standardized measurements with pIC50 | `data/processed/jak2_silver_measurements.csv` |
| Gold | One row per compound: mean pIC50, spread, number of measurements | `data/processed/jak2_gold_compounds.csv` |
| Data-quality log | Rows removed by each rule, and why | `data/processed/jak2_dq_log.csv` |

Censored values (">", "<") are kept separately in `data/processed/jak2_censored_measurements.csv`.
The curation rules are explained in [`docs/curation_rules.md`](docs/curation_rules.md).

## How to run

```bash
pip install -r requirements.txt
python scripts/export_chembl_jak2.py        # downloads raw JAK2 data from ChEMBL (needs internet)
jupyter notebook notebooks/jak2_curation.ipynb   # run all cells
```

## Results

_Fill in after running:_ number of raw records, curated compounds, records removed per step
(see `data/processed/jak2_curation_summary.png`), and baseline model performance on unseen scaffolds.

## Tools

Python, pandas, RDKit (structure standardization, fingerprints, scaffolds), scikit-learn, Matplotlib, ChEMBL web services.

## Next steps

- Group IC50 values by ATP concentration (matters for ATP-competitive kinase inhibitors).
- Canonicalize tautomers.
- Move the pipeline to Databricks as bronze/silver/gold Delta tables, with the data-quality log as a table
  and model runs tracked in MLflow.

## Data source

ChEMBL, EMBL-EBI (https://www.ebi.ac.uk/chembl/), licensed CC BY-SA 3.0.
