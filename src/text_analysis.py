from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "complaints_clean.csv"
)

REPORT_FILE = (
    PROJECT_ROOT
    / "reports"
    / "model_evaluation.csv"
)

SUMMARY_FILE = (
    PROJECT_ROOT
    / "reports"
    / "model_summary.txt"
)

MODEL_FILE = (
    PROJECT_ROOT
    / "models"
    / "complaint_classifier.joblib"
)

MINIMUM_CLASS_SIZE = 50


def train_text_model():
    complaints = pd.read_csv(
        INPUT_FILE,
        low_memory=False,
    )

    model_data = complaints[
        [
            "consumer_complaint_narrative",
            "issue",
        ]
    ].dropna()

    model_data["consumer_complaint_narrative"] = (
        model_data["consumer_complaint_narrative"]
        .astype(str)
        .str.strip()
    )

    model_data["issue"] = (
        model_data["issue"]
        .astype(str)
        .str.strip()
    )

    model_data = model_data[
        model_data["consumer_complaint_narrative"] != ""
    ]

    issue_counts = model_data["issue"].value_counts()

    eligible_issues = issue_counts[
        issue_counts >= MINIMUM_CLASS_SIZE
    ].index

    model_data = model_data[
        model_data["issue"].isin(eligible_issues)
    ].copy()

    print(f"Usable narratives: {len(model_data)}")
    print(f"Issue categories included: {len(eligible_issues)}")

    if len(model_data) == 0:
        raise ValueError(
            "No issue categories have enough narratives."
        )

    features = model_data["consumer_complaint_narrative"]
    target = model_data["issue"]

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=0.20,
        random_state=42,
        stratify=target,
    )

    model = Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    stop_words="english",
                    ngram_range=(1, 2),
                    min_df=3,
                    max_features=20000,
                    sublinear_tf=True,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )

    print("Training TF-IDF + Logistic Regression...")
    model.fit(x_train, y_train)

    predictions = model.predict(x_test)

    accuracy = accuracy_score(
        y_test,
        predictions,
    )

    macro_f1 = f1_score(
        y_test,
        predictions,
        average="macro",
    )

    weighted_f1 = f1_score(
        y_test,
        predictions,
        average="weighted",
    )

    report = classification_report(
        y_test,
        predictions,
        output_dict=True,
        zero_division=0,
    )

    report_dataframe = (
        pd.DataFrame(report)
        .transpose()
        .reset_index()
        .rename(columns={"index": "issue"})
    )

    REPORT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    MODEL_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_dataframe.to_csv(
        REPORT_FILE,
        index=False,
    )

    joblib.dump(
        model,
        MODEL_FILE,
    )

    summary = (
        "RiskLens Text Classification Model\n"
        "==================================\n"
        "Model: TF-IDF + Logistic Regression\n"
        f"Training records: {len(x_train)}\n"
        f"Testing records: {len(x_test)}\n"
        f"Issue categories: {len(eligible_issues)}\n"
        f"Accuracy: {accuracy:.4f}\n"
        f"Macro F1-score: {macro_f1:.4f}\n"
        f"Weighted F1-score: {weighted_f1:.4f}\n"
    )

    SUMMARY_FILE.write_text(
        summary,
        encoding="utf-8",
    )

    print("\nMODEL EVALUATION")
    print(summary)
    print(f"Evaluation saved to: {REPORT_FILE}")
    print(f"Model saved to: {MODEL_FILE}")


if __name__ == "__main__":
    train_text_model()