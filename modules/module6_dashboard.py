"""
modules/module6_dashboard.py
Module 6 - Dashboard & Analytics

Aggregates data from all existing tables and surfaces KPI metrics,
pipeline funnel data, scoring distributions, outreach stats, top leads,
and an activity timeline — all consumed by the Streamlit Dashboard page.

Routes
------
GET /dashboard/status                — health check
GET /dashboard/summary               — top-level KPIs
GET /dashboard/pipeline              — leads per pipeline stage
GET /dashboard/scoring-distribution  — score tier breakdown
GET /dashboard/outreach-stats        — campaign counters
GET /dashboard/top-leads             — top 5 leads by score
GET /dashboard/activity-timeline     — recent interactions (last N)
"""

import logging
from collections import Counter
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from database.connection import get_db
from database.models import Lead, CompanyInsight, OutreachCampaign, SalesInteraction, LeadScore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("module6_dashboard")

router = APIRouter()


# --------------------------------------------------------------------------
# ROUTES
# --------------------------------------------------------------------------
@router.get("/status")
def status():
    return {"module": "6 - Dashboard & Analytics", "status": "fully operational"}


@router.get("/summary")
def get_summary(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    High-level KPIs:
      - total_leads
      - leads_by_status  (dict)
      - leads_by_segment (dict)
      - leads_by_industry (list of {industry, count} top-10)
      - scored_leads      (how many have a LeadScore record)
      - avg_score         (average score across scored leads)
      - total_campaigns   (outreach campaigns)
      - total_interactions
    """
    leads = db.query(Lead).all()
    total_leads = len(leads)

    # by status
    leads_by_status = dict(Counter(l.lead_status or "Unknown" for l in leads))

    # by segment
    leads_by_segment = dict(Counter(l.segment or "Unknown" for l in leads))

    # by industry — top 10
    industry_counter = Counter(l.industry or "Unknown" for l in leads)
    leads_by_industry = [
        {"industry": ind, "count": cnt}
        for ind, cnt in industry_counter.most_common(10)
    ]

    # scoring stats
    score_records = db.query(LeadScore).all()
    scored_leads = len(score_records)
    avg_score = (
        round(sum(s.score for s in score_records) / scored_leads, 1)
        if scored_leads else 0
    )

    total_campaigns    = db.query(func.count(OutreachCampaign.campaign_id)).scalar() or 0
    total_interactions = db.query(func.count(SalesInteraction.interaction_id)).scalar() or 0

    return {
        "total_leads":         total_leads,
        "leads_by_status":     leads_by_status,
        "leads_by_segment":    leads_by_segment,
        "leads_by_industry":   leads_by_industry,
        "scored_leads":        scored_leads,
        "avg_score":           avg_score,
        "total_campaigns":     total_campaigns,
        "total_interactions":  total_interactions,
    }


@router.get("/pipeline")
def get_pipeline(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    Returns an ordered list of pipeline stages with lead counts.
    Ordered by the canonical sales funnel sequence.
    """
    canonical_stages = [
        "New", "Contacted", "Qualified",
        "Proposal", "Negotiation", "Closed Won", "Closed Lost",
    ]

    leads = db.query(Lead).all()
    stage_counter = Counter(l.lead_status or "New" for l in leads)

    results = []
    seen = set()

    # canonical order first
    for stage in canonical_stages:
        results.append({"stage": stage, "count": stage_counter.get(stage, 0)})
        seen.add(stage)

    # any non-canonical stages found in DB
    for stage, count in stage_counter.items():
        if stage not in seen:
            results.append({"stage": stage, "count": count})

    return results


@router.get("/scoring-distribution")
def get_scoring_distribution(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Returns score-tier breakdown and a histogram of raw scores in 10-point buckets.
    """
    score_records = db.query(LeadScore).all()

    tiers = {"Platinum": 0, "Gold": 0, "Silver": 0, "Bronze": 0, "Low Priority": 0}
    buckets: Dict[str, int] = {}

    for rec in score_records:
        tier = rec.classification or "Low Priority"
        if tier in tiers:
            tiers[tier] += 1
        else:
            tiers[tier] = tiers.get(tier, 0) + 1

        # 10-point histogram bucket
        bucket_label = f"{(rec.score // 10) * 10}-{(rec.score // 10) * 10 + 9}"
        buckets[bucket_label] = buckets.get(bucket_label, 0) + 1

    return {
        "total_scored": len(score_records),
        "tier_breakdown": tiers,
        "score_histogram": [
            {"range": k, "count": v}
            for k, v in sorted(buckets.items())
        ],
    }


@router.get("/outreach-stats")
def get_outreach_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Returns outreach campaign counters: total, sent, draft, by type.
    """
    campaigns = db.query(OutreachCampaign).all()

    total  = len(campaigns)
    sent   = sum(1 for c in campaigns if c.campaign_status == "sent")
    draft  = sum(1 for c in campaigns if c.campaign_status == "draft")

    by_type = dict(Counter(c.email_type or "unknown" for c in campaigns))
    by_tone = dict(Counter(c.tone or "unknown" for c in campaigns))

    # leads that received at least one campaign
    reached_leads = len({c.lead_id for c in campaigns})

    return {
        "total":         total,
        "sent":          sent,
        "draft":         draft,
        "by_type":       by_type,
        "by_tone":       by_tone,
        "reached_leads": reached_leads,
    }


@router.get("/top-leads")
def get_top_leads(
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Returns up to `limit` leads ordered by their LeadScore descending.
    Leads without a score record are excluded.
    """
    rows = (
        db.query(LeadScore, Lead)
        .join(Lead, Lead.lead_id == LeadScore.lead_id)
        .order_by(desc(LeadScore.score))
        .limit(limit)
        .all()
    )

    return [
        {
            "lead_id":        lead.lead_id,
            "company_name":   lead.company_name,
            "industry":       lead.industry,
            "segment":        lead.segment,
            "lead_status":    lead.lead_status,
            "score":          score_rec.score,
            "classification": score_rec.classification,
            "confidence":     score_rec.confidence_score,
        }
        for score_rec, lead in rows
    ]


@router.get("/activity-timeline")
def get_activity_timeline(
    limit: int = Query(default=15, ge=1, le=50),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Returns the most recent `limit` sales interactions across all leads,
    enriched with the company name.
    """
    rows = (
        db.query(SalesInteraction, Lead)
        .join(Lead, Lead.lead_id == SalesInteraction.lead_id)
        .order_by(desc(SalesInteraction.interaction_date))
        .limit(limit)
        .all()
    )

    return [
        {
            "interaction_id":   interaction.interaction_id,
            "lead_id":          interaction.lead_id,
            "company_name":     lead.company_name,
            "interaction_type": interaction.interaction_type,
            "summary":          interaction.summary,
            "action_items":     interaction.action_items,
            "interaction_date": (
                interaction.interaction_date.isoformat()
                if interaction.interaction_date else None
            ),
        }
        for interaction, lead in rows
    ]
