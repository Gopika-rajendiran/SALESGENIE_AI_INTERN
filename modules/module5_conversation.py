"""
modules/module5_conversation.py
Module 5 - Conversation Intelligence & CRM

Provides full CRUD for SalesInteraction records and an AI-powered
conversation summarizer that distills a lead's entire interaction history
into a structured markdown digest.

Routes
------
GET  /conversation/status                  — health check
POST /conversation/log                     — log a new interaction
GET  /conversation/{lead_id}               — list all interactions for a lead
PUT  /conversation/{interaction_id}        — edit an existing interaction
DELETE /conversation/{interaction_id}      — delete an interaction
POST /conversation/summarize/{lead_id}     — AI summary of conversation history
"""

import os
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc
from dotenv import load_dotenv

from database.connection import get_db
from database.models import Lead, SalesInteraction

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("module5_conversation")

router = APIRouter()

# --------------------------------------------------------------------------
# LLM CLIENT SETUP  (Groq first, fallback to OpenAI)
# --------------------------------------------------------------------------
GROQ_API_KEY  = os.getenv("GROQ_API_KEY")
GROQ_MODEL    = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL  = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

_client = None
_model  = None

if GROQ_API_KEY:
    try:
        from openai import OpenAI
        _client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
        _model  = GROQ_MODEL
        logger.info(f"Module 5 using Groq ({_model})")
    except Exception as e:
        logger.warning(f"Could not init Groq client: {e}")
elif OPENAI_API_KEY:
    try:
        from openai import OpenAI
        _client = OpenAI(api_key=OPENAI_API_KEY)
        _model  = OPENAI_MODEL
        logger.info(f"Module 5 using OpenAI ({_model})")
    except Exception as e:
        logger.warning(f"Could not init OpenAI client: {e}")


# --------------------------------------------------------------------------
# SCHEMAS
# --------------------------------------------------------------------------
class InteractionCreate(BaseModel):
    lead_id: int
    interaction_type: str          # e.g. Call, Email, Meeting, Note
    summary: Optional[str] = None
    action_items: Optional[str] = None
    interaction_date: Optional[datetime] = None


class InteractionUpdate(BaseModel):
    interaction_type: Optional[str] = None
    summary: Optional[str] = None
    action_items: Optional[str] = None


class InteractionOut(BaseModel):
    interaction_id: int
    lead_id: int
    interaction_type: Optional[str] = None
    summary: Optional[str] = None
    action_items: Optional[str] = None
    interaction_date: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConversationSummaryOut(BaseModel):
    lead_id: int
    company_name: str
    total_interactions: int
    summary: str          # markdown AI digest
    generated_at: datetime


# --------------------------------------------------------------------------
# HELPERS
# --------------------------------------------------------------------------
INTERACTION_TYPES = ["Call", "Email", "Meeting", "Note", "Demo",
                     "LinkedIn", "Website Visit", "Email Reply", "Email Opened"]


def _build_summary_prompt(lead: Lead, interactions: List[SalesInteraction]) -> str:
    lines = []
    for i in interactions:
        date_str = i.interaction_date.strftime("%Y-%m-%d") if i.interaction_date else "unknown date"
        lines.append(
            f"- [{date_str}] {i.interaction_type or 'Unknown'}: "
            f"{i.summary or 'No summary.'}"
            + (f" | Action items: {i.action_items}" if i.action_items else "")
        )
    history_text = "\n".join(lines) if lines else "No interactions recorded."

    return f"""You are an elite B2B Sales Intelligence analyst.
Analyze the full conversation history below for the prospect '{lead.company_name}' (Industry: {lead.industry or 'Unknown'}, Stage: {lead.lead_status or 'Unknown'}).

Conversation History:
{history_text}

Write a concise, structured markdown summary (≤300 words) covering:
1. **Overall Engagement Level** — how engaged is this prospect?
2. **Key Discussion Topics** — what themes keep coming up?
3. **Pending Action Items** — what still needs to happen?
4. **Recommended Next Move** — the single most important next step the sales rep should take.

Be direct and use bullet points where helpful."""


def _fallback_summary(lead: Lead, interactions: List[SalesInteraction]) -> str:
    if not interactions:
        return (
            f"### Conversation Summary for {lead.company_name}\n\n"
            "No interactions have been logged yet.\n\n"
            "**Recommended Next Move:** Initiate first contact via a personalized cold email."
        )

    types = [i.interaction_type for i in interactions if i.interaction_type]
    type_counts: dict = {}
    for t in types:
        type_counts[t] = type_counts.get(t, 0) + 1

    breakdown = "\n".join([f"- {k}: {v}" for k, v in type_counts.items()])
    pending = [i.action_items for i in interactions if i.action_items]
    pending_text = "\n".join([f"- {a}" for a in pending[-3:]]) if pending else "- None recorded."

    return (
        f"### Conversation Summary for {lead.company_name}\n\n"
        f"**Total Interactions:** {len(interactions)}\n\n"
        f"**Interaction Breakdown:**\n{breakdown}\n\n"
        f"**Recent Action Items:**\n{pending_text}\n\n"
        "**Recommended Next Move:** Review the latest action items above and schedule a follow-up."
    )


# --------------------------------------------------------------------------
# ROUTES
# --------------------------------------------------------------------------
@router.get("/status")
def status():
    return {"module": "5 - Conversation Intelligence & CRM", "status": "fully operational"}


@router.post("/log", response_model=InteractionOut)
def log_interaction(payload: InteractionCreate, db: Session = Depends(get_db)):
    """Log a new sales interaction for a lead."""
    lead = db.query(Lead).filter(Lead.lead_id == payload.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    record = SalesInteraction(
        lead_id=payload.lead_id,
        interaction_type=payload.interaction_type,
        summary=payload.summary,
        action_items=payload.action_items,
        interaction_date=payload.interaction_date or datetime.utcnow(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    logger.info(f"Logged interaction {record.interaction_id} for lead {payload.lead_id}")
    return record


@router.get("/{lead_id}", response_model=List[InteractionOut])
def get_interactions(lead_id: int, db: Session = Depends(get_db)):
    """Return all interactions for a lead, newest first."""
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    return (
        db.query(SalesInteraction)
        .filter(SalesInteraction.lead_id == lead_id)
        .order_by(desc(SalesInteraction.interaction_date))
        .all()
    )


@router.put("/{interaction_id}", response_model=InteractionOut)
def update_interaction(
    interaction_id: int,
    payload: InteractionUpdate,
    db: Session = Depends(get_db),
):
    """Edit an existing interaction record."""
    record = db.query(SalesInteraction).filter(
        SalesInteraction.interaction_id == interaction_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Interaction not found.")

    if payload.interaction_type is not None:
        record.interaction_type = payload.interaction_type
    if payload.summary is not None:
        record.summary = payload.summary
    if payload.action_items is not None:
        record.action_items = payload.action_items

    db.commit()
    db.refresh(record)
    return record


@router.delete("/{interaction_id}")
def delete_interaction(interaction_id: int, db: Session = Depends(get_db)):
    """Delete an interaction record."""
    record = db.query(SalesInteraction).filter(
        SalesInteraction.interaction_id == interaction_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Interaction not found.")

    db.delete(record)
    db.commit()
    return {"message": f"Interaction {interaction_id} deleted."}


@router.post("/summarize/{lead_id}", response_model=ConversationSummaryOut)
def summarize_conversation(lead_id: int, db: Session = Depends(get_db)):
    """
    Generate an AI-powered markdown summary of all interactions for a lead.
    Falls back to a template summary when no LLM is configured.
    """
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    interactions = (
        db.query(SalesInteraction)
        .filter(SalesInteraction.lead_id == lead_id)
        .order_by(SalesInteraction.interaction_date)
        .all()
    )

    if _client is None:
        summary_text = _fallback_summary(lead, interactions)
    else:
        prompt = _build_summary_prompt(lead, interactions)
        try:
            completion = _client.chat.completions.create(
                model=_model,
                messages=[
                    {"role": "system", "content": "You are a concise, insightful B2B sales intelligence analyst."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.6,
                max_tokens=500,
            )
            summary_text = completion.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"LLM summarize failed: {e}")
            summary_text = _fallback_summary(lead, interactions)

    return ConversationSummaryOut(
        lead_id=lead_id,
        company_name=lead.company_name,
        total_interactions=len(interactions),
        summary=summary_text,
        generated_at=datetime.utcnow(),
    )
