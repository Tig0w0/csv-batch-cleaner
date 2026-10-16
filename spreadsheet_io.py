"""Small format adapters. All cleaning policy stays in cleaner.py."""
from __future__ import annotations

import csv
import math
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterator
from zipfile import BadZipFile


def _openpyxl():
    try:
        from openpyxl import Workbook, load_workbook
    except ImportError as exc:
        raise RuntimeError("XLSX support requires: python -m pip install -r requirements.txt") from exc
    return Workbook, load_workbook


def read_header(path: Path) -> list[str]:
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            try:
                return list(next(csv.reader(handle, strict=True), []) or [])
            except csv.Error as exc:
                raise ValueError(f"{path.name}: invalid CSV header: {exc}") from exc
    _, load_workbook = _openpyxl()
    try:
        wb = load_workbook(path, read_only=True, data_only=False)
        try:
            values = list(next(wb.worksheets[0].iter_rows(values_only=True), []) or [])
            while values and (values[-1] is None or not str(values[-1]).strip()):
                values.pop()  # Ignore trailing columns expanded by Excel formatting.
            return [str(value).strip() if value is not None else "" for value in values]
        finally:
            wb.close()
    except (OSError, ValueError, IndexError, BadZipFile) as exc:
        raise ValueError(f"{path.name}: cannot read XLSX header: {exc}") from exc


def _cell_text(cell) -> str:
    value = cell.value
    if value is None:
        return ""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    # Preserve simple leading-zero ID formats (e.g. Excel 000123 displayed from 123).
    fmt = cell.number_format
    if (isinstance(value, (int, float)) and not isinstance(value, bool)
            and re.fullmatch(r"0{2,}", fmt or "")
            and math.isfinite(value) and float(value).is_integer()):
        return f"{int(value):0{len(fmt)}d}"
    return str(value).strip()


def read_records(path: Path, header_length: int) -> Iterator[tuple[int, list[str], list[str]]]:
    """Yield (physical row number, all cell values, detected row errors)."""
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle, strict=True)
            try:
                next(reader)
                previous_end = reader.line_num
                while True:
                    first_line = previous_end + 1
                    try:
                        cells = next(reader)
                    except StopIteration:
                        break
                    previous_end = reader.line_num
                    errors = ["malformed_csv_row"] if len(cells) != header_length else []
                    yield first_line, [value.strip() for value in cells], errors
            except csv.Error as exc:
                raise ValueError(f"{path.name}: malformed CSV near line {reader.line_num}: {exc}") from exc
        return

    _, load_workbook = _openpyxl()
    try:
        wb = load_workbook(path, read_only=True, data_only=False)
        try:
            rows = wb.worksheets[0].iter_rows(values_only=False)
            next(rows, None)
            for number, cells in enumerate(rows, 2):
                if all(cell.value is None for cell in cells):
                    continue
                if any(cell.data_type == "f" for cell in cells):
                    raise ValueError(
                        f"{path.name}: Excel formulas are not supported (row {number}); "
                        "export calculated values to a plain worksheet first."
                    )
                values = [_cell_text(cell) for cell in cells]
                errors = []
                if any(cell.data_type == "e" for cell in cells):
                    errors.append("excel_error_cell")
                if any(values[header_length:]):
                    errors.append("malformed_excel_row")
                yield number, values, errors
        finally:
            wb.close()
    except (OSError, IndexError, BadZipFile) as exc:
        raise ValueError(f"{path.name}: cannot read XLSX rows: {exc}") from exc


def write_xlsx(path: Path, fields: list[str], rows: list[dict[str, str]],
               numeric_columns: set[str], safe_text) -> None:
    Workbook, _ = _openpyxl()
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet("Results")
    sheet.append(fields)
    for row in rows:
        values = []
        for field in fields:
            value = str(row.get(field, ""))
            if value and field in numeric_columns:
                try:
                    decimal = Decimal(value)
                    number = float(value)
                    if (decimal.is_finite() and math.isfinite(number)
                            and len(decimal.normalize().as_tuple().digits) <= 15):
                        values.append(number)
                        continue
                except (ValueError, InvalidOperation, OverflowError):
                    pass
            values.append(safe_text(value))
        sheet.append(values)
    workbook.save(path)
