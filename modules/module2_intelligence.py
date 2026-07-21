"""
modules/module2_intelligence.py
Module 2 - Lead Intelligence & Company Analysis

Uses an LLM to analyze a lead's stored company profile (from Module 1) and
generate: a qualification score (0-100), a score label, business needs,
opportunities, an industry fit analysis, and a reasoning breakdown
(the bullet-point factors shown in the "Lead Intelligence" panel).

Mounted in main.py as:
    app.include_router(intelligence_router, prefix="/intelligence", tags=["Module 2 - Intelligence"])
"""

import os
import json
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Lead, CompanyInsight

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("module2_intelligence")

router = APIRouter()

# --------------------------------------------------------------------------
# LLM CLIENT — supports Groq (OpenAI-compatible API) or real OpenAI.
# If GROQ_API_KEY is set, it's used (free tier, fast). Otherwise falls back
# to OPENAI_API_KEY.
# --------------------------------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

_client = None
_model = None
if GROQ_API_KEY:
    try:
        from openai import OpenAI
        _client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
        _model = GROQ_MODEL
        logger.info(f"Module 2 using Groq ({_model})")
    except Exception as e:  # pragma: no cover
        logger.warning(f"Could not init Groq client: {e}")
elif OPENAI_API_KEY:
    try:
        from openai import OpenAI
        _client = OpenAI(api_key=OPENAI_API_KEY)
        _model = OPENAI_MODEL
        logger.info(f"Module 2 using OpenAI ({_model})")
    except Exception as e:  # pragma: no cover
        logger.warning(f"Could not init OpenAI client: {e}")


# --------------------------------------------------------------------------
# SCHEMAS
# --------------------------------------------------------------------------
class ReasoningItem(BaseModel):
    factor: str
    detail: str


class InsightOut(BaseModel):
    insight_id: int
    lead_id: int
    qualification_score: int
    score_label: str
    business_needs: Optional[str] = None
    opportunities: Optional[str] = None
    industry_analysis: Optional[str] = None
    reasoning: Optional[List[ReasoningItem]] = None

    class Config:
        from_attributes = True


# --------------------------------------------------------------------------
# HELPERS
# --------------------------------------------------------------------------
def _build_prompt(lead: Lead) -> str:
    profile_lines = [
        f"Company: {lead.company_name}",
        f"Industry: {lead.industry or 'Unknown'}",
        f"Company size: {lead.company_size or 'Unknown'}",
        f"Annual revenue: {lead.annual_revenue or 'Unknown'}",
        f"Location: {lead.location or 'Unknown'}",
        f"Funding stage: {lead.funding_stage or 'Unknown'}",
        f"Technology stack: {', '.join(lead.tech_stack) if lead.tech_stack else 'Unknown'}",
        f"Current pipeline stage: {lead.lead_status or 'New'}",
    ]

    return f"""You are a B2B sales intelligence analyst. Assess how qualified this
company is as a sales prospect for a B2B SaaS company selling data/AI
infrastructure tooling.

Prospect profile:
{chr(10).join('- ' + l for l in profile_lines)}

Return ONLY valid JSON (no markdown fences) with exactly these keys:
- "qualification_score": integer 0-100
- "score_label": one of "Highly Qualified Lead", "Moderately Qualified Lead", "Low Priority Lead"
- "business_needs": 1-2 sentence string describing likely current business needs
- "opportunities": 1-2 sentence string describing the sales opportunity
- "industry_analysis": 1-2 sentence string on industry/technology fit
- "reasoning": array of exactly 3 objects, each with "factor" (2-4 word title,
  e.g. "High Growth Potential", "Tech Alignment", "Decision Maker Access") and
  "detail" (1 sentence explanation), ordered by importance.
"""


def _call_llm_for_insight(prompt: str) -> dict:
    if _client is None:
        raise HTTPException(
            status_code=503,
            detail="LLM not configured. Set GROQ_API_KEY or OPENAI_API_KEY in your .env file.",
        )
    try:
        completion = _client.chat.completions.create(
            model=_model,
            messages=[
                {"role": "system", "content": "You are a precise assistant that only outputs valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
        )
        raw = completion.choices[0].message.content.strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(raw)

        data["qualification_score"] = max(0, min(100, int(data["qualification_score"])))
        if data["score_label"] not in ("Highly Qualified Lead", "Moderately Qualified Lead", "Low Priority Lead"):
            score = data["qualification_score"]
            data["score_label"] = (
                "Highly Qualified Lead" if score >= 75
                else "Moderately Qualified Lead" if score >= 45
                else "Low Priority Lead"
            )
        return data
    except json.JSONDecodeError:
        logger.error(f"LLM returned non-JSON: {raw!r}")
        raise HTTPException(status_code=502, detail="AI returned an unexpected format. Please try again.")
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise HTTPException(status_code=502, detail=f"AI generation failed: {e}")


# --------------------------------------------------------------------------
# ROUTES
# --------------------------------------------------------------------------
@router.get("/health")
def health():
    return {"status": "ok", "llm_configured": _client is not None}


@router.post("/generate/{lead_id}", response_model=InsightOut)
def generate_insight(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    prompt = _build_prompt(lead)
    data = _call_llm_for_insight(prompt)

    insight = CompanyInsight(
        lead_id=lead_id,
        qualification_score=data["qualification_score"],
        score_label=data["score_label"],
        business_needs=data.get("business_needs"),
        opportunities=data.get("opportunities"),
        industry_analysis=data.get("industry_analysis"),
        reasoning=data.get("reasoning"),
    )
    db.add(insight)
    db.commit()
    db.refresh(insight)
    return insight


@router.get("/{lead_id}", response_model=InsightOut)
def get_latest_insight(lead_id: int, db: Session = Depends(get_db)):
    insight = (
        db.query(CompanyInsight)
        .filter(CompanyInsight.lead_id == lead_id)
        .order_by(CompanyInsight.generated_at.desc())
        .first()
    )
    if not insight:
        raise HTTPException(status_code=404, detail="No insight generated yet for this lead.")
    return insight


@router.get("/{lead_id}/history", response_model=List[InsightOut])
def get_insight_history(lead_id: int, db: Session = Depends(get_db)):
    return (
        db.query(CompanyInsight)
        .filter(CompanyInsight.lead_id == lead_id)
        .order_by(CompanyInsight.generated_at.desc())
        .all()
    )