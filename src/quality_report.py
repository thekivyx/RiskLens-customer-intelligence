from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = PROJECT_ROOT / "data" / "processed" / "complaints_clean.csv"
REPORT_FILE = PROJECT_ROOT / "data" / "processed" / "quality_report.csv"


def generate_quality_report():
    complaints = pd.read_csv(
        INPUT_FILE,
        low_memory=False,
        parse_dates=["date_received", "date_sent_to_company"],
    )

    total_records = len(complaints)

    checks = [
        {
            "check_name": "Total records",
            "failed_records": 0,
            "checked_records": total_records,
        },
        {
            "check_name": "Missing complaint ID",
            "failed_records": complaints["complaint_id"].isna().sum(),
            "checked_records": total_records,
        },
        {
            "check_name": "Duplicate complaint ID",
            "failed_records": complaints["complaint_id"].duplicated().sum(),
            "checked_records": total_records,
        },
        {
            "check_name": "Missing received date",
            "failed_records": complaints["date_received"].isna().sum(),
            "checked_records": total_records,
        },
        {
            "check_name": "Missing product",
            "failed_records": complaints["product"].isna().sum(),
            "checked_records": total_records,
        },
        {
            "check_name": "Missing issue",
            "failed_records": complaints["issue"].isna().sum(),
            "checked_records": total_records,
        },
        {
            "check_name": "Missing company",
            "failed_records": complaints["company"].isna().sum(),
            "checked_records": total_records,
        },
        {
            "check_name": "Duplicate full rows",
            "failed_records": complaints.duplicated().sum(),
            "checked_records": total_records,
        },
        {
            "check_name": "Missing narratives",
            "failed_records": complaints[
                "consumer_complaint_narrative"
            ].isna().sum(),
            "checked_records": total_records,
        },
    ]

    report = pd.DataFrame(checks)

    report["pass_rate_percent"] = (
        (report["checked_records"] - report["failed_records"])
        / report["checked_records"]
        * 100
    ).round(2)

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(REPORT_FILE, index=False)

    print("\nRISK LENS DATA-QUALITY REPORT")
    print(report.to_string(index=False))
    print(f"\nReport saved to: {REPORT_FILE}")


if __name__ == "__main__":
    generate_quality_report()