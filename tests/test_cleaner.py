import csv
import tempfile
import unittest
from pathlib import Path
from cleaner import process, normalize_header


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerows(rows)


class CleaningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.src = self.root / "input"
        self.src.mkdir()
        self.out = self.root / "output"

    def test_multiple_files_aliases_duplicates_invalid(self):
        write_csv(self.src / "a.csv", [
            ["ID", "Time", "Latitude", "mag"],
            ["EQ1", "2026-10-01", "35.1", "3.1"],
            ["EQ2", "2026-10-02", "12.0", "2.8"],
        ])
        write_csv(self.src / "b.csv", [
            ["event_id", "time", "latitude_deg", "Magnitude"],
            ["EQ1", "2026-10-01", "35.1", "3.1"],
            ["EQ3", "2026-10-03", "invalid", "3.8"],
            ["", "2026-10-04", "20.1", "4.2"],
            ["EQ4", "2026-10-05", "55.0", "5.0"],
        ])
        result = process(self.src, self.out, "id", "id,time,latitude", "latitude,magnitude")
        self.assertEqual((result.processed_rows, result.clean_rows, result.duplicate_rows,
                          result.rejected_rows), (6, 3, 1, 2))
        self.assertEqual(result.issues["duplicate_id"], 1)
        self.assertEqual(result.issues["invalid_number_latitude"], 1)
        self.assertEqual(result.issues["missing_id"], 1)
        self.assertTrue((self.out / "report.html").exists())
        with (self.out / "cleaned.csv").open(encoding="utf-8-sig", newline="") as fp:
            rows = list(csv.DictReader(fp))
        self.assertEqual({r["id"] for r in rows}, {"EQ1", "EQ2", "EQ4"})
        self.assertEqual(rows[0]["magnitude"], "3.1")

    def test_missing_key_fails_without_outputs(self):
        write_csv(self.src / "one.csv", [["item", "name"], ["a", "Alice"]])
        with self.assertRaisesRegex(ValueError, "absent"):
            process(self.src, self.out)
        self.assertFalse(self.out.exists())

    def test_protect_against_overlapping_paths(self):
        write_csv(self.src / "a.csv", [["id"], ["1"]])
        with self.assertRaisesRegex(ValueError, "separate"):
            process(self.src, self.src / "output")

    def test_formula_sanitization(self):
        write_csv(self.src / "a.csv", [["id", "name"], ["1", "=HYPERLINK(\"test\")"]])
        process(self.src, self.out)
        with (self.out / "cleaned.csv").open(encoding="utf-8-sig", newline="") as fp:
            result = next(csv.DictReader(fp))
        self.assertTrue(result["name"].startswith("'="))

    def test_normalize_header(self):
        self.assertEqual(normalize_header(" Latitude Deg "), "latitude")
        self.assertEqual(normalize_header("Event ID"), "id")

    def test_duplicate_headers_not_silent(self):
        write_csv(self.src / "a.csv", [["ID", "event_id"], ["one", "two"]])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            process(self.src, self.out)


if __name__ == "__main__":
    unittest.main()
