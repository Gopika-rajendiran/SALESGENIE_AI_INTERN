"""
modules/module1_leads.py
Module 1 - Lead Management & Prospect Database

Full CRUD for leads (prospects), plus basic engagement-history logging
(sales_interactions). This is the source of truth all other modules
(2, 3, 4, 5, 6) read from.

Mounted in main.py as:
    app.include_router(leads_router, prefix="/leads", tags=["Module 1 - Leads"])
"""

from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database.connection import get_db
from database.models import Lead, SalesInteraction

router = APIRouter()


# --------------------------------------------------------------------------
# SCHEMAS
# --------------------------------------------------------------------------
class LeadCreate(BaseModel):
    company_name: str
    industry: Optional[str] = None
    contact_name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company_size: Optional[str] = None
    annual_revenue: Optional[str] = None
    location: Optional[str] = None
    funding_stage: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    lead_status: str = "New"
    segment: Optional[str] = None  # Enterprise / Mid-Market / Startup


class LeadUpdate(BaseModel):
    company_name: Optional[str] = None
    industry: Optional[str] = None
    contact_name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company_size: Optional[str] = None
    annual_revenue: Optional[str] = None
    location: Optional[str] = None
    funding_stage: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    lead_status: Optional[str] = None
    segment: Optional[str] = None


class LeadOut(BaseModel):
    lead_id: int
    company_name: str
    industry: Optional[str] = None
    contact_name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company_size: Optional[str] = None
    annual_revenue: Optional[str] = None
    location: Optional[str] = None
    funding_stage: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    lead_status: Optional[str] = None
    segment: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InteractionCreate(BaseModel):
    interaction_type: str  # Call / Email / Meeting / Note
    summary: Optional[str] = None
    action_items: Optional[str] = None


class InteractionOut(BaseModel):
    interaction_id: int
    lead_id: int
    interaction_type: str
    summary: Optional[str] = None
    action_items: Optional[str] = None
    interaction_date: Optional[datetime] = None

    class Config:
        from_attributes = True


LEAD_STAGES = ["New", "Contacted", "Qualified", "Proposal", "Negotiation", "Closed Won", "Closed Lost"]


# --------------------------------------------------------------------------
# LEAD CRUD ROUTES
# --------------------------------------------------------------------------
@router.get("/stages")
def get_stages():
    """Lifecycle stages the frontend can render as a dropdown."""
    return {"stages": LEAD_STAGES}


@router.post("", response_model=LeadOut)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)):
    lead = Lead(**payload.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.get("", response_model=List[LeadOut])
def list_leads(
    q: Optional[str] = Query(None, description="Search by company, contact, or industry"),
    status: Optional[str] = Query(None, description="Filter by lead_status"),
    segment: Optional[str] = Query(None, description="Filter by segment"),
    db: Session = Depends(get_db),
):
    query = db.query(Lead)

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Lead.company_name.ilike(like),
                Lead.contact_name.ilike(like),
                Lead.industry.ilike(like),
            )
        )
    if status:
        query = query.filter(Lead.lead_status == status)
    if segment:
        query = query.filter(Lead.segment == segment)

    return query.order_by(Lead.created_at.desc()).all()


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return lead


@router.put("/{lead_id}", response_model=LeadOut)
def update_lead(lead_id: int, payload: LeadUpdate, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(lead, field, value)
    lead.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(lead)
    return lead


@router.delete("/{lead_id}")
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")
    db.delete(lead)
    db.commit()
    return {"message": f"Lead {lead_id} deleted."}


# --------------------------------------------------------------------------
# ENGAGEMENT HISTORY (sales_interactions)
# --------------------------------------------------------------------------
@router.post("/{lead_id}/interactions", response_model=InteractionOut)
def log_interaction(lead_id: int, payload: InteractionCreate, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    interaction = SalesInteraction(lead_id=lead_id, **payload.model_dump())
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return interaction


@router.get("/{lead_id}/interactions", response_model=List[InteractionOut])
def list_interactions(lead_id: int, db: Session = Depends(get_db)):
    return (
        db.query(SalesInteraction)
        .filter(SalesInteraction.lead_id == lead_id)
        .order_by(SalesInteraction.interaction_date.desc())
        .all()
    )
