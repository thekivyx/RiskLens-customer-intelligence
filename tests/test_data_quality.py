from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PROCESSED_DATA_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "complaints_clean.csv"
)

SAMPLE_DATA_FILE = (
    PROJECT_ROOT
    / "tests"
    / "fixtures"
    / "complaints_sample.csv"
)

DATA_FILE = (
    PROCESSED_DATA_FILE
    if PROCESSED_DATA_FILE.exists()
    else SAMPLE_DATA_FILE
)
@pytest.fixture(scope="module")
def complaints():
    assert DATA_FILE.exists(), (
        f"Test data file not found: {DATA_FILE}"
    )

    return pd.read_csv(
        DATA_FILE,
        low_memory=False,
    )

def test_dataset_is_not_empty(complaints):
    assert not complaints.empty


def test_required_columns_exist(complaints):
    required_columns = {
        "complaint_id",
        "date_received",
        "product",
        "issue",
        "company",
        "timely_response",
    }

    missing_columns = (
        required_columns - set(complaints.columns)
    )

    assert not missing_columns, (
        f"Missing columns: {missing_columns}"
    )


def test_complaint_ids_are_not_missing(complaints):
    assert complaints["complaint_id"].notna().all()


def test_complaint_ids_are_unique(complaints):
    duplicate_count = (
        complaints["complaint_id"].duplicated().sum()
    )

    assert duplicate_count == 0, (
        f"Found {duplicate_count} duplicate complaint IDs"
    )


def test_received_dates_are_valid(complaints):
    parsed_dates = pd.to_datetime(
        complaints["date_received"],
        errors="coerce",
        utc=True,
    )

    invalid_count = parsed_dates.isna().sum()

    assert invalid_count == 0, (
        f"Found {invalid_count} invalid received dates"
    )


def test_required_business_fields_are_present(complaints):
    required_fields = [
        "product",
        "issue",
        "company",
    ]

    missing_counts = (
        complaints[required_fields]
        .isna()
        .sum()
    )

    assert missing_counts.sum() == 0, (
        f"Missing required values:\n{missing_counts}"
    )


def test_timely_response_values_are_valid(complaints):
    actual_values = set(
        complaints["timely_response"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.lower()
        .unique()
    )

    expected_values = {"yes", "no"}

    unexpected_values = (
        actual_values - expected_values
    )

    assert not unexpected_values, (
        f"Unexpected timely-response values: "
        f"{unexpected_values}"
    )