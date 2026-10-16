"""Command-line entry point for reproducible batch cleanup."""
import argparse
import csv
import json
import sys
from dataclasses import asdict
from cleaner import process


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge, validate and deduplicate CSV files.")
    parser.add_argument("--input", required=True, help="Directory with input CSV files")
    parser.add_argument("--output", required=True, help="Separate output directory")
    parser.add_argument("--key", default="id", help="Unique record key (default: id)")
    parser.add_argument("--required", default="id", help="Comma-separated required columns")
    parser.add_argument("--numeric", default="", help="Comma-separated numeric columns")
    args = parser.parse_args()
    try:
        result = process(args.input, args.output, args.key, args.required, args.numeric)
    except (OSError, ValueError, UnicodeError, csv.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(asdict(result), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
