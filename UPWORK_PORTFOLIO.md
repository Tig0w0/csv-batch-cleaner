# Upwork portfolio entry — draft, not submitted

**Title:** Python Excel & CSV Automation | Cleaning & Reporting

**Project description:**

Built an offline Python automation tool that merges multiple CSV and Excel (XLSX) files, standardizes column names, validates required and numeric fields, removes duplicate records, and generates reviewable reports.

The tool includes a Windows-friendly desktop GUI with drag-and-drop input and column selection without manual typing, a command-line interface, and an in-app data-quality results dashboard. Each run safely writes a fresh output folder. Users can independently choose CSV/XLSX formats for clean, duplicate and rejected records, add a filename prefix, and review the outcome directly in the desktop app. JSON summary export is optional.

For a reproducible demonstration, I tested three public U.S. government datasets (USGS, NOAA, Census) with clearly labeled synthetic errors: 582 records, 542 clean, 14 duplicates, and 26 rejected. Forty-one automated regression tests passed.

The workflow runs locally without paid APIs or uploads to external services. It is designed for clearly scoped spreadsheet cleanup projects and can be adapted to specific client file schemas.

**Skills:** Python, Excel, CSV, Data Cleaning, Data Validation, Data Processing, Automation, OpenPyXL

**My role:** Architecture, coding, GUI, dataset preparation, regression tests, documentation, reporting.

**Public repository:** https://github.com/Tig0w0/csv-batch-cleaner

**Suggested media:** `assets/gui-preview.png`, source and output example files.

**Disclosure:** This is a portfolio prototype, not an official USGS product. Deliberate quality issues are synthetic.
