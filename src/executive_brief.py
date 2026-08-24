import os
from datetime import datetime
from pathlib import Path

import mysql.connector
import pandas as pd
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent

THEMES_FILE = (
    PROJECT_ROOT
    / "reports"
    / "emerging_themes.csv"
)

OUTPUT_FOLDER = (
    PROJECT_ROOT
    / "reports"
    / "daily_briefs"
)

load_dotenv(
    PROJECT_ROOT / ".env",
    override=True,
)


def get_database_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password=os.getenv("MYSQL_PASSWORD"),
        database="risklens",
    )


def fetch_rows(connection, query):
    cursor = connection.cursor(dictionary=True)
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    return rows


def generate_executive_brief():
    connection = get_database_connection()

    alert_query = """
        SELECT
            alert_date,
            product,
            company,
            current_value,
            baseline_value,
            week_over_week_growth,
            anomaly_z_score,
            alert_level,
            alert_explanation
        FROM vw_risk_alerts
        ORDER BY
            FIELD(
                alert_level,
                'Critical',
                'Warning',
                'Watch'
            ),
            anomaly_z_score DESC
    """

    product_query = """
        SELECT
            complaint_date,
            product,
            complaint_count,
            rolling_28_day_average,
            week_over_week_growth,
            anomaly_z_score,
            alert_level
        FROM vw_product_risk_signals
        WHERE data_status = 'Complete'
          AND baseline_days >= 14
          AND complaint_date = (
              SELECT MAX(complaint_date)
              FROM vw_product_risk_signals
              WHERE data_status = 'Complete'
                AND baseline_days >= 14
          )
        ORDER BY product
    """

    alerts = fetch_rows(
        connection,
        alert_query,
    )

    product_metrics = fetch_rows(
        connection,
        product_query,
    )

    connection.close()

    themes = pd.read_csv(THEMES_FILE)

    critical_count = sum(
        row["alert_level"] == "Critical"
        for row in alerts
    )

    warning_count = sum(
        row["alert_level"] == "Warning"
        for row in alerts
    )

    watch_count = sum(
        row["alert_level"] == "Watch"
        for row in alerts
    )

    if product_metrics:
        reporting_date = product_metrics[0][
            "complaint_date"
        ]
    else:
        reporting_date = datetime.now().date()

    lines = [
        "# RiskLens Executive Brief",
        "",
        f"**Latest complete data:** {reporting_date}",
        "",
        "## Executive summary",
        "",
        (
            f"RiskLens identified **{len(alerts)} company-level "
f"signals during the complete monitoring period**: "
            f"**{critical_count} critical**, "
            f"**{warning_count} warning**, and "
            f"**{watch_count} watch**."
        ),
        "",
        (
            "Recent incomplete CFPB publication dates are "
            "excluded from anomaly decisions."
        ),
        "",
        "## Product overview",
        "",
    ]

    for row in product_metrics:
        baseline = float(
            row["rolling_28_day_average"]
        )

        lines.append(
            f"- **{row['product']}**: "
            f"{row['complaint_count']} complaints versus "
            f"a 28-day baseline of {baseline:.2f}; "
            f"weekly change "
            f"{row['week_over_week_growth']}%; "
            f"status: {row['alert_level']}."
        )

    lines.extend(
        [
            "",
            "## Company risk alerts",
            "",
        ]
    )

    for row in alerts:
        lines.append(
            f"- **{row['alert_level']} — "
f"{row['company']}** "
f"({row['alert_date']}): "
            f"{row['alert_explanation']} "
            f"Z-score: {row['anomaly_z_score']}."
        )

    lines.extend(
        [
            "",
            "## Emerging complaint themes",
            "",
        ]
    )

    for product in themes["product"].unique():
        lines.append(f"### {product}")
        lines.append("")

        product_themes = (
            themes[themes["product"] == product]
            .head(5)
        )

        for _, row in product_themes.iterrows():
            lines.append(
                f"- **{row['term']}**: "
                f"{int(row['recent_mentions'])} recent "
                f"mentions; growth "
                f"{row['growth_rate_percent']:.2f}%."
            )

        lines.append("")

    lines.extend(
        [
            "## Methodology note",
            "",
            (
                "Alerts use explainable rolling baselines, "
                "week-over-week growth and z-score anomaly "
                "detection. Complaint volume does not account "
                "for company size or market share."
            ),
            "",
            (
                "Narrative themes compare the latest seven "
                "days containing published narratives against "
                "the preceding 28-day baseline."
            ),
        ]
    )

    OUTPUT_FOLDER.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        OUTPUT_FOLDER
        / f"risklens_brief_{reporting_date}.md"
    )

    output_file.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print(f"Executive brief saved to: {output_file}")
    print("\n".join(lines))


if __name__ == "__main__":
    generate_executive_brief()