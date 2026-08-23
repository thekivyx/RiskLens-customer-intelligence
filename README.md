# RiskLens

**Customer Complaint Intelligence & Early-Warning Platform**

RiskLens is a financial-services analytics platform built using public
consumer-complaint data from the Consumer Financial Protection Bureau
(CFPB).

The project is designed to identify:

- Rising complaint volumes
- Emerging customer issues
- Poor company-response patterns
- Potential operational-risk signals
- Data-quality and pipeline-health problems

## Current progress

### Day 1 — Data foundation

- Connected to the CFPB complaint REST API
- Extracted real complaint data using date filters
- Preserved the original raw dataset
- Explored products, issues, companies and response performance
- Standardized column names and data types
- Removed duplicate and invalid essential records
- Generated an automated data-quality report

## Technology stack

- Python
- pandas
- requests
- CFPB Complaint API
- MySQL — planned
- Power BI — planned
- scikit-learn — planned
- pytest and GitHub Actions — planned

## Project structure

```text
RiskLens/
├── data/
│   ├── raw/
│   └── processed/
├── src/
│   ├── extract_cfpb.py
│   ├── explore_data.py
│   ├── clean_data.py
│   └── quality_report.py
├── .gitignore
├── README.md
└── requirements.txt