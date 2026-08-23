from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = PROJECT_ROOT / "data" / "raw" / "complaints_sample.csv"


def explore_complaints():
    complaints = pd.read_csv(INPUT_FILE, low_memory=False)

    print("\nDATASET SIZE")
    print(f"Rows: {complaints.shape[0]}")
    print(f"Columns: {complaints.shape[1]}")

    print("\nCOLUMN NAMES")
    for column in complaints.columns:
        print(f"- {column}")

    print("\nMISSING VALUES")
    missing_values = complaints.isna().sum().sort_values(ascending=False)
    print(missing_values)

    print("\nDUPLICATE COMPLAINT IDS")
    print(complaints["Complaint ID"].duplicated().sum())

    print("\nTOP 10 PRODUCTS")
    print(complaints["Product"].value_counts().head(10))

    print("\nTOP 10 ISSUES")
    print(complaints["Issue"].value_counts().head(10))

    print("\nTOP 10 COMPANIES")
    print(complaints["Company"].value_counts().head(10))

    print("\nTIMELY RESPONSE DISTRIBUTION")
    print(complaints["Timely response?"].value_counts(dropna=False))


if __name__ == "__main__":
    explore_complaints()