# JAK2 Curated Dataset

**Turning 56,323 raw public bioactivity records into a clean, documented, model-ready dataset —
using medicinal chemistry judgment to decide which measurements can be trusted and compared.**

Python · RDKit · pandas · scikit-learn · Matplotlib · ChEMBL

---

## Why this matters

Public bioactivity data cannot be used as downloaded. For a single target like JAK2, ChEMBL mixes
IC50, Ki, binding-kinetics and percent-inhibition data; the same compound appears as different salt
forms; some values are only limits (">10 µM"); mutant-enzyme and cell-based results sit next to
wild-type enzyme assays; and replicate measurements disagree.

Models or SAR conclusions built on that raw data are unreliable. This project resolves each issue
with an explicit, documented rule and records how many records every rule removed.

## Pipeline

```mermaid
flowchart LR
    A["Bronze<br/>56,323 raw ChEMBL records"] --> B["Silver<br/>13,422 curated IC50 measurements"]
    B --> C["Gold<br/>9,596 curated compounds"]
    C --> D["SAR analysis<br/>and baseline model"]
    B -. every rule logged .-> E["Data-quality log"]
```

| Layer | Contents | Output |
|---|---|---|
| Bronze | Raw ChEMBL activity records, untouched | `data/raw/jak2_chembl_activities.csv` |
| Silver | Filtered, standardized measurements with pIC50 | `data/processed/jak2_silver_measurements.csv` |
| Gold | One row per compound: mean pIC50, spread, number of measurements | `data/processed/jak2_gold_compounds.csv` |
| Data-quality log | Rows removed by each rule, and why | `data/processed/jak2_dq_log.csv` |

---

## 1. What the raw data looks like

Only about a third of the raw JAK2 records are IC50 values. Most of the rest are binding-kinetics
(kon / k_off), Ki and single-point inhibition data, which measure different things and cannot be averaged together.

![Raw records by measurement type](figures/raw_endpoints.png)

## 2. Curation funnel

Each bar shows what remains after one rule. Only about **24%** of raw records survive as comparable,
exact enzyme IC50 values. The rules and the chemistry behind them are in
[`docs/curation_rules.md`](docs/curation_rules.md).

![Curation funnel](figures/curation_funnel.png)

| Rule | Records removed |
|---|---|
| Not IC50 (Ki, kinetics, % inhibition, …) | 37,022 |
| Cell-based (functional) assays | 611 |
| Mutant enzymes (e.g. V617F) | 228 |
| Flagged by ChEMBL as likely errors | 1,035 |
| Missing or non-nM units | 140 |
| Censored values (">", "<"), set aside separately | 3,837 |
| Unparsable structures | 28 |
| **Curated measurements** | **13,422** |

## 3. Structure standardization

The same compound is often registered as a salt. RDKit strips salts and solvents, neutralizes charges,
and maps every record to its neutral parent structure, so all measurements of one compound line up.
The third example is **ruxolitinib phosphate**, the approved JAK1/2 inhibitor, correctly mapped to its free base.

![Salt forms standardized to parent structures](figures/salt_standardization.png)

## 4. Replicate agreement

**2,361 compounds** were measured more than once. Replicates are averaged on the log (pIC50) scale.
Most agree within 0.5 log units (about 3-fold). **423 compounds** differ by more than 10-fold and are
**flagged rather than deleted**, so users can decide how to treat them.

The small cluster at almost exactly **3 log units (1,000-fold)** is the signature of unit errors, values
recorded in nM that were really µM or the reverse, which the flag catches.

![Spread between replicate measurements](figures/replicate_agreement.png)

## 5. The curated dataset

**9,596 curated compounds.** Potencies center around pIC50 7–7.5 (roughly 30–100 nM), typical for
published kinase inhibitor data, which favors compounds that worked.

![Curated potency distribution](figures/potency_distribution.png)

### Most common chemical series

The most frequent Bemis–Murcko scaffolds, with compound counts and mean potency.

![Most common scaffolds](figures/top_scaffolds.png)

### Most potent curated compounds

![Most potent compounds](figures/top_compounds.png)

All of these were measured once (n = 1), with IC50 values around 10–25 pM, and most belong to a single
chemical series. Values this potent can sit at the sensitivity limit of the assay (tight binding), so they
should be read with caution. This series also explains the small bump near pIC50 10.3 in the distribution above.

## 6. Is the dataset usable? A baseline model

A Random Forest on Morgan fingerprints, evaluated with a **scaffold split**: the test set contains only
chemical series the model never saw in training, a stricter and more realistic test than a random split.

| Model | RMSE | MAE | R² |
|---|---|---|---|
| Random Forest (Morgan fingerprints) | 0.69 | 0.50 | 0.68 |
| Mean-value baseline | 1.23 | — | — |

Trained on 7,097 compounds, tested on 2,076 compounds from unseen scaffolds (the 423 flagged compounds
were excluded). A typical error of 0.5 log units means predictions are usually within about 3-fold of the
measured IC50. As is typical for Random Forest, predictions are pulled toward the middle: weak compounds
are slightly over-predicted and the most potent slightly under-predicted.

![Predicted vs measured pIC50](figures/model_parity.png)

---

## How to run

```bash
conda create -n jak2 python=3.11 -y
conda activate jak2
pip install -r requirements.txt
python scripts/export_chembl_jak2.py              # downloads raw JAK2 data from ChEMBL
jupyter notebook notebooks/jak2_curation.ipynb    # run all cells; figures are saved to figures/
```

## Repository structure

```
jak2-curated-dataset/
├── scripts/export_chembl_jak2.py   # downloads raw ChEMBL data, with retries
├── notebooks/jak2_curation.ipynb   # bronze → silver → gold, data-quality log, figures, model
├── data/raw/                       # raw ChEMBL export (bronze)
├── data/processed/                 # curated datasets and data-quality log
├── figures/                        # figures used in this README
└── docs/curation_rules.md          # each curation rule and why
```

## Next steps

- Group IC50 values by ATP concentration (matters for ATP-competitive kinase inhibitors).
- Canonicalize tautomers.
- Move the pipeline to Databricks as bronze/silver/gold Delta tables, with the data-quality log as a
  table and model runs tracked in MLflow.

## Data source and license

Bioactivity data from [ChEMBL](https://www.ebi.ac.uk/chembl/) (EMBL-EBI).
Code is released under the MIT License. Curated data derived from ChEMBL is shared under CC BY-SA 3.0.
