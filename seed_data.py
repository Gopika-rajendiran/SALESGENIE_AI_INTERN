"""
seed_data.py
Inserts sample leads (+ optional insights) so you can demo Module 3
immediately, even before Module 1/2 have real data entry working.
Run with: python seed_data.py
"""

from database.connection import SessionLocal, init_db
from database.models import Lead, CompanyInsight

SAMPLE_LEADS = [
    dict(
        company_name="TechCorp Solutions", industry="Enterprise Software",
        contact_name="Sarah Johnson", title="CTO", email="sarah.johnson@techcorp.com",
        phone="555-0101", company_size="250-500 employees", annual_revenue="$45M - $60M",
        location="San Francisco, CA", funding_stage="Series C - $28M",
        tech_stack=["AWS", "Python", "React", "Node.js", "Kubernetes", "PostgreSQL"],
        lead_status="Qualified", segment="Enterprise",
    ),
    dict(
        company_name="InnovateAI Labs", industry="Artificial Intelligence",
        contact_name="Mark Chen", title="VP Sales", email="mark.chen@innovateai.com",
        phone="555-0102", company_size="50-100 employees", annual_revenue="$8M - $12M",
        location="Austin, TX", funding_stage="Series A - $10M",
        tech_stack=["GCP", "Python", "TensorFlow"],
        lead_status="Contacted", segment="Mid-Market",
    ),
    dict(
        company_name="DataFlow Systems", industry="Data Infrastructure",
        contact_name="Emily Davis", title="CEO", email="emily.davis@dataflow.io",
        phone="555-0103", company_size="10-25 employees", annual_revenue="$1M - $3M",
        location="Seattle, WA", funding_stage="Seed - $2M",
        tech_stack=["Azure", "Go", "Kafka"],
        lead_status="New", segment="Startup",
    ),
    dict(
        company_name="CloudScale Inc.", industry="Cloud Infrastructure",
        contact_name="Robert Lee", title="Head of IT", email="robert.lee@cloudscale.com",
        phone="555-0104", company_size="500-1000 employees", annual_revenue="$80M - $100M",
        location="New York, NY", funding_stage="Series D - $50M",
        tech_stack=["AWS", "Java", "Terraform"],
        lead_status="Proposal", segment="Enterprise",
    ),
]

SAMPLE_INSIGHT_FOR_TECHCORP = dict(
    qualification_score=92,
    score_label="Highly Qualified Lead",
    business_needs="Scaling data infrastructure to support rapid customer growth after Series C raise.",
    opportunities="Likely budget for new integration tooling given recent funding and headcount growth.",
    industry_analysis="Enterprise software company with modern cloud-native stack; strong fit for our platform.",
    reasoning=[
        {"factor": "High Growth Potential",
         "detail": "Series C funding indicates rapid expansion phase with likely budget for new tools."},
        {"factor": "Tech Alignment",
         "detail": "Current stack (AWS, Kubernetes, PostgreSQL) shows strong compatibility with our integrations."},
        {"factor": "Decision Maker Access",
         "detail": "Primary contact is the CTO, who typically owns this category of purchasing decision."},
    ],
)


def run():
    init_db()
    db = SessionLocal()
    try:
        if db.query(Lead).count() > 0:
            print("Leads already exist — skipping seed to avoid duplicates.")
            return

        created = {}
        for data in SAMPLE_LEADS:
            lead = Lead(**data)
            db.add(lead)
            db.flush()  # get lead_id before commit
            created[data["company_name"]] = lead

        techcorp = created.get("TechCorp Solutions")
        if techcorp:
            db.add(CompanyInsight(lead_id=techcorp.lead_id, **SAMPLE_INSIGHT_FOR_TECHCORP))

        db.commit()
        print(f"Seeded {len(SAMPLE_LEADS)} leads.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
