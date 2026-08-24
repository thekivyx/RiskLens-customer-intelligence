from datetime import date, timedelta
from io import StringIO
from pathlib import Path
import time

import pandas as pd
import requests


API_URL = (
    "https://www.consumerfinance.gov/"
    "data-research/consumer-complaints/search/api/v1/"
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "complaints_history.csv"
)

START_DATE = date(2026, 7, 1)
END_DATE = date(2026, 8, 22)
CHUNK_DAYS = 7

PRODUCTS = [
    "Credit card",
    "Checking or savings account",
]


def extract_history():
    extracted_frames = []

    for product in PRODUCTS:
        chunk_start = START_DATE

        while chunk_start <= END_DATE:
            chunk_end = min(
                chunk_start + timedelta(days=CHUNK_DAYS - 1),
                END_DATE,
            )

            params = {
                "date_received_min": chunk_start.isoformat(),
                "date_received_max": chunk_end.isoformat(),
                "product": product,
                "format": "csv",
            }

            print(
                f"Downloading {product}: "
                f"{chunk_start} to {chunk_end}"
            )

            max_attempts = 5

            for attempt in range(1, max_attempts + 1):
                response = requests.get(
    API_URL,
    params=params,
    timeout=120,
)

                if response.status_code == 200:
                    break

                if response.status_code == 429:
                    retry_after = response.headers.get(
                        "Retry-After"
                    )

                    if retry_after and retry_after.isdigit():
                        wait_seconds = int(retry_after)
                    else:
                        wait_seconds = 30 * attempt

                    print(
                        "Rate limited. Waiting "
                        f"{wait_seconds} seconds..."
                    )

                    time.sleep(wait_seconds)
                    continue

                print("Status code:", response.status_code)
                print("Response:", response.text[:500])
                response.raise_for_status()

            else:
                raise RuntimeError(
                    "CFPB API remained rate-limited "
                    "after five attempts."
                )

            frame = pd.read_csv(
                StringIO(response.text),
                low_memory=False,
            )

            print(f"Received {len(frame)} records.")
            extracted_frames.append(frame)

            chunk_start = chunk_end + timedelta(days=1)
            time.sleep(5)

    complaints = pd.concat(
        extracted_frames,
        ignore_index=True,
    )

    before_deduplication = len(complaints)

    complaints = complaints.drop_duplicates(
        subset="Complaint ID",
        keep="last",
    )

    duplicate_count = (
        before_deduplication - len(complaints)
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    complaints.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print("\nHISTORICAL EXTRACTION COMPLETE")
    print(f"Downloaded rows: {before_deduplication}")
    print(f"Duplicate IDs removed: {duplicate_count}")
    print(f"Final unique complaints: {len(complaints)}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    extract_history()