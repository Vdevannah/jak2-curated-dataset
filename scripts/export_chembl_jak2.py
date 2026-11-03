"""
Export raw JAK2 (human) bioactivity records from ChEMBL to a CSV file.

Run this on your laptop (it needs internet access to the ChEMBL web services):

    python scripts/export_chembl_jak2.py

Downloads page by page from the ChEMBL REST API and retries automatically if the
server returns a temporary error (such as HTTP 500).

Output: data/raw/jak2_chembl_activities.csv  (the untouched "bronze" data)
"""
import time
from pathlib import Path

import pandas as pd
import requests

API = "https://www.ebi.ac.uk/chembl/api/data"
JAK2_UNIPROT = "O60674"  # Tyrosine-protein kinase JAK2, Homo sapiens
PAGE_SIZE = 500
MAX_RETRIES = 6
OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "jak2_chembl_activities.csv"

KEEP_COLUMNS = [
    "activity_id", "molecule_chembl_id", "canonical_smiles",
    "standard_type", "standard_relation", "standard_value", "standard_units",
    "pchembl_value", "assay_chembl_id", "assay_type", "assay_description",
    "target_chembl_id", "target_pref_name", "target_organism",
    "document_chembl_id", "data_validity_comment", "activity_comment",
]


def get_json(url, params):
    """GET a ChEMBL API page, retrying with increasing waits on server errors."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, params=params, timeout=120)
            if r.status_code == 200:
                return r.json()
            reason = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            reason = type(e).__name__
        wait = min(5 * 2 ** (attempt - 1), 120)
        print(f"  {reason} - retry {attempt}/{MAX_RETRIES} in {wait}s")
        time.sleep(wait)
    raise SystemExit(
        "ChEMBL kept returning errors. Their server may be down; please try again later."
    )


def find_target_id():
    """Look up the ChEMBL target ID for human JAK2 from its UniProt accession."""
    data = get_json(f"{API}/target.json", {
        "target_components__accession": JAK2_UNIPROT,
        "target_type": "SINGLE PROTEIN",
    })
    targets = data.get("targets", [])
    if not targets:
        raise SystemExit(f"No single-protein ChEMBL target found for UniProt {JAK2_UNIPROT}")
    t = targets[0]
    print(f"Target: {t['target_chembl_id']}  {t['pref_name']}  ({t['organism']})")
    return t["target_chembl_id"]


def main():
    target_id = find_target_id()
    rows, offset, total = [], 0, None
    print("Downloading activity records page by page...")
    while total is None or offset < total:
        page = get_json(f"{API}/activity.json", {
            "target_chembl_id": target_id, "limit": PAGE_SIZE, "offset": offset,
        })
        total = page["page_meta"]["total_count"]
        batch = page.get("activities", [])
        if not batch:
            break
        rows.extend(batch)
        offset += len(batch)
        print(f"  {offset:,} / {total:,} records")
        time.sleep(0.5)  # be polite to the public API

    df = pd.DataFrame(rows)
    df = df[[c for c in KEEP_COLUMNS if c in df.columns]]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"\nSaved {len(df):,} rows to {OUT}")
    print(df["standard_type"].value_counts().head(10).to_string())


if __name__ == "__main__":
    main()