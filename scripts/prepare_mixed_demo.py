"""Create a mixed-format counterpart of the original public USGS CSV demo.

Two CSV files are copied byte-for-byte; the third is converted to XLSX.
Data counts and deliberately synthetic errors stay unchanged.
"""
import csv
import shutil
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "input"
TARGET = ROOT / "data" / "mixed_input"


def main():
    TARGET.mkdir(parents=True, exist_ok=True)
    for idx in (1, 2):
        filename = f"usgs_batch_{idx:02d}.csv"
        shutil.copyfile(SOURCE / filename, TARGET / filename)
    with (SOURCE / "usgs_batch_03.csv").open(encoding="utf-8", newline="") as fp:
        reader = csv.reader(fp)
        book = Workbook(write_only=True)
        sheet = book.create_sheet("Events")
        for record in reader:
            sheet.append(record)
    book.save(TARGET / "usgs_batch_03.xlsx")
    print("Mixed demo ready: 2 CSV + 1 XLSX (195 rows including synthetic issues).")


if __name__ == "__main__":
    main()
