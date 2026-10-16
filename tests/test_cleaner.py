import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cleaner import DEFAULT_KEY, DEFAULT_REQUIRED, DEFAULT_NUMERIC, normalize_header, process


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerows(rows)


def output_file(results, name):
    return Path(results.output_directory) / name


class CleaningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.src = self.root / "input"
        self.src.mkdir()
        self.out = self.root / "output"

    def test_multiple_files_merge_duplicates_invalid(self):
        write_csv(self.src / "a.csv", [
            ["ID", "Time", "Latitude", "Magnitude"],
            ["EQ1", "2026-10-01", "35.1", "3.1"],
            ["EQ2", "2026-10-02", "12.0", "2.8"],
        ])
        write_csv(self.src / "b.csv", [
            ["id", "time", "latitude", "Magnitude"],
            ["EQ1", "2026-10-01", "35.1", "3.1"],
            ["EQ3", "2026-10-03", "invalid", "3.8"],
            ["", "2026-10-04", "20.1", "4.2"],
            ["EQ4", "2026-10-05", "55.0", "5.0"],
        ])
        result = process(self.src, self.out, "id", "id,time,latitude", "latitude,magnitude")
        self.assertEqual((result.processed_rows, result.clean_rows,
                          result.duplicate_rows, result.rejected_rows), (6, 3, 1, 2))
        self.assertEqual(result.issues["duplicate_id"], 1)
        self.assertEqual(result.issues["invalid_number_latitude"], 1)
        self.assertEqual(result.issues["missing_id"], 1)
        self.assertTrue(output_file(result, "cleaned.xlsx").exists())
        with output_file(result, "cleaned.csv").open(encoding="utf-8-sig", newline="") as fp:
            rows = list(csv.DictReader(fp))
        self.assertEqual({r["id"] for r in rows}, {"EQ1", "EQ2", "EQ4"})
        self.assertEqual(rows[0]["magnitude"], "3.1")

    def test_missing_key_fails_without_outputs(self):
        write_csv(self.src / "one.csv", [["item", "name"], ["a", "Alice"]])
        with self.assertRaisesRegex(ValueError, "missing"):
            process(self.src, self.out)
        self.assertFalse(self.out.exists())

    def test_missing_configured_numeric_column_fails(self):
        write_csv(self.src / "one.csv", [["id", "amount"], ["1", "not a number"]])
        with self.assertRaisesRegex(ValueError, "price"):
            process(self.src, self.out, numeric="price")
        self.assertFalse(self.out.exists())

    def test_missing_configured_column_in_one_file_fails(self):
        write_csv(self.src / "a.csv", [["id", "price"], ["1", "10"]])
        write_csv(self.src / "b.csv", [["id", "name"], ["2", "Bob"]])
        with self.assertRaisesRegex(ValueError, "b.csv"):
            process(self.src, self.out, numeric="price")

    def test_protect_against_overlapping_paths(self):
        write_csv(self.src / "a.csv", [["id"], ["1"]])
        with self.assertRaisesRegex(ValueError, "separate"):
            process(self.src, self.src / "output")

    def test_formula_sanitization_csv(self):
        write_csv(self.src / "a.csv", [["id", "name"], ["1", '=HYPERLINK("test")']])
        result = process(self.src, self.out)
        with output_file(result, "cleaned.csv").open(encoding="utf-8-sig", newline="") as fp:
            record = next(csv.DictReader(fp))
        self.assertTrue(record["name"].startswith("'="))

    def test_formula_sanitization_xlsx_output(self):
        from openpyxl import load_workbook
        write_csv(self.src / "a.csv", [["id", "name", "price"], ["1", "=HYPERLINK(1)", "12.5"]])
        result = process(self.src, self.out, numeric="price")
        wb = load_workbook(output_file(result, "cleaned.xlsx"), read_only=True)
        try:
            row = list(wb.active.values)[1]
        finally:
            wb.close()
        self.assertEqual(row[1], "'=HYPERLINK(1)")
        self.assertEqual(row[2], 12.5)

    def test_normalize_header(self):
        self.assertEqual(normalize_header(" Latitude Deg "), "latitude_deg")
        self.assertEqual(normalize_header("Event ID"), "event_id")

    def test_duplicate_headers_not_silent(self):
        write_csv(self.src / "a.csv", [["ID", "id"], ["one", "two"]])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            process(self.src, self.out)

    def test_strict_unclosed_csv_quote(self):
        (self.src / "broken.csv").write_text('id,description\nONE,"hello\nTWO,world\n', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "malformed CSV"):
            process(self.src, self.out)
        self.assertFalse(self.out.exists())

    def test_multiline_physical_row_tracking(self):
        write_csv(self.src / "multiline.csv", [["id", "note"], ["one", "one\ntwo"], ["two", "done"]])
        result = process(self.src, self.out)
        with output_file(result, "cleaned.csv").open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual([r["__source_row"] for r in rows], ["2", "4"])

    def test_mixed_csv_and_xlsx_input(self):
        from openpyxl import Workbook, load_workbook
        write_csv(self.src / "a.csv", [["ID", "Time", "Latitude"], ["A", "2026", "15.5"]])
        wb = Workbook()
        ws = wb.active
        ws.append(["id", "time", "latitude"])
        ws.append(["B", "2026", 32.4])
        ws.append(["A", "2026", 15.5])
        wb.save(self.src / "b.xlsx")
        result = process(self.src, self.out, numeric="latitude")
        self.assertEqual((result.input_files, result.clean_rows, result.duplicate_rows), (2, 2, 1))
        workbook = load_workbook(output_file(result, "cleaned.xlsx"), read_only=True)
        try:
            values = list(workbook.active.values)
        finally:
            workbook.close()
        self.assertEqual(len(values), 3)
        self.assertEqual(values[1][2], 15.5)

    def test_excel_formulas_are_not_silently_accepted(self):
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.append(["id", "price"])
        ws.append(["A", "=1+2"])
        wb.save(self.src / "formula.xlsx")
        with self.assertRaisesRegex(ValueError, "formulas are not supported"):
            process(self.src, self.out, numeric="price")
        self.assertFalse(self.out.exists())

    def test_prior_output_preserved_on_failure(self):
        write_csv(self.src / "a.csv", [["id", "price"], ["A", "1"]])
        first = process(self.src, self.out, numeric="price")
        previous = output_file(first, "cleaned.csv").read_bytes()
        with patch("cleaner.write_xlsx", side_effect=OSError("simulated failure")):
            with self.assertRaisesRegex(OSError, "simulated failure"):
                process(self.src, self.out, numeric="price")
        self.assertEqual(output_file(first, "cleaned.csv").read_bytes(), previous)
        self.assertEqual(len(list(self.out.glob("run_*"))), 1)
        self.assertEqual(len(list(self.out.glob(".working_*"))), 0)

    def test_successful_runs_do_not_overwrite(self):
        write_csv(self.src / "a.csv", [["id"], ["A"]])
        first = process(self.src, self.out)
        second = process(self.src, self.out)
        self.assertNotEqual(first.output_directory, second.output_directory)
        self.assertTrue(output_file(first, "cleaned.csv").exists())
        self.assertTrue(output_file(second, "cleaned.xlsx").exists())

    def test_shared_defaults_are_generic(self):
        import gui
        self.assertEqual((DEFAULT_KEY, DEFAULT_REQUIRED, DEFAULT_NUMERIC),
                         ("id", "id", ""))
        self.assertIs(gui.DEFAULT_KEY, DEFAULT_KEY)

    def test_corrupt_xlsx_is_handled(self):
        (self.src / "broken.xlsx").write_bytes(b"not a real workbook")
        with self.assertRaisesRegex(ValueError, "cannot read XLSX"):
            process(self.src, self.out)
        self.assertFalse(self.out.exists())

    def test_nonfinite_numeric_values_are_rejected_in_excel_export(self):
        from openpyxl import load_workbook
        write_csv(self.src / "a.csv", [["id", "amount"], ["A", "NaN"], ["B", "Infinity"]])
        result = process(self.src, self.out, numeric="amount")
        self.assertEqual((result.clean_rows, result.rejected_rows), (0, 2))
        book = load_workbook(output_file(result, "rejected.xlsx"), read_only=True)
        try:
            rows = list(book.active.values)
        finally:
            book.close()
        self.assertEqual([rows[1][1], rows[2][1]], ["NaN", "Infinity"])

    def test_ragged_csv_rows_are_rejected(self):
        write_csv(self.src / "ragged.csv", [["id", "name"], ["A", "Alice"], ["B"], ["C", "Carol", "Extra"]])
        result = process(self.src, self.out)
        self.assertEqual((result.clean_rows, result.rejected_rows), (1, 2))
        self.assertEqual(result.issues["malformed_csv_row"], 2)

    def test_business_location_header_not_renamed(self):
        write_csv(self.src / "customers.csv", [["id", "location"], ["A", "Seattle"]])
        result = process(self.src, self.out)
        self.assertIn("location", result.columns)
        self.assertNotIn("place", result.columns)

    def test_unicode_headers_preserved(self):
        write_csv(self.src / "clients.csv", [["id", "고객명", "Café Name"], ["A", "Kim", "North"]])
        result = process(self.src, self.out)
        self.assertEqual(result.columns, ["id", "고객명", "café_name"])

    def test_excel_zero_padded_identifiers(self):
        from openpyxl import Workbook
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["id", "customer"])
        sheet.append([123, "Alice"])
        sheet["A2"].number_format = "000000"
        workbook.save(self.src / "ids.xlsx")
        result = process(self.src, self.out)
        with output_file(result, "cleaned.csv").open(encoding="utf-8-sig", newline="") as f:
            self.assertEqual(next(csv.DictReader(f))["id"], "000123")

    def test_excel_large_numeric_text_preserved(self):
        from openpyxl import load_workbook
        big = "12345678901234567890"
        write_csv(self.src / "large.csv", [["id", "amount"], ["A", big]])
        result = process(self.src, self.out, numeric="amount")
        book = load_workbook(output_file(result, "cleaned.xlsx"), read_only=True)
        try:
            self.assertEqual(list(book.active.values)[1][1], big)
        finally:
            book.close()

    def test_numeric_plus_sign_exports_consistently(self):
        from openpyxl import load_workbook
        write_csv(self.src / "numbers.csv", [["id", "amount"], ["A", "+125"]])
        result = process(self.src, self.out, numeric="amount")
        with output_file(result, "cleaned.csv").open(encoding="utf-8-sig", newline="") as f:
            self.assertEqual(next(csv.DictReader(f))["amount"], "125")
        book = load_workbook(output_file(result, "cleaned.xlsx"), read_only=True)
        try:
            self.assertEqual(list(book.active.values)[1][1], 125)
        finally:
            book.close()

    def test_excel_lock_file_ignored(self):
        write_csv(self.src / "orders.csv", [["id"], ["A"]])
        (self.src / "~$active.xlsx").write_bytes(b"lock placeholder")
        result = process(self.src, self.out)
        self.assertEqual(result.input_files, 1)

    def test_excel_format_only_extra_columns_ignored(self):
        from openpyxl import Workbook
        book = Workbook()
        sheet = book.active
        sheet.append(["id", "name"])
        sheet.append(["A", "Alice"])
        sheet["J8"].number_format = "0.00"
        book.save(self.src / "styled.xlsx")
        result = process(self.src, self.out)
        self.assertEqual((result.clean_rows, result.rejected_rows), (1, 0))

    def test_excel_error_cell_rejected(self):
        from openpyxl import Workbook
        book = Workbook()
        sheet = book.active
        sheet.append(["id", "total"])
        sheet.append(["A", "#DIV/0!"])
        sheet["B2"].data_type = "e"
        book.save(self.src / "broken.xlsx")
        result = process(self.src, self.out)
        self.assertEqual((result.clean_rows, result.rejected_rows), (0, 1))
        self.assertEqual(result.issues["excel_error_cell"], 1)

    def test_ragged_csv_extra_values_preserved(self):
        write_csv(self.src / "ragged.csv", [["id", "name"], ["A", "Alice", "EXTRA"]])
        result = process(self.src, self.out)
        with output_file(result, "rejected.csv").open(encoding="utf-8-sig", newline="") as f:
            row = next(csv.DictReader(f))
        self.assertEqual(row["__extra_values"], '["EXTRA"]')

    def test_ragged_excel_extra_values_preserved(self):
        from openpyxl import Workbook
        book = Workbook()
        sheet = book.active
        sheet.append(["id", "name"])
        sheet.append(["A", "Alice", "EXTRA"])
        book.save(self.src / "ragged.xlsx")
        result = process(self.src, self.out)
        with output_file(result, "rejected.csv").open(encoding="utf-8-sig", newline="") as f:
            row = next(csv.DictReader(f))
        self.assertEqual(row["__extra_values"], '["EXTRA"]')

    def test_processing_summary_available_in_memory(self):
        write_csv(self.src / "one.csv", [["id"], ["A"]])
        result = process(self.src, self.out)
        self.assertEqual((result.processed_rows, result.clean_rows), (1, 1))
        self.assertEqual(len(list(Path(result.output_directory).iterdir())), 6)

    def test_bundled_demo_without_special_mode(self):
        source = Path(__file__).resolve().parents[1] / "data" / "input"
        result = process(source, self.out, required="id,time,latitude,longitude",
                         numeric="latitude,longitude,depth,magnitude")
        self.assertEqual((result.input_files, result.processed_rows, result.clean_rows,
                          result.duplicate_rows, result.rejected_rows), (3, 195, 180, 6, 9))

    def test_drop_file_path_as_direct_input(self):
        write_csv(self.src / "first.csv", [["id", "name"], ["A", "Alpha"]])
        write_csv(self.src / "excluded.csv", [["id", "name"], ["B", "Beta"]])
        result = process(self.src / "first.csv", self.out)
        self.assertEqual((result.input_files, result.clean_rows), (1, 1))

    def test_drop_multiple_files_and_folders_without_repeating_inputs(self):
        other = self.root / "with spaces"
        other.mkdir()
        write_csv(self.src / "first.csv", [["id", "name"], ["A", "Alpha"]])
        write_csv(other / "second.csv", [["id", "name"], ["B", "Beta"]])
        result = process([other / "second.csv", self.src, self.src / "first.csv"], self.out)
        self.assertEqual((result.input_files, result.clean_rows), (2, 2))

    def test_drop_folder_preserves_output_isolation(self):
        write_csv(self.src / "first.csv", [["id"], ["A"]])
        with self.assertRaisesRegex(ValueError, "separate"):
            process([self.src], self.src / "results")

    def test_drop_rejects_missing_or_empty_selection(self):
        with self.assertRaisesRegex(ValueError, "do not exist"):
            process([self.src / "absent.csv"], self.out)
        with self.assertRaisesRegex(ValueError, "do not exist"):
            process([], self.out)


    def test_only_requested_format_is_created(self):
        write_csv(self.src / "one.csv", [["id", "amount"], ["A", "10"], ["A", "10"], ["B", "oops"]])
        result = process(self.src, self.out, numeric="amount",
                         exports={"cleaned.xlsx", "rejected.csv"}, prefix="October_2026")
        files = {p.name for p in Path(result.output_directory).iterdir()}
        self.assertEqual(files, {"October_2026_cleaned.xlsx", "October_2026_rejected.csv"})
        self.assertEqual((result.clean_rows, result.duplicate_rows, result.rejected_rows), (1, 1, 1))

    def test_prefixed_files_contain_only_selected_csv_xlsx(self):
        write_csv(self.src / "one.csv", [["id"], ["A"]])
        result = process(self.src, self.out, exports={"cleaned.csv", "rejected.xlsx"},
                         prefix="client_1")
        self.assertEqual({p.name for p in Path(result.output_directory).iterdir()},
                         {"client_1_cleaned.csv", "client_1_rejected.xlsx"})

    def test_removed_html_output_is_rejected(self):
        write_csv(self.src / "one.csv", [["id"], ["A"]])
        with self.assertRaisesRegex(ValueError, "supported output"):
            process(self.src, self.out, exports={"report.html"})
        self.assertFalse(self.out.exists())

    def test_single_output_does_not_create_extra_files(self):
        write_csv(self.src / "one.csv", [["id"], ["A"]])
        result = process(self.src, self.out, exports={"cleaned.csv"})
        self.assertEqual([p.name for p in Path(result.output_directory).iterdir()], ["cleaned.csv"])

    def test_invalid_output_selections_and_prefix_do_not_create_results(self):
        write_csv(self.src / "one.csv", [["id"], ["A"]])
        for kwargs in ({"exports": set()}, {"exports": {"cleaned.pdf"}}, {"exports": {"report.html"}},
                       {"exports": {"summary.json"}},
                       {"prefix": "../unsafe"}, {"prefix": "a/b"}, {"prefix": "a" * 41}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaisesRegex(ValueError, "output|prefix"):
                    process(self.src, self.out, **kwargs)
        self.assertFalse(self.out.exists())

    def test_valid_unicode_prefix(self):
        write_csv(self.src / "one.csv", [["id"], ["A"]])
        result = process(self.src, self.out, exports={"cleaned.csv"}, prefix="고객사_10월")
        self.assertTrue(output_file(result, "고객사_10월_cleaned.csv").is_file())



if __name__ == "__main__":
    unittest.main()
