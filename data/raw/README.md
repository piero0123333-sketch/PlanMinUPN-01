# Cerro Azul — EXP03

Dataset ID: `DS01`  
Audience role: `student_project`  
Included campaigns: C01, C02, C03

## Contents

- `collar.csv` — Drillhole collar location, orientation and final depth.
- `survey.csv` — Downhole orientation measurements.
- `lithology.csv` — Observed downhole lithology intervals.
- `alteration.csv` — Observed alteration intervals when available.
- `assay.csv` — Observed downhole assay intervals.
- `density.csv` — Observed sparse density samples.
- `data_dictionary.csv` — Safe field definitions, units and data types.
- `release_manifest.json` — Safe file inventory, counts and integrity hashes.

## Coordinates and units

Coordinates use the source/local Cartesian coordinate system. Coordinate and
downhole distance units are metres. Assay and density units are documented in
`data_dictionary.csv`.

## Scientific scope

These are synthetic educational data. They do not represent a mineral resource
or mineral reserve statement. The release contains exploration observations only.

## Alteration availability

Alteration observations are not available in this dataset version; `alteration.csv` therefore contains its valid header and zero records.

