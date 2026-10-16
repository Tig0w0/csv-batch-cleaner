"""Make a reproducible English demo dataset from a USGS public-domain snapshot.

The input rows are real observations; duplicates and invalid values added below
are intentionally synthetic, strictly for demonstrating quality checks.
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data/source/usgs_earthquakes_snapshot.csv"
OUT = ROOT / "data/input"
FIELDS = ("id", "time", "latitude", "longitude", "depth", "mag", "place", "status", "type")
HEADER_VARIANTS = [
    ("ID", "Time", "Latitude", "Longitude", "Depth", "Magnitude", "Place", "Status", "Type"),
    ("event_id", "time", "latitude_deg", "longitude_deg", "depth", "mag", "location", "status", "type"),
    ("id", "time", "latitude", "longitude", "depth", "magnitude", "place", "status", "type"),
]


def main():
    if not SNAPSHOT.exists():
        raise SystemExit("Download the USGS CSV snapshot first; see DATA_SOURCES.md.")
    with SNAPSHOT.open(encoding="utf-8-sig", newline="") as fp:
        incoming = list(csv.DictReader(fp))
    chosen, seen = [], set()
    for raw in incoming:
        if (not raw.get("id") or not raw.get("time") or not raw.get("latitude")
                or not raw.get("longitude") or raw["id"] in seen):
            continue
        seen.add(raw["id"])
        chosen.append({f: raw.get(f, "").strip() for f in FIELDS})
        if len(chosen) == 180:
            break
    if len(chosen) < 180:
        raise SystemExit("Snapshot has fewer than 180 usable unique records.")
    OUT.mkdir(parents=True, exist_ok=True)
    for batch in range(3):
        subset = [row.copy() for row in chosen[batch * 60:(batch + 1) * 60]]
        for x in range(2):
            subset.append(subset[x].copy())  # 6 clearly duplicated IDs
        for x in range(3):
            broken = subset[6 + x].copy()
            broken["id"] = f"synthetic-invalid-{batch}-{x}"
            if x == 0:
                broken["id"] = ""
            elif x == 1:
                broken["latitude"] = "not-a-number"
            elif x == 2:
                broken["time"] = ""
            subset.append(broken)
        path = OUT / f"usgs_batch_{batch + 1:02d}.csv"
        with path.open("w", newline="", encoding="utf-8") as fp:
            writer = csv.writer(fp)
            writer.writerow(HEADER_VARIANTS[batch])
            writer.writerows([[row.get(field, "") for field in FIELDS] for row in subset])
        print(f"{path.name}: {len(subset)} rows")
    print("180 authentic source records + 6 synthetic duplicates + 9 synthetic invalid rows.")


if __name__ == "__main__":
    main()
