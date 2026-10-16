# CSV Batch Cleaner

**Offline CSV automation that merges files, standardizes columns, detects duplicate records, validates data and exports an audit-friendly HTML report.** Built in Python with **zero third-party packages**.

![Processing report preview](assets/report-preview.png)

> **Portfolio project.** The included example uses an actual public-domain USGS dataset, plus *clearly labeled synthetic issues* to demonstrate validation. No confidential customer data, paid API, or external upload is required.

## Why this helps

Manually combining weekly CSV exports is repetitive and error-prone. CSV Batch Cleaner lets a client select an input folder, click **Run Data Cleanup**, and receive separated deliverables that make bad or repeated rows easy to inspect.

| Capability | Implemented |
|---|---|
| Merge all CSV files in a folder | Yes |
| Normalize inconsistent column names | Yes |
| Find duplicates using a chosen unique ID | Yes |
| Validate required fields | Yes |
| Detect invalid numeric values | Yes |
| Record originating filename and row | Yes |
| Export accepted, duplicate and rejected records separately | Yes |
| Generate shareable HTML report and JSON statistics | Yes |
| Windows desktop GUI and command-line use | Yes |
| Native Excel `.xlsx` import/export | **Not implemented** — use Excel's **CSV** export |

## Live-demo results

Using **180 real USGS earthquake observations** split into three CSVs, the preparation script also inserts **6 synthetic duplicates** and **9 synthetic invalid rows**. The resulting batch has **195 records**.

| Metric | Result |
|---|---:|
| Files merged | 3 |
| Rows scanned | 195 |
| Valid unique rows | 180 |
| Duplicates isolated | 6 |
| Invalid rows isolated | 9 |
| Automated unit tests | 6 passing |

### Screenshots

![Desktop application](assets/gui-preview.png)

![HTML audit report](assets/report-preview.png)

## Quick start — GUI (Windows, macOS, Linux)

1. Install **Python 3.10 or newer**. No `pip install` needed.
2. Download the repository.
3. Run `python gui.py` (or double-click `run_demo.bat` on Windows).
4. Choose input and output folders, then click **Run Data Cleanup**.
5. Open `report.html` in the output directory.

The included demo folders and validation fields are filled in by default.

## CLI example

```bash
python cli.py --input data/input --output data/output --key id \
  --required id,time,latitude,longitude \
  --numeric latitude,longitude,depth,magnitude
```

**Custom business CSVs:** Replace the demo input files with your own CSV exports, choose a unique column (e.g. `order_id`), and adjust required/numeric fields. Header names are normalized to snake_case; `Event ID`, `event_id` and `ID` all map to `id` in the demonstration. When files have incompatible schemas, the union of their columns is retained.

**Generated outputs:**
- `cleaned.csv`: accepted unique rows.
- `duplicates.csv`: extra copies, with a duplicate reason.
- `rejected.csv`: missing values, invalid numbers or malformed rows, with reasons.
- `summary.json`: counts, parameters and issue breakdown.
- `report.html`: ready-to-view local audit dashboard.

The HTML report links directly to the CSV/JSON files beside it. Source filename and source row are retained in every output.

## Verify the example

```bash
python scripts/prepare_demo.py
python -m unittest discover -s tests -v
python cli.py --input data/input --output data/output --key id --required id,time,latitude,longitude --numeric latitude,longitude,depth,magnitude
```

The source snapshot is committed in `data/source/` so the example can be reproduced even after the USGS live feed changes. The example intentionally modifies some rows: **do not use `data/input/` or `data/output/` as authoritative earthquake records**.

## How it works

```text
Source CSVs (different column names)
            |
            v
     Header normalization
            |
            v
   Required + numeric checks
          /   \
         v     v
     Rejected  Valid
                  |
                  v
          Deduplication by ID
             /       \
            v         v
       Duplicates   Cleaned
             \       /
              v     v
           JSON + HTML report
```

## Security, caveats and scope

- Entirely offline while processing; no telemetry or cloud storage.
- Inputs are CSV files of up to 20 MB **each**; larger batches should use a streaming implementation.
- The unique key must exist in every input CSV; otherwise the run stops with a clear error.
- The first valid record for each case-insensitive unique ID is kept. There is no complex reconciliation or fuzzy matching.
- The app does not modify input files. It writes five named output files; **rerunning into the same output directory replaces these generated outputs**.
- CSV formula-like text is escaped when exported to spreadsheet applications.
- For actual paid client work, confirm the column mapping, acceptance rules, data sensitivity and required deliverables before processing.

## Data provenance and rights

Example data: **U.S. Geological Survey (USGS) Earthquake Hazards Program**  
Download source: https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_month.csv  
USGS data use policy: https://www.usgs.gov/data-management/data-licensing

USGS-created government works are generally U.S. public domain, and USGS recommends CC0 for its fully USGS-produced datasets. See [DATA_SOURCES.md](DATA_SOURCES.md) for the exact snapshot details and licensing caveat. Credit: U.S. Geological Survey. Our source code is separately licensed under **MIT**; the included USGS data are not relicensed under MIT.

## Portfolio positioning

**Python CSV Data Automation | Cleaning, Deduplication & Reporting**

A small, clearly scoped, reproducible automation project demonstrating Python scripting, error handling, data validation, traceable outputs, unit testing and a usable desktop interface.

Created as a software portfolio demonstration, not as an official USGS product.
