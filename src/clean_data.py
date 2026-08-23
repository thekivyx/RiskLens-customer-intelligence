from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = PROJECT_ROOT / "data" / "raw" / "complaints_sample.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "complaints_clean.csv"


def clean_complaints():
    complaints = pd.read_csv(INPUT_FILE, low_memory=False)

    print(f"Raw records: {len(complaints)}")

    # Convert column names into database-friendly names
    complaints.columns = (
        complaints.columns
        .str.strip()
        .str.lower()
        .str.replace("?", "", regex=False)
        .str.replace("-", "_", regex=False)
        .str.replace(" ", "_", regex=False)
    )

    # Convert dates from text into datetime values
    date_columns = [
        "date_received",
        "date_sent_to_company",
    ]

    for column in date_columns:
        complaints[column] = pd.to_datetime(
            complaints[column],
            errors="coerce",
            utc=True,
        )

    # Standardize text fields
    text_columns = [
        "product",
        "sub_product",
        "issue",
        "sub_issue",
        "company",
        "state",
        "submitted_via",
        "company_response_to_consumer",
        "timely_response",
    ]

    for column in text_columns:
        complaints[column] = complaints[column].astype("string").str.strip()

    # Remove records with missing essential information
    required_columns = [
        "complaint_id",
        "date_received",
        "product",
        "issue",
        "company",
    ]

    missing_required = complaints[required_columns].isna().any(axis=1)
    rejected_count = missing_required.sum()

    complaints = complaints.loc[~missing_required].copy()

    # Remove duplicate complaint IDs
    duplicate_count = complaints["complaint_id"].duplicated().sum()
    complaints = complaints.drop_duplicates(
        subset="complaint_id",
        keep="last",
    )

    # Sort records consistently
    complaints = complaints.sort_values("date_received")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    complaints.to_csv(OUTPUT_FILE, index=False)

    print(f"Rejected for missing required values: {rejected_count}")
    print(f"Duplicate complaint IDs removed: {duplicate_count}")
    print(f"Clean records: {len(complaints)}")
    print(f"Saved to: {OUTPUT_FILE}")

    print("\nCleaned columns:")
    print(complaints.columns.tolist())

    print("\nData types:")
    print(complaints.dtypes)

    return complaints


if __name__ == "__main__":
    clean_complaints()