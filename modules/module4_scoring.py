"""
modules/module4_scoring.py
Module 4 - Lead Scoring & Recommendation Engine

Calculates a priority score (0-100), classifies the lead, generates
AI-driven recommendations using Groq/OpenAI, ranks leads, and provides
real-time simulation capabilities for What-If analysis.
"""

import os
import json
import logging
from typing import Optional, List, Dict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc
from dotenv import load_dotenv

from database.connection import get_db
from database.models import Lead, CompanyInsight, OutreachCampaign, SalesInteraction, LeadScore

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("module4_scoring")

router = APIRouter()

# --------------------------------------------------------------------------
# LLM CLIENT SETUP
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
        logger.info(f"Module 4 using Groq ({_model})")
    except Exception as e:
        logger.warning(f"Could not init Groq client: {e}")
elif OPENAI_API_KEY:
    try:
        from openai import OpenAI
        _client = OpenAI(api_key=OPENAI_API_KEY)
        _model = OPENAI_MODEL
        logger.info(f"Module 4 using OpenAI ({_model})")
    except Exception as e:
        logger.warning(f"Could not init OpenAI client: {e}")


# --------------------------------------------------------------------------
# SCHEMAS
# --------------------------------------------------------------------------
class ScoreOut(BaseModel):
    lead_id: int
    score: int
    classification: str
    explanation: Dict[str, float]
    recommendations: str
    confidence_score: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ScoreSimulateRequest(BaseModel):
    lead_id: int
    company_size: Optional[str] = None
    annual_revenue: Optional[str] = None
    funding_stage: Optional[str] = None
    industry: Optional[str] = None
    hiring_trend: Optional[str] = None
    website_engagement: Optional[str] = None
    email_open_rate: Optional[str] = None
    email_reply: Optional[str] = None
    linkedin_engagement: Optional[str] = None
    recent_news: Optional[str] = None
    demo_booked: Optional[bool] = None


class RankOut(BaseModel):
    lead_id: int
    company_name: str
    industry: Optional[str] = None
    lead_status: Optional[str] = None
    score: int
    classification: str


# --------------------------------------------------------------------------
# SCORING ALGORITHM HELPERS
# --------------------------------------------------------------------------
def parse_company_size(size_str: Optional[str]) -> int:
    if not size_str:
        return 0
    s = size_str.lower()
    if ">1000" in s or "1000+" in s or "500-1000" in s:
        return 15
    elif "250-500" in s:
        return 12
    elif "100-250" in s:
        return 9
    elif "50-100" in s:
        return 6
    elif "10-50" in s or "10-25" in s:
        return 3
    return 1


def parse_annual_revenue(rev_str: Optional[str]) -> int:
    if not rev_str:
        return 1
    r = rev_str.lower()
    if "b" in r or "80m" in r or "100m" in r or "120m" in r or "60m" in r or "50m" in r:
        return 15
    elif "10m" in r or "12m" in r or "15m" in r or "20m" in r or "45m" in r:
        return 12
    elif "5m" in r or "8m" in r:
        return 9
    elif "1m" in r or "2m" in r or "3m" in r:
        return 4
    return 1


def parse_funding_stage(fund_str: Optional[str]) -> int:
    if not fund_str:
        return 1
    f = fund_str.lower()
    if "series c" in f or "series d" in f or "series e" in f or "late" in f:
        return 10
    elif "series a" in f or "series b" in f:
        return 8
    elif "seed" in f:
        return 4
    return 1


def parse_industry_match(ind_str: Optional[str]) -> int:
    if not ind_str:
        return 3
    i = ind_str.lower()
    tech_industries = ["enterprise software", "artificial intelligence", "saas", "cloud infrastructure", "data infrastructure"]
    if any(ti in i for ti in tech_industries):
        return 15
    elif "tech" in i or "software" in i or "ai" in i or "infrastructure" in i:
        return 12
    elif "healthcare" in i or "finance" in i or "retail" in i or "e-commerce" in i:
        return 8
    return 3


def calculate_lead_score(
    lead: Lead,
    insight: Optional[CompanyInsight],
    campaigns: List[OutreachCampaign],
    interactions: List[SalesInteraction],
    overrides: Optional[dict] = None
) -> tuple[int, dict]:
    overrides = overrides or {}

    size_val = overrides.get("company_size") or lead.company_size
    score_size = parse_company_size(size_val)

    rev_val = overrides.get("annual_revenue") or lead.annual_revenue
    score_rev = parse_annual_revenue(rev_val)

    fund_val = overrides.get("funding_stage") or lead.funding_stage
    score_funding = parse_funding_stage(fund_val)

    hiring_override = overrides.get("hiring_trend")
    if hiring_override is not None:
        if hiring_override == "Growing":
            score_hiring = 10
        elif hiring_override == "Stable":
            score_hiring = 6
        else:
            score_hiring = 2
    else:
        has_hiring = False
        if insight:
            text = f"{insight.business_needs or ''} {insight.opportunities or ''} {insight.industry_analysis or ''}".lower()
            if any(w in text for w in ["hiring", "openings", "expanding", "growth"]):
                has_hiring = True

        if has_hiring:
            score_hiring = 10
        elif lead.funding_stage and any(x in lead.funding_stage.lower() for x in ["series", "seed"]):
            score_hiring = 7
        else:
            score_hiring = 3

    ind_val = overrides.get("industry") or lead.industry
    score_industry = parse_industry_match(ind_val)

    web_override = overrides.get("website_engagement")
    if web_override is not None:
        if web_override == "High":
            score_website = 10
        elif web_override == "Medium":
            score_website = 6
        else:
            score_website = 2
    else:
        visits = [i for i in interactions if i.interaction_type and i.interaction_type.lower() in ["website", "visit", "website visit"]]
        if len(visits) >= 5:
            score_website = 10
        elif len(visits) >= 1:
            score_website = 6
        else:
            score_website = 3

    email_open_override = overrides.get("email_open_rate")
    if email_open_override is not None:
        if email_open_override == "Opened":
            score_email_open = 10
        elif email_open_override == "Sent but Not Opened":
            score_email_open = 5
        else:
            score_email_open = 0
    else:
        has_sent = any(c.campaign_status == "sent" for c in campaigns)
        has_opened = any(i.interaction_type and i.interaction_type.lower() in ["email opened", "open", "email open"] for i in interactions)
        if has_opened:
            score_email_open = 10
        elif has_sent:
            score_email_open = 5
        else:
            score_email_open = 0

    email_reply_override = overrides.get("email_reply")
    if email_reply_override is not None:
        score_email_reply = 10 if email_reply_override == "Replied" else 0
    else:
        has_replied = any(i.interaction_type and i.interaction_type.lower() in ["email reply", "reply received", "reply"] for i in interactions)
        score_email_reply = 10 if has_replied else 0

    li_override = overrides.get("linkedin_engagement")
    if li_override is not None:
        score_linkedin = 5 if li_override == "Engaged" else 0
    else:
        has_li = any(i.interaction_type and "linkedin" in i.interaction_type.lower() for i in interactions)
        score_linkedin = 5 if has_li else 0

    news_override = overrides.get("recent_news")
    if news_override is not None:
        score_news = 10 if news_override == "Positive News" else 3
    else:
        score_news = 10 if insight else 3

    base_score = (
        score_size + score_rev + score_funding + score_hiring + score_industry +
        score_website + score_email_open + score_email_reply + score_linkedin + score_news
    )

    demo_val = overrides.get("demo_booked")
    if demo_val is None:
        demo_val = any(i.interaction_type and ("demo" in i.interaction_type.lower() or "meeting" in i.interaction_type.lower()) for i in interactions)

    booster = 15 if demo_val else 0
    final_score = min(100, base_score + booster)

    explanation = {
        "Company Size (Max 15)": score_size,
        "Annual Revenue (Max 15)": score_rev,
        "Funding Stage (Max 10)": score_funding,
        "Hiring Trend (Max 10)": score_hiring,
        "Industry Match (Max 15)": score_industry,
        "Website Engagement (Max 10)": score_website,
        "Email Open Rate (Max 10)": score_email_open,
        "Email Reply (Max 10)": score_email_reply,
        "LinkedIn Engagement (Max 5)": score_linkedin,
        "Recent News (Max 10)": score_news,
        "Demo Booked Booster (+15)": booster
    }

    return final_score, explanation


def get_classification_label(score: int) -> str:
    if score >= 90:
        return "Platinum"
    elif score >= 80:
        return "Gold"
    elif score >= 65:
        return "Silver"
    elif score >= 45:
        return "Bronze"
    return "Low Priority"


def calculate_data_confidence(lead: Lead, insight: Optional[CompanyInsight], interactions: List[SalesInteraction]) -> int:
    score = 0
    if lead.company_size:
        score += 15
    if lead.annual_revenue:
        score += 15
    if lead.funding_stage:
        score += 15
    if lead.tech_stack and len(lead.tech_stack) > 0:
        score += 15
    if insight:
        score += 20
    if len(interactions) > 0:
        score += 20
    return min(100, score)


# --------------------------------------------------------------------------
# AI NEXT STEPS / RECOMMENDATION GENERATION
# --------------------------------------------------------------------------
def generate_ai_recommendation(
    lead: Lead,
    score: int,
    classification: str,
    explanation: dict,
    insight: Optional[CompanyInsight],
    interactions: List[SalesInteraction]
) -> str:
    if _client is None:
        if score >= 90:
            return (
                "### Next Steps:\n"
                "- 📞 **Schedule a Product Demo** immediately (within 24-48 hours).\n"
                "- 💼 Assign this lead to a **Senior Account Executive**.\n"
                "- 💡 Highlight enterprise scalability and security integrations.\n"
                "- 🏢 Offer a personalized custom pricing model."
            )
        elif score >= 80:
            return (
                "### Next Steps:\n"
                "- ✉️ **Send a follow-up email** with a client case study or testimonial.\n"
                "- 🔍 Pitch core technical benefits aligning with their tech stack.\n"
                "- 👥 Introduce key technical stakeholders."
            )
        elif score >= 65:
            return (
                "### Next Steps:\n"
                "- 📝 Add this lead to a semi-automated outreach campaign.\n"
                "- 🔗 Connect with their team on LinkedIn and share tech blogs."
            )
        else:
            return (
                "### Next Steps:\n"
                "- 📥 Add this lead to the **marketing nurture newsletter**.\n"
                "- 📅 Re-evaluate automatically in 30 days."
            )

    stack = ", ".join(lead.tech_stack) if lead.tech_stack else "Unknown"
    needs = insight.business_needs if insight else "Unknown"
    opps = insight.opportunities if insight else "Unknown"
    recent_actions = "\n".join([f"- {i.interaction_type}: {i.summary}" for i in interactions[:3]]) if interactions else "None"

    prompt = f"""You are an elite AI B2B Sales Advisor. Your goal is to analyze a prospect and generate a specific, highly actionable list of recommendations / next steps for the sales team.

Prospect Profile:
- Company Name: {lead.company_name}
- Industry: {lead.industry or "Unknown"}
- Company Size: {lead.company_size or "Unknown"}
- Revenue: {lead.annual_revenue or "Unknown"}
- Funding Stage: {lead.funding_stage or "Unknown"}
- Tech Stack: {stack}
- Business Needs: {needs}
- Opportunity: {opps}
- Lead Score: {score} / 100 ({classification})
- Recent Interactions:
{recent_actions}

Detailed score breakdown:
{json.dumps(explanation, indent=2)}

Please write exactly 3-5 specific, bulleted recommendations.
Rules:
1. Do NOT use generic advice. Tailor it to their industry, tech stack, and funding/size.
2. Be direct and tactical (e.g. "Draft an email targeting the CTO pointing out how they can optimize their AWS PostgreSQL infrastructure", "Assign to Enterprise Account Executive").
3. Make sure to specify the tone and the direct value proposition they care about.
4. Output your response in markdown format with bullet points.
"""

    try:
        completion = _client.chat.completions.create(
            model=_model,
            messages=[
                {"role": "system", "content": "You are a direct, professional sales strategist AI."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=400
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Failed to generate recommendation from LLM: {e}")
        return f"AI generation failed ({e}). Recommended strategy based on score {score}: Focus on product fit and trigger an outreach."


# --------------------------------------------------------------------------
# ROUTES
# --------------------------------------------------------------------------
@router.get("/status")
def status():
    return {"module": "4 - Lead Scoring & Recommendations", "status": "fully operational"}


@router.post("/generate/{lead_id}", response_model=ScoreOut)
def generate_lead_score_endpoint(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    insight = db.query(CompanyInsight).filter(CompanyInsight.lead_id == lead_id).order_by(desc(CompanyInsight.generated_at)).first()
    campaigns = db.query(OutreachCampaign).filter(OutreachCampaign.lead_id == lead_id).all()
    interactions = db.query(SalesInteraction).filter(SalesInteraction.lead_id == lead_id).all()

    score, explanation = calculate_lead_score(lead, insight, campaigns, interactions)
    classification = get_classification_label(score)
    confidence = calculate_data_confidence(lead, insight, interactions)

    recommendations = generate_ai_recommendation(lead, score, classification, explanation, insight, interactions)

    score_rec = db.query(LeadScore).filter(LeadScore.lead_id == lead_id).first()
    if not score_rec:
        score_rec = LeadScore(lead_id=lead_id)
        db.add(score_rec)

    score_rec.score = score
    score_rec.classification = classification
    score_rec.explanation = explanation
    score_rec.recommendations = recommendations
    score_rec.confidence_score = confidence
    score_rec.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(score_rec)

    return score_rec


@router.get("/{lead_id}", response_model=ScoreOut)
def get_lead_score_endpoint(lead_id: int, db: Session = Depends(get_db)):
    score_rec = db.query(LeadScore).filter(LeadScore.lead_id == lead_id).first()
    if not score_rec:
        return generate_lead_score_endpoint(lead_id, db)
    return score_rec


@router.post("/simulate", response_model=ScoreOut)
def simulate_lead_score_endpoint(req: ScoreSimulateRequest, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.lead_id == req.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    insight = db.query(CompanyInsight).filter(CompanyInsight.lead_id == req.lead_id).order_by(desc(CompanyInsight.generated_at)).first()
    campaigns = db.query(OutreachCampaign).filter(OutreachCampaign.lead_id == req.lead_id).all()
    interactions = db.query(SalesInteraction).filter(SalesInteraction.lead_id == req.lead_id).all()

    overrides = {}
    if req.company_size is not None:
        overrides["company_size"] = req.company_size
    if req.annual_revenue is not None:
        overrides["annual_revenue"] = req.annual_revenue
    if req.funding_stage is not None:
        overrides["funding_stage"] = req.funding_stage
    if req.industry is not None:
        overrides["industry"] = req.industry
    if req.hiring_trend is not None:
        overrides["hiring_trend"] = req.hiring_trend
    if req.website_engagement is not None:
        overrides["website_engagement"] = req.website_engagement
    if req.email_open_rate is not None:
        overrides["email_open_rate"] = req.email_open_rate
    if req.email_reply is not None:
        overrides["email_reply"] = req.email_reply
    if req.linkedin_engagement is not None:
        overrides["linkedin_engagement"] = req.linkedin_engagement
    if req.recent_news is not None:
        overrides["recent_news"] = req.recent_news
    if req.demo_booked is not None:
        overrides["demo_booked"] = req.demo_booked

    score, explanation = calculate_lead_score(lead, insight, campaigns, interactions, overrides)
    classification = get_classification_label(score)
    confidence = calculate_data_confidence(lead, insight, interactions)

    recommendations = generate_ai_recommendation(lead, score, classification, explanation, insight, interactions)

    simulated = ScoreOut(
        lead_id=req.lead_id,
        score=score,
        classification=classification,
        explanation=explanation,
        recommendations=recommendations,
        confidence_score=confidence,
        updated_at=datetime.utcnow()
    )

    return simulated


@router.get("/ranking/list", response_model=List[RankOut])
def get_ranked_leads_endpoint(db: Session = Depends(get_db)):
    leads = db.query(Lead).all()
    results = []

    for l in leads:
        score_rec = db.query(LeadScore).filter(LeadScore.lead_id == l.lead_id).first()
        if not score_rec:
            try:
                insight = db.query(CompanyInsight).filter(CompanyInsight.lead_id == l.lead_id).order_by(desc(CompanyInsight.generated_at)).first()
                campaigns = db.query(OutreachCampaign).filter(OutreachCampaign.lead_id == l.lead_id).all()
                interactions = db.query(SalesInteraction).filter(SalesInteraction.lead_id == l.lead_id).all()
                score, explanation = calculate_lead_score(l, insight, campaigns, interactions)
                classification = get_classification_label(score)
            except Exception:
                score = 0
                classification = "Low Priority"
        else:
            score = score_rec.score
            classification = score_rec.classification

        results.append(RankOut(
            lead_id=l.lead_id,
            company_name=l.company_name,
            industry=l.industry,
            lead_status=l.lead_status,
            score=score,
            classification=classification
        ))

    results.sort(key=lambda x: x.score, reverse=True)
    return results