# Curation rules

Each rule is applied in this order. The number of rows removed by each rule is recorded in
`data/processed/jak2_dq_log.csv`.

| # | Rule | Reason |
|---|---|---|
| 1 | Keep `standard_type == IC50` | Ki, Kd, % inhibition and EC50 measure different quantities and cannot be averaged with IC50. |
| 2 | Keep `assay_type == B` (biochemical/binding) | Cell-based (functional) results include permeability, efflux and off-target effects, so they are a different endpoint. |
| 3 | Keep `target_organism == Homo sapiens` | Potency can differ between species. |
| 4 | Drop mutant/variant assays (e.g. V617F) | Mutant enzymes can bind inhibitors differently from wild type. Detected from the assay description. |
| 5 | Drop rows with a ChEMBL `data_validity_comment` | ChEMBL flags likely errors, such as values outside a typical range or transcription errors. |
| 6 | Keep values in nM that are greater than 0 | Required for a correct pIC50 conversion. |
| 7 | Set aside censored values (`>`, `<`, `>=`, `<=`) | A limit is not an exact value. These rows are saved separately, not averaged with exact values. |
| 8 | Standardize structures with RDKit and drop unparsable ones | Normalize functional groups, remove salts and solvents, neutralize charges. The parent InChIKey becomes the compound ID. |
| 9 | Keep pIC50 between 3 and 12 | Removes physically implausible values. |

## Aggregation (gold)

- Measurements are grouped by parent InChIKey and averaged on the pIC50 (log) scale.
- The number of measurements, number of source documents, standard deviation, minimum and maximum are kept.
- Compounds whose measurements differ by more than 1 log unit (10-fold) are flagged `flag_inconsistent`,
  not removed, so users can decide how to treat them.

## Known limitations

- IC50 for ATP-competitive inhibitors depends on ATP concentration; assays are not yet grouped by ATP level.
- Tautomers are not canonicalized.
- Mutant detection relies on the assay description text, so a few mutant assays may be missed.
