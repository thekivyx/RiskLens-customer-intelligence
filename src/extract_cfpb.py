from pathlib import Path
from io import StringIO

import pandas as pd
import requests


API_URL = (
    "https://www.consumerfinance.gov/"
    "data-research/consumer-complaints/search/api/v1/"
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = PROJECT_ROOT / "data" / "raw" / "complaints_sample.csv"


def extract_complaints():
    params = {
        "date_received_min": "2026-08-01",
        "date_received_max": "2026-08-02",
        "format": "csv",
    }

    print("Requesting complaint data...")

    response = requests.get(
        API_URL,
        params=params,
        timeout=60,
    )

    if response.status_code != 200:
        print("Status code:", response.status_code)
        print("API response:", response.text[:1000])
        response.raise_for_status()

    complaints = pd.read_csv(StringIO(response.text))

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    complaints.to_csv(OUTPUT_FILE, index=False)

    print(f"Downloaded {len(complaints)} complaints.")
    print(f"Saved to: {OUTPUT_FILE}")

    print("\nAvailable columns:")
    print(complaints.columns.tolist())

    return complaints


if __name__ == "__main__":
    dataframe = extract_complaints()

    print("\nFirst five records:")
    print(dataframe.head())