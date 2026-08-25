from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    PROJECT_ROOT
    / "reports"
    / "llm_theme_summaries.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "reports"
    / "llm_evaluation.csv"
)


def count_evidence_ids(value):
    if pd.isna(value) or not str(value).strip():
        return 0

    return len(
        [
            item
            for item in str(value).split(";")
            if item.strip()
        ]
    )


def prepare_evaluation():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"LLM output was not found: {INPUT_FILE}"
        )

    summaries = pd.read_csv(
        INPUT_FILE,
        low_memory=False,
    )

    evaluation = summaries[
        [
            "product",
            "term",
            "supporting_records",
            "cluster_summary",
            "risk_implication",
            "urgency",
            "recommended_action",
            "confidence",
            "requires_human_review",
            "evidence_complaint_ids",
            "model_name",
        ]
    ].copy()

    evaluation["evidence_id_count"] = evaluation[
        "evidence_complaint_ids"
    ].apply(count_evidence_ids)

    evaluation["evidence_ids_valid"] = (
        (evaluation["evidence_id_count"] > 0)
        & (
            evaluation["evidence_id_count"]
            <= evaluation["supporting_records"]
        )
    )

    evaluation["minimum_evidence_met"] = (
        evaluation["supporting_records"] >= 3
    )

    evaluation["confidence_valid"] = (
        evaluation["confidence"].between(0, 1)
    )

    evaluation["manual_grounded"] = ""
    evaluation["manual_cluster_coherent"] = ""
    evaluation["manual_actionable"] = ""
    evaluation["unsupported_claims"] = ""
    evaluation["urgency_appropriate"] = ""
    evaluation["reviewer_notes"] = ""

    evaluation.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print("\nAUTOMATED LLM VALIDATION")
    print("=" * 45)
    print(f"Outputs evaluated: {len(evaluation)}")
    print(
        "Valid evidence IDs:",
        int(evaluation["evidence_ids_valid"].sum()),
    )
    print(
        "Minimum evidence met:",
        int(evaluation["minimum_evidence_met"].sum()),
    )
    print(
        "Valid confidence values:",
        int(evaluation["confidence_valid"].sum()),
    )
    print(f"\nSaved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    prepare_evaluation()