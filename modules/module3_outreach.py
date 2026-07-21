"""
modules/module3_outreach.py
Module 3 - AI Outreach Generation

Generates personalized cold emails and follow-up emails for a lead using
an LLM, based on that lead's stored company profile + (if available)
Module 2's company_insights. Saves generated emails as "campaigns" and
lets you fetch outreach history per lead.

Exposes a FastAPI router that main.py includes with:
    from modules.module3_outreach import router as outreach_router
    app.include_router(outreach_router, prefix="/outreach", tags=["Outreach"])
"""

import os
import json
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Lead, CompanyInsight, OutreachCampaign

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("module3_outreach")

router = APIRouter()

# --------------------------------------------------------------------------
# LLM CLIENT SETUP — supports Groq (OpenAI-compatible API) or real OpenAI.
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
        logger.info(f"Module 3 using Groq ({_model})")
    except Exception as e:  # pragma: no cover
        logger.warning(f"Could not init Groq client: {e}")
elif OPENAI_API_KEY:
    try:
        from openai import OpenAI
        _client = OpenAI(api_key=OPENAI_API_KEY)
        _model = OPENAI_MODEL
        logger.info(f"Module 3 using OpenAI ({_model})")
    except Exception as e:  # pragma: no cover
        logger.warning(f"Could not init OpenAI client: {e}")


# --------------------------------------------------------------------------
# SCHEMAS
# --------------------------------------------------------------------------
class GenerateRequest(BaseModel):
    lead_id: int
    email_type: str = "cold_email"   # "cold_email" | "follow_up"
    tone: str = "professional"       # professional | friendly | direct | consultative
    extra_context: Optional[str] = None  # e.g. "mention their recent funding round"


class GenerateResponse(BaseModel):
    subject: str
    body: str


class SaveCampaignRequest(BaseModel):
    lead_id: int
    email_type: str
    tone: str
    subject: str
    body: str
    status: str = "draft"  # draft | sent


class CampaignOut(BaseModel):
    campaign_id: int
    lead_id: int
    email_type: str
    tone: str
    email_subject: str
    email_content: str
    campaign_status: str

    class Config:
        from_attributes = True


# --------------------------------------------------------------------------
# HELPERS
# --------------------------------------------------------------------------
def _build_prompt(lead: Lead, insight: Optional[CompanyInsight], req: GenerateRequest) -> str:
    kind = "a cold outreach email" if req.email_type == "cold_email" else \
           "a short, polite follow-up email to a prospect who has gone quiet"

    profile_lines = [
        f"Company: {lead.company_name}",
        f"Industry: {lead.industry or 'Unknown'}",
        f"Contact: {lead.contact_name or 'Unknown'} ({lead.title or 'Unknown title'})",
        f"Company size: {lead.company_size or 'Unknown'}",
        f"Location: {lead.location or 'Unknown'}",
        f"Funding stage: {lead.funding_stage or 'Unknown'}",
        f"Tech stack: {', '.join(lead.tech_stack) if lead.tech_stack else 'Unknown'}",
    ]

    if insight:
        profile_lines.append(f"Qualification score: {insight.qualification_score} ({insight.score_label})")
        if insight.business_needs:
            profile_lines.append(f"Known business needs: {insight.business_needs}")
        if insight.opportunities:
            profile_lines.append(f"Known opportunities: {insight.opportunities}")

    if req.extra_context:
        profile_lines.append(f"Additional context to weave in: {req.extra_context}")

    prompt = f"""You are an expert B2B sales copywriter. Write {kind}.

Tone: {req.tone}

Prospect profile:
{chr(10).join('- ' + l for l in profile_lines)}

Rules:
- Keep it under 150 words.
- Make it specific to this company, not generic.
- One clear call to action at the end.
- Do NOT use placeholder brackets like [Your Name] — sign off as "The SalesGenie Team".
- Return ONLY valid JSON, no markdown fences, with exactly two keys: "subject" and "body".
"""
    return prompt


def _call_llm(prompt: str) -> GenerateResponse:
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
            temperature=0.7,
        )
        raw = completion.choices[0].message.content.strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(raw)
        return GenerateResponse(subject=data["subject"], body=data["body"])
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


@router.post("/generate", response_model=GenerateResponse)
def generate_outreach(req: GenerateRequest, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.lead_id == req.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    try:
        insight = (
            db.query(CompanyInsight)
            .filter(CompanyInsight.lead_id == req.lead_id)
            .order_by(CompanyInsight.generated_at.desc())
            .first()
        )
    except Exception as e:
        logger.warning(f"Could not fetch company_insights for lead {req.lead_id}: {e}")
        db.rollback()
        insight = None

    prompt = _build_prompt(lead, insight, req)
    return _call_llm(prompt)


@router.post("/save", response_model=CampaignOut)
def save_campaign(req: SaveCampaignRequest, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.lead_id == req.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    campaign = OutreachCampaign(
        lead_id=req.lead_id,
        email_type=req.email_type,
        tone=req.tone,
        email_subject=req.subject,
        email_content=req.body,
        campaign_status=req.status,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.get("/history/{lead_id}", response_model=List[CampaignOut])
def outreach_history(lead_id: int, db: Session = Depends(get_db)):
    return (
        db.query(OutreachCampaign)
        .filter(OutreachCampaign.lead_id == lead_id)
        .order_by(OutreachCampaign.created_at.desc())
        .all()
    )


@router.patch("/mark-sent/{campaign_id}", response_model=CampaignOut)
def mark_sent(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.query(OutreachCampaign).filter(OutreachCampaign.campaign_id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    campaign.campaign_status = "sent"
    db.commit()
    db.refresh(campaign)
    return campaign