"""
Export raw JAK2 (human) bioactivity records from ChEMBL to a CSV file.

Run this on your laptop (it needs internet access to the ChEMBL web services):

    pip install chembl_webresource_client pandas
    python scripts/export_chembl_jak2.py

Output: data/raw/jak2_chembl_activities.csv  (the untouched "bronze" data)
"""
from pathlib import Path

import pandas as pd
from chembl_webresource_client.new_client import new_client

JAK2_UNIPROT = "O60674"  # Tyrosine-protein kinase JAK2, Homo sapiens
OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "jak2_chembl_activities.csv"

FIELDS = [
    "activity_id", "molecule_chembl_id", "canonical_smiles",
    "standard_type", "standard_relation", "standard_value", "standard_units",
    "pchembl_value", "assay_chembl_id", "assay_type", "assay_description",
    "target_chembl_id", "target_pref_name", "target_organism",
    "document_chembl_id", "data_validity_comment", "activity_comment",
]


def find_target_id() -> str:
    """Look up the ChEMBL target ID for human JAK2 from its UniProt accession."""
    hits = new_client.target.filter(
        target_components__accession=JAK2_UNIPROT, target_type="SINGLE PROTEIN"
    ).only(["target_chembl_id", "pref_name", "organism"])
    hits = list(hits)
    if not hits:
        raise SystemExit(f"No single-protein ChEMBL target found for UniProt {JAK2_UNIPROT}")
    t = hits[0]
    print(f"Target: {t['target_chembl_id']}  {t['pref_name']}  ({t['organism']})")
    return t["target_chembl_id"]


def main() -> None:
    target_id = find_target_id()
    print("Downloading activity records (this can take a few minutes)...")
    acts = new_client.activity.filter(target_chembl_id=target_id).only(FIELDS)
    df = pd.DataFrame(list(acts))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"Saved {len(df):,} rows to {OUT}")
    print(df["standard_type"].value_counts().head(10).to_string())


if __name__ == "__main__":
    main()
