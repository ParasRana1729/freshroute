"""Recover the complete rows of FreshRoute's October–November 2025 APMC benchmark."""
from __future__ import annotations

import argparse
import csv
from io import TextIOWrapper
from pathlib import Path
from tempfile import NamedTemporaryFile

import requests

ROOT = Path(__file__).resolve().parents[1]
PORTAL_CSV = (
    "https://ckandev.indiadataportal.com/dataset/1749d812-35b4-4635-ac29-dd3116ed31b0"
    "/resource/078fd1ea-dab6-4aca-aed9-3a4b8b2c761d/download"
    "/apmc-arrivals-and-prices-new-source.csv"
)
# The original export's final (394,258th) record lacked a modal price and was
# discarded by the cleaner. The archive now contains the rest of that day's data.
LAST_COMPLETE_ID = 394_257
FIRST_DATE = "2025-10-27"
LAST_DATE = "2025-11-19"


def fetch_benchmark(output: Path) -> None:
    """Download the archive prefix and publish the CSV after validating its row IDs."""
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with requests.get(
            PORTAL_CSV, headers={"Range": "bytes=0-120000000"}, stream=True, timeout=(15, 60)
        ) as response:
            response.raise_for_status()
            response.raw.decode_content = True
            with TextIOWrapper(response.raw, encoding="utf-8-sig", newline="") as source, (
                NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=output.parent, delete=False)
            ) as destination:
                temporary = Path(destination.name)
                reader = csv.reader(source)
                writer = csv.writer(destination)
                header = next(reader, [])
                if len(header) != 22 or header[:2] != ["id", "date"]:
                    raise ValueError("Unexpected India Data Portal CSV schema")
                writer.writerow(header)
                previous_date = FIRST_DATE
                for row_id in range(1, LAST_COMPLETE_ID + 1):
                    row = next(reader, [])
                    if len(row) != len(header) or row[0] != str(row_id):
                        raise ValueError(f"Expected complete archive record {row_id}")
                    if not previous_date <= row[1] <= LAST_DATE or (row_id == 1 and row[1] != FIRST_DATE):
                        raise ValueError(f"Unexpected date for archive record {row_id}: {row[1]}")
                    previous_date = row[1]
                    writer.writerow(row)
                if previous_date != LAST_DATE:
                    raise ValueError(f"Expected the benchmark to end on {LAST_DATE}")
        temporary.replace(output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data/raw/apmc_arrivals_prices.csv")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing output CSV")
    args = parser.parse_args()
    if args.output.exists() and not args.overwrite:
        parser.error(f"{args.output} exists. Use --overwrite to replace it.")
    try:
        fetch_benchmark(args.output)
    except requests.RequestException as error:
        status = f" (HTTP {error.response.status_code})" if error.response is not None else ""
        parser.exit(1, f"India Data Portal download failed{status}.\n")
    except (OSError, ValueError) as error:
        parser.exit(1, f"Benchmark download failed: {error}\n")
    print(f"Wrote {LAST_COMPLETE_ID:,} benchmark records to {args.output}")


if __name__ == "__main__":
    main()
