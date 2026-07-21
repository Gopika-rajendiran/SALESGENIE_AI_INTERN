"""
database/models.py
Shared ORM models for SalesGenie AI.

NOTE for team: if module1/module2 teammates already created a models.py with
Lead / CompanyInsight classes, MERGE this file with theirs rather than
overwriting — keep column names identical so foreign keys line up. This file
adds OutreachCampaign (new, for Module 3) and includes the others so
Module 3 can run standalone if needed.
"""

from sqlalchemy import (
    Column, Integer, String, Text, TIMESTAMP, ForeignKey, ARRAY, func
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from database.connection import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    role = Column(String(50))
    department = Column(String(100))
    created_at = Column(TIMESTAMP, server_default=func.now())


class Lead(Base):
    __tablename__ = "leads"

    lead_id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(200), nullable=False)
    industry = Column(String(100))
    contact_name = Column(String(150))
    title = Column(String(100))
    email = Column(String(150))
    phone = Column(String(30))
    company_size = Column(String(50))
    annual_revenue = Column(String(50))
    location = Column(String(150))
    funding_stage = Column(String(50))
    tech_stack = Column(ARRAY(String))
    lead_status = Column(String(50), default="New")
    segment = Column(String(20))
    created_by = Column(Integer, ForeignKey("users.user_id"))
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now())

    insights = relationship("CompanyInsight", back_populates="lead")
    campaigns = relationship("OutreachCampaign", back_populates="lead")
    score_record = relationship("LeadScore", back_populates="lead", uselist=False, cascade="all, delete-orphan")


class CompanyInsight(Base):
    __tablename__ = "company_insights"

    insight_id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.lead_id", ondelete="CASCADE"))
    qualification_score = Column(Integer)
    score_label = Column(String(50))
    business_needs = Column(Text)
    opportunities = Column(Text)
    industry_analysis = Column(Text)
    reasoning = Column(JSONB)  # list of {"factor": str, "detail": str}
    generated_at = Column(TIMESTAMP, server_default=func.now())

    lead = relationship("Lead", back_populates="insights")


class OutreachCampaign(Base):
    """
    New table for Module 3 (matches 'Outreach_Campaigns' in the project's
    ER diagram: campaign_id PK, lead_id FK, email_subject, email_content,
    campaign_status, created_at).
    """
    __tablename__ = "outreach_campaigns"

    campaign_id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.lead_id", ondelete="CASCADE"))
    email_type = Column(String(30), default="cold_email")  # cold_email | follow_up
    tone = Column(String(30), default="professional")
    email_subject = Column(String(255))
    email_content = Column(Text)
    campaign_status = Column(String(30), default="draft")  # draft | sent
    created_at = Column(TIMESTAMP, server_default=func.now())

    lead = relationship("Lead", back_populates="campaigns")


class SalesInteraction(Base):
    __tablename__ = "sales_interactions"

    interaction_id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.lead_id", ondelete="CASCADE"))
    interaction_type = Column(String(50))
    summary = Column(Text)
    action_items = Column(Text)
    interaction_date = Column(TIMESTAMP, server_default=func.now())


class LeadScore(Base):
    __tablename__ = "lead_scores"

    score_id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.lead_id", ondelete="CASCADE"), unique=True)
    score = Column(Integer, nullable=False)
    classification = Column(String(50), nullable=False)
    explanation = Column(JSONB, nullable=False)  # JSON detailing points per feature
    recommendations = Column(Text, nullable=False)  # markdown AI recommendations
    confidence_score = Column(Integer, nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    lead = relationship("Lead", back_populates="score_record")
