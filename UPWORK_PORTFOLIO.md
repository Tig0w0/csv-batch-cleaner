# Upwork portfolio entry — draft, not submitted

**Title:** Python Excel & CSV Automation | Cleaning & Reporting

**Project description:**

Built an offline Python automation tool that merges multiple CSV and Excel (XLSX) files, standardizes column names, validates required and numeric fields, removes duplicate records, and generates reviewable reports.

The tool includes a Windows-friendly desktop GUI, a command-line interface, and a visual HTML data-quality dashboard. Each run safely writes a fresh folder of cleaned, duplicate, and rejected results in both CSV and XLSX formats.

For a reproducible demonstration, I used public-domain USGS earthquake data and intentionally inserted synthetic errors. The program processed 195 records, retained 180 clean observations, isolated 6 duplicates, and flagged 9 invalid records. Nineteen automated regression tests passed.

The workflow runs locally without paid APIs or uploads to external services. It is designed for clearly scoped spreadsheet cleanup projects and can be adapted to specific client file schemas.

**Skills:** Python, Excel, CSV, Data Cleaning, Data Validation, Data Processing, Automation, OpenPyXL

**My role:** Architecture, coding, GUI, dataset preparation, regression tests, documentation, reporting.

**Public repository:** https://github.com/Tig0w0/csv-batch-cleaner

**Suggested media:** `assets/gui-preview.png`, `assets/report-preview.png`, source and output example files.

**Disclosure:** This is a portfolio prototype, not an official USGS product. Deliberate quality issues are synthetic.
