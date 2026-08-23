import os
from pathlib import Path

import mysql.connector
import pandas as pd
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = PROJECT_ROOT / "data" / "processed" / "complaints_clean.csv"

load_dotenv(PROJECT_ROOT / ".env", override=True)


def prepare_value(value):
    if pd.isna(value):
        return None

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    return value


def load_complaints():
    complaints = pd.read_csv(INPUT_FILE, low_memory=False)

    date_columns = [
        "date_received",
        "date_sent_to_company",
    ]

    for column in date_columns:
        complaints[column] = pd.to_datetime(
            complaints[column],
            errors="coerce",
            utc=True,
        ).dt.tz_localize(None)

   
    database = mysql.connector.connect(
    host="127.0.0.1",
    port=3306,
    user="root",
    password=os.getenv("MYSQL_PASSWORD"),
    database="risklens",
)

    cursor = database.cursor()

    query = """
        INSERT INTO complaints (
            complaint_id,
            date_received,
            product,
            sub_product,
            issue,
            sub_issue,
            consumer_complaint_narrative,
            company_public_response,
            company,
            state,
            zip_code,
            tags,
            submitted_via,
            date_sent_to_company,
            company_response_to_consumer,
            timely_response
        )
        VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
            date_received = VALUES(date_received),
            product = VALUES(product),
            sub_product = VALUES(sub_product),
            issue = VALUES(issue),
            sub_issue = VALUES(sub_issue),
            consumer_complaint_narrative =
                VALUES(consumer_complaint_narrative),
            company_public_response =
                VALUES(company_public_response),
            company = VALUES(company),
            state = VALUES(state),
            zip_code = VALUES(zip_code),
            tags = VALUES(tags),
            submitted_via = VALUES(submitted_via),
            date_sent_to_company =
                VALUES(date_sent_to_company),
            company_response_to_consumer =
                VALUES(company_response_to_consumer),
            timely_response = VALUES(timely_response)
    """

    columns = [
        "complaint_id",
        "date_received",
        "product",
        "sub_product",
        "issue",
        "sub_issue",
        "consumer_complaint_narrative",
        "company_public_response",
        "company",
        "state",
        "zip_code",
        "tags",
        "submitted_via",
        "date_sent_to_company",
        "company_response_to_consumer",
        "timely_response",
    ]

    records = [
        tuple(prepare_value(value) for value in row)
        for row in complaints[columns].itertuples(
            index=False,
            name=None,
        )
    ]

    try:
        cursor.executemany(query, records)
        database.commit()

        print(f"Successfully loaded {len(records)} complaints.")

    except Exception:
        database.rollback()
        raise

    finally:
        cursor.close()
        database.close()


if __name__ == "__main__":
    load_complaints()