# Three independent public-data test cases

Three **different schemas**, one unmodified CSV/XLSX cleaning engine. All test data are English-language records. The original government datasets are saved separately from the modified fixtures. **Synthetic errors are not claims about the original agency datasets.**

## Results (2026-10-16)

| Task | Input files | Scanned | Valid unique | Duplicates | Rejected |
|---|---:|---:|---:|---:|---:|
| 1. USGS earthquake events | 2 CSV + 1 XLSX | 195 | 180 | 6 | 9 |
| 2. NOAA NYC daily weather, Jan–May 2024 | 2 CSV | 166 | 154 | 4 | 8 |
| 3. Census state/territory population, 2021–2024 | **1 XLSX** | 221 | 208 | 4 | 9 |
| **Total** | **6** | **582** | **542** | **14** | **26** |

The weather sample contains 152 authentic source records plus **two labeled synthetic valid rows** to check an optional blank and safe spreadsheet-formula escaping. The Census fixture contains **208 authentic population estimates** (52 state-level geographies × four years). All other injected records are clearly labeled `synthetic_*`.

## Diverse injected problems

| Case | Source preserved | Deliberate anomalies | Processing rules |
|---|---|---|---|
| USGS | `data/source/usgs_earthquakes_snapshot.csv` | Repeated event IDs, blank IDs, invalid latitude, blank timestamp | Key: `id`; required: `id,time,latitude,longitude`; numeric: `latitude,longitude,depth,magnitude` |
| NOAA | `data/test_cases/noaa/original.csv` | Same-date duplicates (including conflicting values), missing date and station, nonnumeric/infinite readings, extra/missing CSV columns, blank optional reading, formula-looking note text | Key: `date`; required: `date,station`; numeric: `prcp,tmax,tmin` |
| Census | `data/test_cases/census/original.csv` | Duplicate records, blank record ID/state code/year/population, invalid year and population, Excel `#DIV/0!`, overflow cell; two-digit numeric state codes formatted as `00` | Key: `record_id`; required: `record_id,state_code,year,population`; numeric: `year,population` |

Issue totals may exceed rejected-row totals because a single row can violate several rules.

**Three additional failure-mode checks** use disposable inputs: an unterminated quoted CSV field, a missing configured numeric column, and an Excel formula. Each must abort without publishing partial results.

The program **does not** check domain-specific constraints such as plausible weather extremes, valid date calendars, population growth assumptions, or whether conflicting duplicate records should be merged. These require client-specific rules and are not represented as implemented.

## Running all three tests

From the project directory:

```powershell
python -m pip install -r requirements.txt
python scripts/prepare_extra_cases.py
python scripts/run_test_cases.py
python -m unittest discover -s tests -v
```

The preparation script downloads the agency snapshots only when they do not already exist; reruns are offline and deterministic using those frozen originals. The baseline USGS fixture stays in `data/input/`. New inputs are under `data/test_cases/noaa/input/` and `data/test_cases/census/input/`.

Each dataset is cleaned **separately**; incompatible schemas should not be mixed into one run. Results are saved to new, non-overwriting folders under `data/test_cases/<agency>/output/` (ignored by Git). Consolidated counts and issue breakdown: `data/test_cases/test_results.json`.

## Provenance and reuse

- **USGS**: Earthquake Hazards Program M2.5+ monthly CSV, saved snapshot; see [DATA_SOURCES.md](DATA_SOURCES.md).
- **NOAA / NCEI**: NYC Central Park-area observation station `USW00094728`, Daily Summaries (2024-01-01 to 2024-05-31). Original query: https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&stations=USW00094728&startDate=2024-01-01&endDate=2024-05-31&dataTypes=TMAX,TMIN,PRCP&units=metric&format=csv&includeAttributes=false . NOAA open-data policy: https://www.ncei.noaa.gov/sites/default/files/2023-12/NCEI%20PD-10-2-02%20-%20Open%20Data%20Policy%20Signed.pdf .
- **U.S. Census Bureau**: National and State Population Estimates, Vintage 2024, `NST-EST2024-ALLDATA.csv`. Original: https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/state/totals/NST-EST2024-ALLDATA.csv . Citation guidance: https://www.census.gov/about/policies/citation.html .

The original files are publicly released U.S. government statistical/environmental data. Agency attribution is retained, and this project does not imply government endorsement. Reuse rights depend on the original producer; this demo uses the agencies' own released datasets and no third-party imagery or private records. Source CSVs retain their original status; the project's MIT software license does not relicense those datasets.

**Do not use the altered test fixtures as authoritative weather, population, or earthquake observations.**
