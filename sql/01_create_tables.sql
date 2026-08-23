CREATE DATABASE IF NOT EXISTS risklens;

USE risklens;

CREATE TABLE IF NOT EXISTS complaints (
    complaint_id BIGINT PRIMARY KEY,
    date_received DATETIME NOT NULL,
    product VARCHAR(255) NOT NULL,
    sub_product VARCHAR(255),
    issue VARCHAR(500) NOT NULL,
    sub_issue VARCHAR(500),
    consumer_complaint_narrative TEXT,
    company_public_response TEXT,
    company VARCHAR(500) NOT NULL,
    state VARCHAR(100),
    zip_code VARCHAR(20),
    tags VARCHAR(255),
    submitted_via VARCHAR(100),
    date_sent_to_company DATETIME,
    company_response_to_consumer VARCHAR(255),
    timely_response VARCHAR(20),
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_complaints_date
ON complaints(date_received);

CREATE INDEX idx_complaints_product
ON complaints(product);

CREATE INDEX idx_complaints_company
ON complaints(company);

CREATE INDEX idx_complaints_issue
ON complaints(issue);