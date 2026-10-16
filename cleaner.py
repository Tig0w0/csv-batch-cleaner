"""Local CSV/XLSX batch cleaning with traceable, safe output folders."""
from __future__ import annotations

import csv
import json
import math
import re
import secrets
import shutil
import tempfile
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from spreadsheet_io import read_header, read_records, write_xlsx

# These rules are shared by the CLI and GUI.
DEFAULT_KEY = "id"
DEFAULT_REQUIRED = "id"
DEFAULT_NUMERIC = ""
TRACE = ("__source_file", "__source_row")
RESERVED = (*TRACE, "__issue", "__extra_values")
MAX_BYTES = 20 * 1024 * 1024  # per input file
MAX_TOTAL_BYTES = 100 * 1024 * 1024
MAX_COLUMNS = 200
EXPORT_NAMES = frozenset(
    f"{name}.{suffix}" for name in ("cleaned", "duplicates", "rejected")
    for suffix in ("csv", "xlsx")
)


def export_filename(name: str, prefix: str = "") -> str:
    return f"{prefix}_{name}" if prefix else name



def normalize_header(value: str) -> str:
    return re.sub(r"[^\w]+", "_", value.strip().casefold()).strip("_")


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


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, str]],
               numeric: set[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            cells = {}
            for field in fields:
                value = str(row.get(field, ""))
                # A leading plus sign in a verified number is not a CSV formula.
                if field in numeric and value.startswith("+"):
                    try:
                        value = value[1:] if math.isfinite(float(value)) else value
                    except ValueError:
                        pass
                cells[field] = escape_csv_formula(value)
            writer.writerow(cells)


def process(input_dir: str | Path | list[str | Path], output_dir: str | Path,
            key: str = DEFAULT_KEY, required: str = DEFAULT_REQUIRED,
            numeric: str = DEFAULT_NUMERIC, *,
            exports: set[str] | None = None, prefix: str = "") -> Results:
    prefix = prefix.strip()
    if prefix and not re.fullmatch(r"[\w-]{1,40}", prefix):
        raise ValueError("Filename prefix must be 1–40 letters, numbers, _ or -.")
    exports = set(EXPORT_NAMES) if exports is None else set(exports)
    if not exports or not exports <= EXPORT_NAMES:
        raise ValueError("Select at least one supported output file.")
    target = Path(output_dir).resolve()
    sources = ([Path(input_dir)] if isinstance(input_dir, (str, Path))
               else [Path(p) for p in input_dir])
    sources = [p.resolve() for p in sources]
    if not sources or any(not p.exists() for p in sources):
        raise ValueError("Input files or folders do not exist.")
    folders = [p for p in sources if p.is_dir()]
    if any(target == p or p in target.parents or target in p.parents for p in folders):
        raise ValueError("Input and output folders must be separate, non-nested directories.")

    files = sorted({file for path in sources
                    for file in (path.iterdir() if path.is_dir() else [path])
                    if file.is_file() and file.suffix.lower() in (".csv", ".xlsx")
                    and not file.name.startswith("~$")}, key=lambda p: str(p).casefold())
    if not files:
        raise ValueError("No CSV/XLSX files found in the input directory.")
    total_bytes = 0
    key = normalize_header(key)
    if not key or key in RESERVED:
        raise ValueError("Invalid deduplication key.")
    required_cols = list(dict.fromkeys([key, *split_columns(required)]))
    numeric_cols = split_columns(numeric)
    for column in [*required_cols, *numeric_cols]:
        if column in RESERVED or not column:
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
        if len(fields) > MAX_COLUMNS or any(field in RESERVED for field in fields):
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
        for rowno, cells, reasons in read_records(file, len(headers)):
            processed += 1
            record = dict(zip(headers, cells[:len(headers)]))
            record["__source_file"] = file.name
            record["__source_row"] = str(rowno)
            if len(cells) > len(headers) and any(cells[len(headers):]):
                record["__extra_values"] = json.dumps(cells[len(headers):], ensure_ascii=False)
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
            ("rejected", rejected, [*fields, "__extra_values", "__issue"]),
        ):
            for suffix in ("csv", "xlsx"):
                name = f"{basename}.{suffix}"
                if name not in exports:
                    continue
                path = staging / export_filename(name, prefix)
                if suffix == "csv":
                    _write_csv(path, exported_fields, rows, set(numeric_cols))
                else:
                    write_xlsx(path, exported_fields, rows,
                               set(numeric_cols), escape_csv_formula)
        staging.rename(final)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return summary
