import os
import re
from pathlib import Path
from typing import Literal

import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field


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
    / "llm_analysis_sample.csv"
)


class ComplaintAnalysis(BaseModel):
    summary: str = Field(
        description="A factual summary in no more than two sentences."
    )
    primary_theme: str = Field(
        description="The main customer problem."
    )
    urgency: Literal["Low", "Medium", "High", "Critical"]
    recommended_action: str = Field(
        description="A practical action for a risk or service team."
    )
    supporting_evidence: str = Field(
        description="A short phrase supported directly by the complaint."
    )
    confidence: float = Field(ge=0, le=1)
    requires_human_review: bool


def remove_personal_information(text):
    """Remove common personal information before calling the API."""

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

    return text[:6000]


def analyse_complaint():
    load_dotenv(PROJECT_ROOT / ".env")

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY was not found in the .env file."
        )

    complaints = pd.read_csv(
        INPUT_FILE,
        low_memory=False,
    )

    usable_complaints = complaints.dropna(
        subset=["consumer_complaint_narrative"]
    ).copy()

    if usable_complaints.empty:
        raise ValueError("No complaint narratives are available.")

    complaint = usable_complaints.iloc[0]

    narrative = remove_personal_information(
        str(complaint["consumer_complaint_narrative"])
    )

    prompt = f"""
You are assisting a financial-services customer-risk analyst.

Analyse only the complaint evidence supplied below.

Rules:
- Do not invent facts.
- Do not identify the consumer.
- Do not make legal conclusions.
- Keep the summary factual and concise.
- Mark requires_human_review as true when evidence is unclear,
  incomplete, highly sensitive or potentially urgent.
- Supporting evidence must be a short phrase grounded directly
  in the complaint.

Product: {complaint.get("product", "Unknown")}
Recorded issue: {complaint.get("issue", "Unknown")}

Complaint narrative:
{narrative}
"""

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ComplaintAnalysis,
            temperature=0.1,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable = True),
        ),
    )

    analysis = ComplaintAnalysis.model_validate_json(
        response.text
    )

    result = pd.DataFrame(
        [
            {
                "complaint_id": complaint.get("complaint_id"),
                "product": complaint.get("product"),
                "recorded_issue": complaint.get("issue"),
                **analysis.model_dump(),
                "model_name": "gemini-3.5-flash-lite",
            }
        ]
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print("\nLLM COMPLAINT ANALYSIS")
    print("=" * 40)
    print(result.to_string(index=False))
    print(f"\nSaved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    analyse_complaint()