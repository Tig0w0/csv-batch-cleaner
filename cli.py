"""Command-line entry point for reproducible batch cleanup."""
import argparse
import csv
import sys
from cleaner import process, DEFAULT_KEY, DEFAULT_REQUIRED, DEFAULT_NUMERIC


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge, validate and deduplicate CSV/XLSX files.")
    parser.add_argument("--input", required=True, help="Directory with input CSV or XLSX files")
    parser.add_argument("--output", required=True, help="Separate output directory")
    parser.add_argument("--key", default=DEFAULT_KEY, help="Unique record key (default: id)")
    parser.add_argument("--required", default=DEFAULT_REQUIRED, help="Comma-separated required columns")
    parser.add_argument("--numeric", default=DEFAULT_NUMERIC, help="Comma-separated numeric columns")
    parser.add_argument("--exports", help="Comma-separated outputs, e.g. cleaned.xlsx,rejected.csv; default: all six")
    parser.add_argument("--prefix", default="", help="Optional filename prefix (letters, digits, _ or -)")
    args = parser.parse_args()
    try:
        result = process(args.input, args.output, args.key, args.required, args.numeric,
                         exports=set(args.exports.split(",")) if args.exports is not None else None,
                         prefix=args.prefix)
    except (OSError, ValueError, UnicodeError, RuntimeError, csv.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Processed {result.processed_rows} rows from {result.input_files} files: "
          f"{result.clean_rows} clean, {result.duplicate_rows} duplicate, "
          f"{result.rejected_rows} rejected.")
    print(f"Results: {result.output_directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
