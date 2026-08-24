from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer


PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "complaints_clean.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "reports"
    / "emerging_themes.csv"
)

RECENT_DAYS = 7
BASELINE_DAYS = 28
MINIMUM_RECENT_MENTIONS = 3

PRODUCTS = [
    "Credit card",
    "Checking or savings account",
]


def analyse_product(complaints, product, complete_date):
    product_data = complaints[
        complaints["product"] == product
    ].copy()

    recent_start = (
        complete_date
        - pd.Timedelta(days=RECENT_DAYS - 1)
    )

    baseline_end = recent_start - pd.Timedelta(days=1)

    baseline_start = (
        baseline_end
        - pd.Timedelta(days=BASELINE_DAYS - 1)
    )

    product_data = product_data[
        product_data["date_received"].between(
            baseline_start,
            complete_date,
        )
    ].copy()

    product_data = product_data.dropna(
        subset=["consumer_complaint_narrative"]
    )

    product_data["period"] = np.where(
        product_data["date_received"] >= recent_start,
        "recent",
        "baseline",
    )

    recent_total = (
        product_data["period"] == "recent"
    ).sum()

    baseline_total = (
        product_data["period"] == "baseline"
    ).sum()

    if recent_total == 0 or baseline_total == 0:
        print(
            f"Skipping {product}: insufficient narratives."
        )
        return pd.DataFrame()

    vectorizer = CountVectorizer(
        stop_words="english",
        ngram_range=(2, 2),
        min_df=3,
        max_features=15000,
        binary=True,
    )

    document_term_matrix = vectorizer.fit_transform(
        product_data["consumer_complaint_narrative"]
    )

    terms = vectorizer.get_feature_names_out()

    recent_mask = (
        product_data["period"].to_numpy() == "recent"
    )

    baseline_mask = (
        product_data["period"].to_numpy() == "baseline"
    )

    recent_mentions = np.asarray(
        document_term_matrix[recent_mask].sum(axis=0)
    ).ravel()

    baseline_mentions = np.asarray(
        document_term_matrix[baseline_mask].sum(axis=0)
    ).ravel()

    recent_rate = recent_mentions / recent_total
    baseline_rate = baseline_mentions / baseline_total

    growth_rate = np.full(
        recent_rate.shape,
        np.nan,
        dtype=float,
    )

    np.divide(
        (recent_rate - baseline_rate) * 100,
        baseline_rate,
        out=growth_rate,
        where=baseline_rate > 0,
    )

    results = pd.DataFrame(
        {
            "product": product,
            "term": terms,
            "recent_mentions": recent_mentions,
            "baseline_mentions": baseline_mentions,
            "recent_rate_percent": recent_rate * 100,
            "baseline_rate_percent": baseline_rate * 100,
            "growth_rate_percent": growth_rate,
            "emergence_score": (
                recent_rate - baseline_rate
            ) * 100,
        }
    )

    results = results[
        results["recent_mentions"]
        >= MINIMUM_RECENT_MENTIONS
    ]
    noise_pattern = r"\bxx+\b|\d"

    results = results[
        ~results["term"].str.contains(
            noise_pattern,
            case=False,
            regex=True,
            na=False,
        )
    ]
    results = results.sort_values(
        "emergence_score",
        ascending=False,
    ).head(30)

    results["recent_start"] = recent_start.date()
    results["recent_end"] = complete_date.date()
    results["baseline_start"] = baseline_start.date()
    results["baseline_end"] = baseline_end.date()

    return results


def detect_emerging_themes():
    complaints = pd.read_csv(
        INPUT_FILE,
        low_memory=False,
    )

    complaints["date_received"] = pd.to_datetime(
        complaints["date_received"],
        errors="coerce",
        utc=True,
    ).dt.tz_localize(None)

    narrative_rows = complaints.dropna(
        subset=["consumer_complaint_narrative"]
    )

    complete_date = (
        narrative_rows["date_received"]
        .max()
        .normalize()
    )

    print(
        "Latest available narrative date:",
        complete_date.date(),
    )

    all_results = []

    for product in PRODUCTS:
        print(f"Analysing themes for: {product}")

        product_results = analyse_product(
            complaints,
            product,
            complete_date,
        )

        if not product_results.empty:
            all_results.append(product_results)

    if not all_results:
        raise ValueError(
            "No emerging themes could be calculated."
        )

    themes = pd.concat(
        all_results,
        ignore_index=True,
    )

    numeric_columns = [
        "recent_rate_percent",
        "baseline_rate_percent",
        "growth_rate_percent",
        "emergence_score",
    ]

    themes[numeric_columns] = (
        themes[numeric_columns].round(2)
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    themes.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    display_themes = (
        themes.groupby(
            "product",
            group_keys=False,
        )
        .head(10)
    )

    print("\nTOP EMERGING THEMES")

    print(
        display_themes[
            [
                "product",
                "term",
                "recent_mentions",
                "growth_rate_percent",
                "emergence_score",
            ]
        ].to_string(index=False)
    )

    print(f"\nSaved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    detect_emerging_themes()