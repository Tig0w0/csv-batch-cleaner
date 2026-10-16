"""Local CSV/XLSX batch cleaning with traceable, safe output folders."""
from __future__ import annotations

import csv
import html
import json
import math
import re
import secrets
import shutil
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from spreadsheet_io import read_header, read_records, write_xlsx

# These rules are shared by the CLI and GUI.
DEFAULT_KEY = "id"
DEFAULT_REQUIRED = "id"
DEFAULT_NUMERIC = ""
DEMO_REQUIRED = "id,time,latitude,longitude"
DEMO_NUMERIC = "latitude,longitude,depth,magnitude"

# Explicit demonstration aliases. Other datasets can supply matching headers.
ALIASES = {
    "event_id": "id",
    "eventid": "id",
    "latitude_deg": "latitude",
    "longitude_deg": "longitude",
    "mag": "magnitude",
    "mag_value": "magnitude",
    "mag_type": "magnitude_type",
    "location": "place",
}
TRACE = ("__source_file", "__source_row")
MAX_BYTES = 20 * 1024 * 1024  # per input file
MAX_TOTAL_BYTES = 100 * 1024 * 1024
MAX_COLUMNS = 200


def normalize_header(value: str) -> str:
    name = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    return ALIASES.get(name, name)


def split_columns(value: str) -> list[str]:
    return list(dict.fromkeys(normalize_header(x) for x in value.split(",") if x.strip()))


def escape_csv_formula(value: str) -> str:
    """Keep untrusted cell text from becoming spreadsheet formulas."""
    if value and value.lstrip().startswith(("=", "+", "@", "\t", "\r")):
        return "'" + value
    if value and value.lstrip().startswith("-"):
        try:
            float(value)
        except ValueError:
            return "'" + value
    return value


@dataclass
class Results:
    input_files: int
    processed_rows: int
    clean_rows: int
    duplicate_rows: int
    rejected_rows: int
    columns: list[str]
    required: list[str]
    numeric: list[str]
    dedupe_key: str
    issues: dict[str, int]
    created_utc: str
    output_directory: str


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: escape_csv_formula(str(row.get(field, ""))) for field in fields})


def process(input_dir: str | Path, output_dir: str | Path,
            key: str = DEFAULT_KEY, required: str = DEFAULT_REQUIRED,
            numeric: str = DEFAULT_NUMERIC) -> Results:
    source, target = Path(input_dir).resolve(), Path(output_dir).resolve()
    if not source.is_dir():
        raise ValueError("Input directory does not exist.")
    if target == source or source in target.parents or target in source.parents:
        raise ValueError("Input and output folders must be separate, non-nested directories.")

    files = sorted(p for p in source.iterdir() if p.is_file()
                   and p.suffix.lower() in (".csv", ".xlsx"))
    if not files:
        raise ValueError("No CSV/XLSX files found in the input directory.")
    total_bytes = 0
    key = normalize_header(key)
    if not key or key in TRACE:
        raise ValueError("Invalid deduplication key.")
    required_cols = list(dict.fromkeys([key, *split_columns(required)]))
    numeric_cols = split_columns(numeric)
    for column in [*required_cols, *numeric_cols]:
        if column in TRACE or not column:
            raise ValueError("Invalid validation column.")

    normalized_headers: dict[Path, list[str]] = {}
    all_columns: list[str] = []
    known_columns: set[str] = set()
    checked_cols = set(required_cols + numeric_cols)
    # Inspect every source first; no output is touched when schemas are invalid.
    for file in files:
        size = file.stat().st_size
        total_bytes += size
        if size > MAX_BYTES or total_bytes > MAX_TOTAL_BYTES:
            raise ValueError("Input too large (20 MB/file, 100 MB total).")
        fields = [normalize_header(value) for value in read_header(file)]
        if not fields or not all(fields) or len(fields) != len(set(fields)):
            raise ValueError(f"{file.name}: empty or duplicate header names.")
        if len(fields) > MAX_COLUMNS or any(field in TRACE or field == "__issue" for field in fields):
            raise ValueError(f"{file.name}: too many or reserved column names.")
        missing = checked_cols - set(fields)
        if missing:
            raise ValueError(f"{file.name}: configured columns missing: {', '.join(sorted(missing))}")
        normalized_headers[file] = fields
        for name in fields:
            if name not in known_columns:
                known_columns.add(name)
                all_columns.append(name)

    kept: list[dict[str, str]] = []
    duplicates: list[dict[str, str]] = []
    rejected: list[dict[str, str]] = []
    issues: Counter[str] = Counter()
    seen: set[str] = set()
    processed = 0
    for file in files:
        headers = normalized_headers[file]
        for rowno, cells, malformed in read_records(file, len(headers)):
            processed += 1
            record = dict(zip(headers, cells))
            record["__source_file"] = file.name
            record["__source_row"] = str(rowno)
            reasons: list[str] = ["malformed_csv_row"] if malformed else []
            for column in required_cols:
                if not record.get(column, ""):
                    reasons.append(f"missing_{column}")
            for column in numeric_cols:
                value = record.get(column, "")
                if value:
                    try:
                        if not math.isfinite(float(value)):
                            raise ValueError("nonfinite")
                    except ValueError:
                        reasons.append(f"invalid_number_{column}")
            if reasons:
                issues.update(reasons)
                rejected.append({**record, "__issue": "; ".join(reasons)})
                continue
            identity = record[key].casefold()
            if identity in seen:
                issues[f"duplicate_{key}"] += 1
                duplicates.append({**record, "__issue": f"duplicate_{key}"})
                continue
            seen.add(identity)
            kept.append(record)

    fields = [*all_columns, *TRACE]
    timestamp = datetime.now(timezone.utc)
    final = target / f"run_{timestamp:%Y%m%d_%H%M%S}_{secrets.token_hex(3)}"
    summary = Results(
        input_files=len(files), processed_rows=processed,
        clean_rows=len(kept), duplicate_rows=len(duplicates), rejected_rows=len(rejected),
        columns=all_columns, required=required_cols, numeric=numeric_cols,
        dedupe_key=key, issues=dict(sorted(issues.items())),
        created_utc=timestamp.isoformat(timespec="seconds"),
        output_directory=str(final),
    )

    # All files are written to a staging directory before one final directory rename.
    # Existing output directories and prior runs are never overwritten.
    target.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".working_", dir=target))
    try:
        for basename, rows, exported_fields in (
            ("cleaned", kept, fields),
            ("duplicates", duplicates, [*fields, "__issue"]),
            ("rejected", rejected, [*fields, "__issue"]),
        ):
            _write_csv(staging / f"{basename}.csv", exported_fields, rows)
            write_xlsx(staging / f"{basename}.xlsx", exported_fields, rows,
                       set(numeric_cols), escape_csv_formula)
        (staging / "summary.json").write_text(
            json.dumps(asdict(summary), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8"
        )
        (staging / "report.html").write_text(build_report(summary, files), encoding="utf-8")
        staging.rename(final)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return summary


def build_report(s: Results, files: list[Path]) -> str:
    esc = html.escape
    pct = round(s.clean_rows * 100 / s.processed_rows, 1) if s.processed_rows else 0
    issue_rows = "".join(
        f"<tr><td>{esc(name.replace('_', ' ').capitalize())}</td><td>{count:,}</td></tr>"
        for name, count in s.issues.items()
    ) or '<tr><td colspan="2">No issues detected</td></tr>'
    input_rows = "".join(
        f"<tr><td>{esc(p.name)}</td><td>{p.stat().st_size:,} bytes</td></tr>"
        for p in files
    )
    chips = "".join(f'<span class="chip">{esc(field)}</span>' for field in s.columns[:16])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CSV & Excel Cleaner | Processing Report</title>
<style>
:root{{--ink:#142439;--muted:#63758a;--line:#e3eaf0;--bg:#f4f7fb;--accent:#047d89;--success:#188674;--warn:#e09a39;--danger:#d85d68}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);font:15px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;color:var(--ink)}}
main{{max-width:1080px;margin:0 auto;padding:48px 24px 70px}}
header{{background:#13283b;color:#fff;padding:42px;border-radius:20px;display:flex;justify-content:space-between;gap:16px;align-items:end}}
.overline{{color:#7ddee3;letter-spacing:.14em;font-weight:800;font-size:12px}}h1{{font-size:34px;margin:10px 0 8px;line-height:1.15}}header p{{margin:0;color:#bad0dc}}
.stamp{{font-size:12px;color:#a8c2d2;text-align:right}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:22px 0}}
.kpi{{background:#fff;border:1px solid var(--line);border-radius:15px;padding:22px}}.kpi small{{display:block;color:var(--muted);font-weight:700}}
.kpi strong{{font-size:32px;font-weight:750;display:block;margin-top:10px;letter-spacing:-1px}}
.kpi:nth-child(2) strong{{color:var(--success)}}.kpi:nth-child(3) strong{{color:var(--warn)}}.kpi:nth-child(4) strong{{color:var(--danger)}}
.panel{{border:1px solid var(--line);background:white;border-radius:16px;padding:26px;margin-top:18px}}
h2{{margin:0 0 16px;font-size:19px}}.progress{{height:14px;border-radius:40px;background:#e3eaf0;overflow:hidden;display:flex}}
.good{{background:var(--success)}}.dupe{{background:var(--warn)}}.bad{{background:var(--danger)}}
.legend{{display:flex;gap:24px;flex-wrap:wrap;margin:14px 0 0;color:var(--muted);font-size:13px}}
.dot{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}}.columns{{display:flex;gap:7px;flex-wrap:wrap}}
.chip{{padding:5px 10px;background:#edf4f7;color:#426074;border-radius:7px;font:12px Consolas,monospace}}
table{{width:100%;border-collapse:collapse}}td{{border-bottom:1px solid var(--line);padding:12px 6px}}td:last-child{{text-align:right;font-weight:700}}
.downloads{{display:flex;flex-wrap:wrap;gap:10px}}.downloads a{{text-decoration:none;color:#006673;border:1px solid #b8d8da;background:#eef9f9;border-radius:9px;padding:10px 15px;font-weight:700;font-size:13px}}
footer{{color:var(--muted);font-size:12px;margin:22px 4px}}@media(max-width:700px){{.grid{{grid-template-columns:repeat(2,1fr)}}header{{display:block}}.stamp{{text-align:left;margin-top:14px}}h1{{font-size:28px}}}}
</style></head>
<body><main><header><div><div class="overline">DATA QUALITY / AUTOMATION</div><h1>CSV & Excel Processing Report</h1><p>Batch merging · data validation · duplicate detection</p></div>
<div class="stamp">CREATED IN UTC<br>{esc(s.created_utc)}</div></header>
<div class="grid">
<div class="kpi"><small>Processed rows</small><strong>{s.processed_rows:,}</strong></div>
<div class="kpi"><small>Clean rows</small><strong>{s.clean_rows:,}</strong></div>
<div class="kpi"><small>Duplicates</small><strong>{s.duplicate_rows:,}</strong></div>
<div class="kpi"><small>Rejected rows</small><strong>{s.rejected_rows:,}</strong></div></div>
<section class="panel"><h2>Data quality overview · {pct}% accepted</h2>
<div class="progress"><span class="good" style="width:{s.clean_rows * 100 / max(s.processed_rows, 1):.3f}%"></span>
<span class="dupe" style="width:{s.duplicate_rows * 100 / max(s.processed_rows, 1):.3f}%"></span>
<span class="bad" style="width:{s.rejected_rows * 100 / max(s.processed_rows, 1):.3f}%"></span></div>
<div class="legend"><span><i class="dot" style="background:var(--success)"></i>Accepted</span><span><i class="dot" style="background:var(--warn)"></i>Duplicates</span><span><i class="dot" style="background:var(--danger)"></i>Rejected</span></div></section>
<section class="panel"><h2>Detected issues</h2><table>{issue_rows}</table></section>
<section class="panel"><h2>Source files · {s.input_files}</h2><table>{input_rows}</table></section>
<section class="panel"><h2>Normalized column names</h2><div class="columns">{chips}</div></section>
<section class="panel"><h2>Exported deliverables</h2><div class="downloads">
<a href="cleaned.csv">Cleaned CSV ↗</a><a href="cleaned.xlsx">Cleaned Excel ↗</a>
<a href="duplicates.csv">Duplicates CSV ↗</a><a href="duplicates.xlsx">Duplicates Excel ↗</a>
<a href="rejected.csv">Rejected CSV ↗</a><a href="rejected.xlsx">Rejected Excel ↗</a>
<a href="summary.json">JSON summary ↗</a></div></section>
<footer>Created by CSV Batch Cleaner · Local processing only · No data is sent to external services.</footer>
</main></body></html>"""
