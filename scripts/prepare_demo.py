"""Build a mixed CSV/XLSX demo from a preserved USGS public-domain snapshot.

180 authentic records plus 6 synthetic duplicates and 9 synthetic invalid rows.
"""
import csv
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data/source/usgs_earthquakes_snapshot.csv"
OUT = ROOT / "data/input"
FIELDS = ("id", "time", "latitude", "longitude", "depth", "mag", "place", "status", "type")
HEADERS = ("id", "time", "latitude", "longitude", "depth", "magnitude", "place", "status", "type")


def main():
    with SNAPSHOT.open(encoding="utf-8-sig", newline="") as handle:
        chosen, seen = [], set()
        for row in csv.DictReader(handle):
            if not all(row.get(name) for name in ("id", "time", "latitude", "longitude")):
                continue
            if row["id"] in seen:
                continue
            seen.add(row["id"])
            chosen.append([row.get(name, "").strip() for name in FIELDS])
            if len(chosen) == 180:
                break
    if len(chosen) != 180:
        raise ValueError("USGS snapshot needs at least 180 complete unique records.")

    OUT.mkdir(parents=True, exist_ok=True)
    for batch in range(3):
        rows = [item.copy() for item in chosen[batch * 60:(batch + 1) * 60]]
        rows.extend(item.copy() for item in rows[:2])  # 6 synthetic duplicates total
        for issue in range(3):
            broken = rows[6 + issue].copy()
            broken[0] = f"synthetic-invalid-{batch}-{issue}"
            if issue == 0:
                broken[0] = ""
            elif issue == 1:
                broken[2] = "not-a-number"
            else:
                broken[1] = ""
            rows.append(broken)
        if batch < 2:
            path = OUT / f"usgs_batch_{batch + 1:02d}.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(HEADERS)
                writer.writerows(rows)
        else:
            path = OUT / "usgs_batch_03.xlsx"
            book = Workbook(write_only=True)
            sheet = book.create_sheet("Events")
            sheet.append(HEADERS)
            for row in rows:
                sheet.append(row)
            book.save(path)
        print(f"{path.name}: {len(rows)} rows")
    print("195 rows: 180 source records + 6 synthetic duplicates + 9 synthetic errors.")


if __name__ == "__main__":
    main()
