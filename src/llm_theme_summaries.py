import os
import re
import time
from pathlib import Path
from typing import Literal

import pandas as pd
from dotenv import load_dotenv
from google import genai
from sklearn.feature_extraction.text import CountVectorizer
from google.genai import types
from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parent.parent

COMPLAINTS_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "complaints_clean.csv"
)

THEMES_FILE = (
    PROJECT_ROOT
    / "reports"
    / "emerging_themes.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "reports"
    / "llm_theme_summaries.csv"
)

MODEL_NAME = "gemini-3.5-flash-lite"
THEMES_PER_PRODUCT = 3
NARRATIVES_PER_THEME = 5


class ThemeSummary(BaseModel):
    cluster_summary: str = Field(
        description="A concise, factual summary of the complaint cluster."
    )
    customer_need: str = Field(
        description="The primary unmet customer need."
    )
    risk_implication: str = Field(
        description="The potential service or operational risk."
    )
    urgency: Literal["Low", "Medium", "High", "Critical"]
    recommended_action: str = Field(
        description="A practical investigation or improvement action."
    )
    confidence: float = Field(ge=0, le=1)
    requires_human_review: bool
    evidence_complaint_ids: list[int]


def remove_personal_information(text):
    """Remove common personal information before API processing."""

    text = re.sub(
        r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b",
        "[EMAIL REMOVED]",
        text,
    )

    text = re.sub(
        r"\b(?:\+?\d[\d\s().-]{7,}\d)\b",
        "[NUMBER REMOVED]",
        text,
    )

    return text[:1500]


def load_data():
    if not COMPLAINTS_FILE.exists():
        raise FileNotFoundError(
            f"Complaint file not found: {COMPLAINTS_FILE}"
        )

    if not THEMES_FILE.exists():
        raise FileNotFoundError(
            f"Emerging-themes file not found: {THEMES_FILE}"
        )

    complaints = pd.read_csv(
        COMPLAINTS_FILE,
        low_memory=False,
    )

    themes = pd.read_csv(
        THEMES_FILE,
        low_memory=False,
    )

    complaints["date_received"] = pd.to_datetime(
        complaints["date_received"],
        errors="coerce",
        utc=True,
    ).dt.tz_localize(None)

    themes["recent_start"] = pd.to_datetime(
        themes["recent_start"],
        errors="coerce",
    )

    themes["recent_end"] = pd.to_datetime(
        themes["recent_end"],
        errors="coerce",
    )

    return complaints, themes


def select_top_themes(themes):
    return (
        themes.sort_values(
            ["product", "emergence_score"],
            ascending=[True, False],
        )
        .groupby(
            "product",
            group_keys=False,
        )
        .head(THEMES_PER_PRODUCT)
        .reset_index(drop=True)
    )


def find_supporting_complaints(complaints, theme):
    product = theme["product"]
    term = str(theme["term"]).lower()
    recent_start = theme["recent_start"]
    recent_end = theme["recent_end"]

    candidates = complaints[
        (complaints["product"] == product)
        & complaints["date_received"].between(
            recent_start,
            recent_end
            + pd.Timedelta(days=1)
            - pd.Timedelta(seconds=1),
        )
    ].copy()

    candidates = candidates.dropna(
        subset=["consumer_complaint_narrative"]
    )

    analyser = CountVectorizer(
        stop_words="english",
        ngram_range=(2, 2),
    ).build_analyzer()

    candidates = candidates[
        candidates[
            "consumer_complaint_narrative"
        ].apply(
            lambda narrative: (
                term in analyser(str(narrative))
            )
        )
    ]

    return candidates.head(NARRATIVES_PER_THEME)


def build_prompt(theme, supporting_complaints):
    evidence_sections = []

    for _, complaint in supporting_complaints.iterrows():
        complaint_id = int(complaint["complaint_id"])

        narrative = remove_personal_information(
            str(complaint["consumer_complaint_narrative"])
        )

        evidence_sections.append(
            f"""
Complaint ID: {complaint_id}
Recorded issue: {complaint.get("issue", "Unknown")}
Narrative: {narrative}
"""
        )

    evidence_text = "\n".join(evidence_sections)

    return f"""
You are supporting a financial-services customer-experience
and operational-risk analytics team.

Analyse this emerging complaint cluster using only the supplied
evidence.

Product: {theme["product"]}
Detected term: {theme["term"]}
Recent mentions: {int(theme["recent_mentions"])}
Baseline mentions: {int(theme["baseline_mentions"])}
Growth rate: {theme["growth_rate_percent"]}%
Emergence score: {theme["emergence_score"]}

Rules:
- Do not invent information.
- Do not make legal conclusions.
- Describe allegations as customer-reported claims.
- The evidence complaint IDs must come only from the supplied records.
- Recommend investigation or service improvement, not automatic
  action against a company or customer.
- Set requires_human_review to true when the evidence is ambiguous,
  sensitive, potentially urgent or based on a small sample.
- Base urgency on the nature of the complaints, not growth alone.
- Keep each written field concise and executive-ready.
- Do not infer regulatory violations or cite regulations unless
  they are explicitly mentioned in the supplied evidence.
Supporting complaints:
{evidence_text}
"""


def analyse_themes():
    load_dotenv(PROJECT_ROOT / ".env")

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY was not found in the .env file."
        )

    complaints, themes = load_data()
    selected_themes = select_top_themes(themes)

    client = genai.Client(api_key=api_key)
    results = []

    for _, theme in selected_themes.iterrows():
        product = theme["product"]
        term = theme["term"]

        print(f"\nAnalysing: {product} — {term}")

        supporting_complaints = find_supporting_complaints(
            complaints,
            theme,
        )

        if supporting_complaints.empty:
            print("Skipped: no supporting narratives found.")
            continue

        allowed_ids = set(
            supporting_complaints["complaint_id"]
            .astype(int)
            .tolist()
        )

        prompt = build_prompt(
            theme,
            supporting_complaints,
        )

        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ThemeSummary,
                    temperature=0.1,
                    automatic_function_calling=(
                        types.AutomaticFunctionCallingConfig(
                            disable=True
                        )
                    ),
                ),
            )

            analysis = ThemeSummary.model_validate_json(
                response.text
            )

            validated_ids = [
                complaint_id
                for complaint_id in analysis.evidence_complaint_ids
                if complaint_id in allowed_ids
            ]

            if not validated_ids:
                analysis.requires_human_review = True

            result = {
                "product": product,
                "term": term,
                "recent_mentions": int(
                    theme["recent_mentions"]
                ),
                "baseline_mentions": int(
                    theme["baseline_mentions"]
                ),
                "growth_rate_percent": theme[
                    "growth_rate_percent"
                ],
                "emergence_score": theme[
                    "emergence_score"
                ],
                "supporting_records": len(
                    supporting_complaints
                ),
                "cluster_summary": analysis.cluster_summary,
                "customer_need": analysis.customer_need,
                "risk_implication": analysis.risk_implication,
                "urgency": analysis.urgency,
                "recommended_action": (
                    analysis.recommended_action
                ),
                "confidence": analysis.confidence,
                "requires_human_review": (
                    analysis.requires_human_review
                ),
                "evidence_complaint_ids": ";".join(
                    str(value)
                    for value in validated_ids
                ),
                "model_name": MODEL_NAME,
            }

            results.append(result)

            pd.DataFrame(results).to_csv(
                OUTPUT_FILE,
                index=False,
            )

            print(
                f"Completed: urgency={analysis.urgency}, "
                f"confidence={analysis.confidence}"
            )

        except Exception as error:
            print(f"Failed: {error}")

        time.sleep(2)

    if not results:
        raise ValueError(
            "No LLM theme summaries were generated."
        )

    results_frame = pd.DataFrame(results)

    print("\nLLM THEME SUMMARIES")
    print("=" * 50)

    print(
        results_frame[
            [
                "product",
                "term",
                "urgency",
                "confidence",
                "requires_human_review",
            ]
        ].to_string(index=False)
    )

    print(f"\nSaved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    analyse_themes()