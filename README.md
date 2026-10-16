# CSV & Excel Batch Cleaner

**Offline Python automation for merging CSV/XLSX exports, validating records, detecting duplicates, and showing results directly in the desktop app.** The GUI and CLI use the **same processing engine**.

> **Portfolio demonstration, not a client project.** Three publicly released U.S. government datasets (USGS, NOAA, Census) are tested with **deliberately injected, labeled synthetic errors**. No real client data or client results are claimed.

## The problem

Manually opening multiple spreadsheet exports, copying rows, checking missing fields, and removing duplicate records is slow and error-prone. This utility processes a folder of files and produces consistent reviewable outputs while preserving the original inputs.

## Features

| Feature | Status |
|---|---|
| Drag-and-drop CSV/XLSX files or folders | Supported |
| Auto-detect columns; choose duplicate/required/numeric fields without typing | Supported |
| Batch import CSV and .xlsx | Supported |
| Mixed CSV/XLSX input folder | Supported |
| First worksheet of each .xlsx | Supported |
| Unicode-aware, consistent header normalization | Supported |
| Required-field and numeric validation | Supported |
| Case-insensitive deduplication using an ID column | Supported |
| Source filename and original row tracking | Supported |
| Independently select clean / duplicate / rejected results as CSV and/or XLSX | Supported |
| In-app results dashboard after every run | Supported |
| Optional filename prefix on all selected outputs | Supported |
| Windows GUI and scriptable CLI | Supported |
| No cloud uploads or paid APIs | Supported |
| Original Excel styling, formulas, macros, pivot tables | **Not supported** |

**Dependencies:** `openpyxl` for Excel and `tkinterdnd2` for desktop drag-and-drop. No pandas, cloud account or external services.

## Reproducible portfolio tests

The same processing engine was tested against **three distinct data schemas** using official source snapshots and separate, deliberately corrupted fixtures.

| Case | Formats | Rows | Clean | Duplicates | Rejected |
|---|---|---:|---:|---:|---:|
| USGS earthquakes | 2 CSV + 1 XLSX | 195 | 180 | 6 | 9 |
| NOAA daily weather | 2 CSV | 166 | 154 | 4 | 8 |
| U.S. Census population | 1 XLSX | 221 | 208 | 4 | 9 |
| **Total** | **6 files** | **582** | **542** | **14** | **26** |

**41 automated regression tests passed.** Three separate malformed-input checks also verified that no partial output is published. These tests demonstrate controlled input/output behavior, **not performance on large datasets or real client projects**. Source records and synthetic anomalies are kept separate; details and reproduction commands are in [TEST_CASES.md](TEST_CASES.md).

![Desktop GUI](assets/gui-preview.png)

## Install and run

Requires **Python 3.10+**.

```bash
python -m pip install -r requirements.txt
```

On Windows, double-click `run_demo.bat` or run:

```bash
python gui.py
```

1. **Drop** one or more CSV/XLSX files or folders, or select an input folder using **Browse**.
2. Select the duplicate key and optional required/numeric checks from the detected columns.
3. Under **Output files**, choose only the CSV/XLSX categories you need.
4. Optionally enter a filename prefix, e.g. `October` → `October_cleaned.xlsx`.
5. Click **Run Data Cleanup**. The result counts, issue reasons and saved filenames appear **inside the app**, with a button to open the output folder.

The desktop app preloads the sample data and automatically detects column names shared by the selected files. **By default the GUI saves only `cleaned.xlsx`; all other exports are optional.** New input selections default to `id` (or the first shared column if `id` is absent), require that column, and leave numeric checks optional. **Always confirm the duplicate key and validation choices:** they depend on what each file represents. Only common columns can be selected because configured validation columns must exist in every file. Dropped folders are scanned one level deep, and duplicate file selections are ignored. The original input files stay untouched and offline. The CLI retains generic defaults: key `id`, required `id`, and no numeric validation.

### CLI

```bash
python cli.py --input data/input --output data/output --key id \
  --required id,time,latitude,longitude \
  --numeric latitude,longitude,depth,magnitude
```

Use `--exports` and `--prefix` to choose the exact CLI outputs:

```bash
python cli.py --input data/input --output data/output \
  --exports cleaned.xlsx,rejected.csv --prefix October
```

The CLI defaults to all six CSV/XLSX outputs; GUI export choices are independent.

For another business export, change the input/output directory and validation field names. **Every configured required or numeric column must exist in each source file.** Names are normalized consistently (for example, `Order ID` becomes `order_id`); the tool does not guess whether differently named columns have the same meaning.

### Prepare the mixed demo

```bash
python scripts/prepare_demo.py
```

The three standardized sample files (two CSV, one XLSX) and output are included. Regeneration is optional. A separate demo-only processing mode is not needed.

### Run all three cases

The additional NOAA and Census snapshots and fixtures are already included, so downloading data is **not required** to run these tests:

```bash
python scripts/run_test_cases.py
python -m unittest discover -s tests -v
```

To regenerate the optional test fixtures from the preserved snapshots, run `python scripts/prepare_extra_cases.py`. Separate results are placed in new folders each time.

## Outputs

Every run creates a **new subfolder** under the requested output folder, such as `data/output/run_20261016_120000_a1b2c3/`. Existing runs are never overwritten.

| Optional output | Purpose |
|---|---|
| `cleaned.csv` / `cleaned.xlsx` | Valid unique records |
| `duplicates.csv` / `duplicates.xlsx` | Extra records sharing the same ID |
| `rejected.csv` / `rejected.xlsx` | Invalid records with reasons and any overflow columns preserved |

Select individual combinations; nothing extra is exported. The in-app result summary appears automatically after processing. Prefixes are optional and support letters, numbers, underscores and hyphens (up to 40 characters).

The original input files are never modified. Results are written to a staging directory first and published as a complete run folder only after every output is created successfully.

## Scope and limitations

- The tool processes only `.csv` and `.xlsx`, not legacy `.xls` or macro-enabled `.xlsm`.
- For each XLSX file it reads the first worksheet. Formulas are **not calculated** and are rejected if present in input data. Data should be exported as values.
- Input Excel formatting, images, and embedded objects are not carried into cleaned output; the utility produces new flat tables.
- The per-file input limit is 20MB and the combined input limit is 100MB. Row results are stored in memory for final export, so very large projects may need a streaming/database approach.
- Duplicate detection uses a single user-selected normalized column; it is not fuzzy matching.
- Empty numeric cells are allowed unless the corresponding column is also marked required.
- A malformed CSV syntax error aborts processing without publishing a partial output folder. Rows with the wrong number of fields are sent to rejected outputs when they can be parsed.
- Header normalization is deterministic and Unicode-aware. Different semantic names are never implicitly merged.
- Excel cells with a simple leading-zero format (e.g. `000123`) are preserved as text. Very long numeric CSV values are exported as text to avoid Excel's ~15-digit precision limit; numbers *already rounded by Excel in the source file* cannot be recovered.
- Excel lock files and format-only trailing columns are ignored. Native Excel error cells are rejected.
- CSV and XLSX outputs protect text resembling spreadsheet formulas by escaping them.
- Output files are created locally; the app does not contact any remote service.

## Testing

```bash
python -m unittest discover -s tests -v
```

Tests cover CSV/XLSX input, identifiers and precision, signed numbers, Unicode headers, Excel lock/error/styled cells, invalid CSV syntax, overflow cells, output isolation and validation defaults.

## Repository structure

```text
cleaner.py            shared validation, deduplication and output reporting
spreadsheet_io.py     CSV and XLSX reading / XLSX writing
gui.py                Tkinter frontend
cli.py                command-line frontend
tests/                41 automated regression tests
scripts/              reproducible data preparation and test runner
data/source/          preserved original USGS feed snapshot
data/input/           2 CSV + 1 XLSX USGS examples
data/test_cases/      NOAA/Census source snapshots, fixtures, manifest and results
data/output/          generated runtime folders (ignored by Git)
data/example_output/  committed USGS sample outputs
assets/               real screenshots of the GUI and report
```

## License and sample data

**Code:** [MIT](LICENSE). **Sample data:** USGS, NOAA and the U.S. Census Bureau; demonstration errors were synthetically generated. This project is not affiliated with those agencies. See [DATA_SOURCES.md](DATA_SOURCES.md) and [TEST_CASES.md](TEST_CASES.md) for original source links and reuse details; the MIT license applies only to our code.
