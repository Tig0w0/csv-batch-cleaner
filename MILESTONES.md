# Development Milestones — CSV & Excel Batch Cleaner

Milestones M1–M4 were implemented on `feature/safe-xlsx-processing`. New data-integrity changes (M5–M7) are on local branch `fix/data-integrity-compact`.
**Publishing the code to GitHub and editing Upwork must wait for owner review.**

## M1 — Data correctness and safe output

[GitHub milestone 1](https://github.com/Tig0w0/csv-batch-cleaner/milestone/1) · [issue #1](https://github.com/Tig0w0/csv-batch-cleaner/issues/1)

- [x] Reject files missing configured required/numeric columns before writing any results.
- [x] Strictly reject malformed CSV quoting.
- [x] Share safe, generic validation defaults between GUI and CLI.
- [x] Stage complete outputs and atomically publish each run as a *new directory*.
- [x] Preserve existing output folders and original inputs.

## M2 — Lean processing core

[GitHub milestone 2](https://github.com/Tig0w0/csv-batch-cleaner/milestone/2) · [issue #2](https://github.com/Tig0w0/csv-batch-cleaner/issues/2)

- [x] Remove redundant `incoming` and `malformed` parallel arrays.
- [x] Process file records directly into accepted/duplicate/rejected collections.
- [x] Preserve source filename and actual starting physical line numbers for multiline CSV records.
- [x] Keep GUI and CLI thin wrappers around a single cleaning engine.

## M3 — XLSX support

[GitHub milestone 3](https://github.com/Tig0w0/csv-batch-cleaner/milestone/3) · [issue #3](https://github.com/Tig0w0/csv-batch-cleaner/issues/3)

- [x] Read the first worksheet of `.xlsx` files using `openpyxl`.
- [x] Support mixed `.csv` and `.xlsx` folders.
- [x] Export all three result categories in both CSV and XLSX formats.
- [x] Reject XLSX formula input rather than pretending to calculate formulas.
- [x] Escape formula-like exported text and keep valid numeric output cells numeric.

## M4 — Regression tests and portfolio documentation

[GitHub milestone 4](https://github.com/Tig0w0/csv-batch-cleaner/milestone/4) · [issue #4](https://github.com/Tig0w0/csv-batch-cleaner/issues/4)

- [x] 30 automated tests pass (malformed/absent columns, saved files, Excel input/output, etc.).
- [x] Real Windows GUI smoke test passes.
- [x] Actual mixed data sample: 3 inputs, 195 rows → 180 cleaned, 6 duplicate, 9 rejected.
- [x] Screenshots captured from the running application and actual HTML report.
- [x] English README, source attribution, MIT source-code license and Upwork text prepared.
- [ ] Owner review and approval for GitHub branch publication.
- [ ] Publish approved code and close milestone issues.
- [ ] Owner approval for Upwork portfolio submission.

## Commands for reviewer

```powershell
cd C:\automation\csv-cleaner-portfolio
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python gui.py
```

For a reproducible batch run:

```powershell
python cli.py --input data/mixed_input --output data/output --key id --required id,time,latitude,longitude --numeric latitude,longitude,depth,magnitude --usgs-demo
```

## M5 — Lossless field handling

[Milestone 5](https://github.com/Tig0w0/csv-batch-cleaner/milestone/5) · [issue #5](https://github.com/Tig0w0/csv-batch-cleaner/issues/5)

- [x] Preserve Excel's simple zero-padded IDs and large numeric values from CSV exports.
- [x] Consistent leading-plus numeric CSV/XLSX output.
- [x] Preserve extra cells from rejected malformed CSV and XLSX rows.
- [x] Retain Unicode column names and make USGS-specific aliases opt-in.

## M6 — Practical Excel resilience

[Milestone 6](https://github.com/Tig0w0/csv-batch-cleaner/milestone/6) · [issue #6](https://github.com/Tig0w0/csv-batch-cleaner/issues/6)

- [x] Ignore Excel `~$` lock files and formatting-only trailing columns.
- [x] Reject Excel error cells with traceable reasons.
- [x] Keep the same first-sheet-only and no-formula-calculation boundaries.

## M7 — Compact regression and review

[Milestone 7](https://github.com/Tig0w0/csv-batch-cleaner/milestone/7) · [issue #7](https://github.com/Tig0w0/csv-batch-cleaner/issues/7)

- [x] 30 automated regression tests passed.
- [x] Actual 3-file mixed USGS demo remains 195 → 180 clean / 6 duplicate / 9 rejected.
- [x] Kept one cleaner and one small CSV/XLSX adapter; no extra frameworks.
- [ ] Owner review of the local-only changes before remote code publication.
