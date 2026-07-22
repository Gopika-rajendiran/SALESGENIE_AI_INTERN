# 🧠 SalesGenie AI — Intelligent B2B Sales Automation Platform

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.36+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Groq](https://img.shields.io/badge/Groq_LLM-Llama--3.3--70b-F55036?style=for-the-badge)

**A production-grade, AI-powered Intelligence and Outreach Automation system — built as a AI intern project.**

[Features](#-features) · [Architecture](#-system-architecture)  · [Modules](#-module-breakdown) · [API Reference](#-api-reference) ·

</div>

---

## 📌 Overview

**SalesGenie AI** is a fully integrated sales intelligence platform that empowers B2B sales teams and business developers to:

- **Manage prospects** with full CRUD operations via a structured lead pipeline
- **Generate AI-driven qualification insights** — score leads, identify opportunities, and surface business needs using LLM inference
- **Compose personalized outreach** — AI-written cold emails and follow-ups tailored to each lead's profile
- **Track conversations** — log interactions, retrieve history, and get AI-generated conversation summaries

The platform is architected as a **decoupled, microservice-inspired backend** powered by **FastAPI**, persisted in a relational **PostgreSQL** database  and surfaced via a rich **Streamlit** dashboard with a customized UI theme.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🗂️ Lead Management | Full CRUD — create, read, update, delete leads with company, contact, and segment data |
| 🤖 AI Qualification | LLM-powered 0–100 qualification score, label, business needs, and reasoning breakdown |
| 📧 Outreach Generation | AI-personalized cold email + follow-up email composer with campaign history |
| 🏆 Priority Scoring | Multi-factor priority ranking engine with What-If simulation |
| 💬 Conversation Intelligence | CRM-style interaction logging + AI-generated digest summaries |
| 📊 Analytics Dashboard | Real-time KPIs, pipeline funnel, score distribution, outreach stats, top-5 leads |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        SalesGenie AI                            │
│                                                                 │
│  ┌──────────────────────┐     HTTP REST      ┌───────────────┐  │
│  │  Streamlit Frontend  │ ─────────────────► │  FastAPI API  │  │
│  │     app.py :8502     │ ◄───────────────── │  main.py :8000│  │
│  └──────────────────────┘                    └───────┬───────┘  │
│                                                      │           │
│                                                      |           │
│                                                      │           │
│                                             ┌────────▼────────┐  │
│                                             │   PostgreSQL DB │  │
│                                             │  database/      │  │
│                                             │  models.py      │  │
│                                             └─────────────────┘  │
│                                                      │           │
│                                             ┌────────▼────────┐  │
│                                             │  LLM API Layer  │  │
│                                             │ Groq → OpenAI   │  │
│                                             └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Tech Stack at a Glance

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | Streamlit 1.36+ | Dashboard UI with dark theme, Plotly charts |
| **Backend** | FastAPI 0.111+ | Async REST API with 6 modular domain routers |
| **Database** | PostgreSQL 15+ | Relational persistence for all entities |
| **AI Core** | Groq (Llama-3.3-70b) | Primary LLM — fast inference |
| **Validation** | Pydantic 2.7+ | Request/response schema enforcement |
| **Charts** | Plotly 5.22+ | Interactive dashboard visualizations |

---

## 📁 Directory Layout

```
salesgenie/
│
├── main.py                     # FastAPI application entrypoint
├── app.py                      # Streamlit frontend (1115 lines)
├── run_all.py                  # One-command launcher: backend + frontend
├── seed_data.py                # Sample data seeder for development
├── requirements.txt            # Python dependency manifest
├── .env                        # Environment variables (not committed)
├── .gitignore                  # Git exclusion rules
│
├── database/
│   ├── __init__.py
│   ├── connection.py           # SQLAlchemy engine, session, Base, init_db()
│   └── models.py               # ORM models: User, Lead, CompanyInsight,
│                               #   OutreachCampaign, SalesInteraction, LeadScore
│
└── modules/
    ├── __init__.py
    ├── module1_leads.py        # Lead CRUD + interaction history
    ├── module2_intelligence.py # AI qualification analysis
    ├── module3_outreach.py     # AI email generation & campaign storage
    ├── module4_scoring.py      # Priority scoring engine + What-If sim
    ├── module5_conversation.py # CRM interaction CRUD + AI summaries
    └── module6_dashboard.py    # Aggregated KPIs & analytics endpoints
```

---

## 🗄️ Database Schema

```
users
  └─ user_id , name, email, role, department, created_at

leads
  ├─ lead_id (PK), company_name, industry, contact_name, title
  ├─ email, phone, company_size, annual_revenue, location
  ├─ funding_stage, tech_stack[], lead_status, segment
  └─ created_by (FK → users), created_at, updated_at

company_insights
  └─ insight_id (PK), lead_id (FK), qualification_score, score_label,
     business_needs[], opportunities[], industry_fit, ai_reasoning, created_at

outreach_campaigns
  └─ campaign_id (PK), lead_id (FK), campaign_type, subject_line,
     email_body, status, created_by (FK → users), created_at

sales_interactions
  └─ interaction_id (PK), lead_id (FK), user_id (FK), interaction_type,
     notes, outcome, interaction_date, created_at

lead_scores
  └─ score_id (PK), lead_id (FK, UNIQUE), priority_score, score_tier,
     scoring_factors (JSONB), recommendations (JSONB),
     last_scored_at, created_at
```

---

## 📦 Module Breakdown

### Module 1 — Lead Management (`/leads`)
> **The source of truth.** All other modules read from this data.

- `POST /leads/` — Create a new lead
- `GET /leads/` — List all leads (supports search, filter by status/segment, pagination)
- `GET /leads/{lead_id}` — Retrieve a single lead
- `PUT /leads/{lead_id}` — Update lead fields
- `DELETE /leads/{lead_id}` — Delete a lead
- `POST /leads/{lead_id}/interactions` — Log a sales interaction
- `GET /leads/{lead_id}/interactions` — Fetch interaction history

---

### Module 2 — Lead Intelligence (`/intelligence`)
> **AI-powered company qualification** using stored lead profile data.

- `POST /intelligence/analyze/{lead_id}` — Run LLM analysis, save `CompanyInsight`
- `GET /intelligence/{lead_id}` — Retrieve stored insight for a lead
- `GET /intelligence/status` — Health check

**AI Output Includes:**
- Qualification score (0–100)
- Score label (Hot / Warm / Cold / etc.)
- Business needs (list)
- Opportunities (list)
- Industry fit analysis
- Reasoning factors (bullet breakdown)

---

### Module 3 — AI Outreach (`/outreach`)
> **Personalized email generation** — cold emails + follow-up templates.

- `POST /outreach/generate/{lead_id}` — Generate email using LLM (type: `cold` / `followup`)
- `GET /outreach/history/{lead_id}` — Retrieve campaign history for a lead
- `GET /outreach/status` — Health check

**Email Generation uses:** Lead profile + existing `CompanyInsight` (if available) for hyper-personalization.

---

### Module 4 — Priority Scoring (`/scoring`)
> **Multi-factor lead ranking** with AI recommendations and simulation.

- `POST /scoring/score/{lead_id}` — Compute priority score, persist `LeadScore`
- `GET /scoring/scores` — Ranked leaderboard with filters
- `GET /scoring/{lead_id}` — Get score record for a lead
- `POST /scoring/simulate` — What-If simulation (adjust factors, see hypothetical score)
- `GET /scoring/status` — Health check

**Scoring Factors Include:** Company size, revenue, funding stage, tech stack, engagement, segment fit, and LLM-derived bonus insights.

---

### Module 5 — Conversation Intelligence (`/conversation`)
> **CRM-style interaction management** with AI digest generation.

- `POST /conversation/log` — Log a new interaction (call, email, demo, etc.)
- `GET /conversation/{lead_id}` — List all interactions for a lead
- `PUT /conversation/{interaction_id}` — Edit interaction notes/outcome
- `DELETE /conversation/{interaction_id}` — Delete an interaction
- `POST /conversation/summarize/{lead_id}` — LLM summary of full history
- `GET /conversation/status` — Health check

---

### Module 6 — Analytics Dashboard (`/dashboard`)
> **Real-time business intelligence** aggregated across all tables.

- `GET /dashboard/summary` — KPIs: total leads, active campaigns, avg score, hot leads
- `GET /dashboard/pipeline` — Leads per pipeline stage (funnel chart)
- `GET /dashboard/scoring-distribution` — Score tier breakdown
- `GET /dashboard/outreach-stats` — Campaign counters by type/status
- `GET /dashboard/top-leads` — Top 5 leads by priority score
- `GET /dashboard/activity-timeline` — Recent N interactions timeline

---

## ⚙️ Installation & Setup

### Prerequisites

- Python **3.11+**
- PostgreSQL **15+** running locally or via Docker
- **Groq API key** (free tier available at [console.groq.com](https://console.groq.com))

---

### 1. Clone the Repository

```bash
git clone https://github.com/Gopika-rajendiran/SALESGENIE_AI_INTERN.git
cd SALESGENIE_AI_INTERN
```

### 2. Create & Activate Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/salesgenie

# LLM APIs
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx   # optional fallback

# Service Ports (optional — defaults shown)
FASTAPI_PORT=8000
FASTAPI_URL=http://127.0.0.1:8000
STREAMLIT_PORT=8502
```

### 5. Initialize the Database

```bash
# Create the PostgreSQL database
psql -U postgres -c "CREATE DATABASE salesgenie;"

# Tables are auto-created on first startup via SQLAlchemy
# Optionally seed with sample data:
python seed_data.py
```

### 6. Run the Application

**Option A — Single command (recommended):**
```bash
python run_all.py
```
This launches both the FastAPI backend and Streamlit frontend simultaneously.

**Option B — Run services separately:**
```bash
# Terminal 1 — Backend
uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
streamlit run app.py --server.port 8502
```

### 7. Access the Application

| Service | URL |
|---|---|
| 🖥️ Streamlit Dashboard | http://localhost:8502 |
| ⚡ FastAPI Backend | http://localhost:8000 |
| 📖 Swagger (OpenAPI) Docs | http://localhost:8000/docs |
| 📘 ReDoc API Reference | http://localhost:8000/redoc |

---

## 🔑 API Reference

> Full interactive docs available at **`/docs`** (Swagger UI) and **`/redoc`** when the backend is running.

### Authentication
Currently uses no authentication in development mode. Production deployments should add OAuth2 / JWT via FastAPI's `Security` utilities.

### Base URL
```
http://localhost:8000
```

### Quick Request Examples

**Create a Lead:**
```bash
curl -X POST http://localhost:8000/leads/ \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "TechCorp Inc.",
    "industry": "SaaS",
    "contact_name": "Jane Doe",
    "email": "jane@techcorp.com",
    "company_size": "51-200",
    "annual_revenue": "$5M-$10M",
    "segment": "SMB"
  }'
```

**Run AI Analysis:**
```bash
curl -X POST http://localhost:8000/intelligence/analyze/1
```

**Generate Cold Email:**
```bash
curl -X POST "http://localhost:8000/outreach/generate/1?campaign_type=cold"
```

**Get Dashboard KPIs:**
```bash
curl http://localhost:8000/dashboard/summary
```

---

## 🤖 AI Integration Details

### LLM Call Flow

```
Request → Module Handler
    ↓
Try: Groq API (Llama-3.3-70b-versatile)
    ↓
Parse JSON response → Persist to DB → Return to frontend
```

### Prompt Strategy
Each module crafts a **structured system prompt** combining:
1. Lead profile data (company, size, revenue, tech stack, segment)
2. Existing `CompanyInsight` data (if available — Module 3 uses Module 2's output)
3. Task-specific instructions (qualification analysis / email tone / scoring factors)
4. **Strict JSON output format** requirements for programmatic parsing

---

## 🧪 Development Notes

### Seed Data
```bash
python seed_data.py
```
Populates the database with realistic sample leads, users, interactions, and scores for development and testing.

### Environment Switching
All configurable values are environment-variable driven. Use separate `.env.development`, `.env.production` files and load with `python-dotenv`.

### Adding a New Module
1. Create `modules/moduleN_name.py` with a FastAPI `APIRouter`
2. Add ORM models to `database/models.py` if needed
3. Mount the router in `main.py`:
   ```python
   from modules.moduleN_name import router as name_router
   app.include_router(name_router, prefix="/name", tags=["Module N"])
   ```
4. Add the corresponding Streamlit page section in `app.py`

---


## 👩‍💻 Author

**Gopika Rajendiran**
- GitHub: [@Gopika-rajendiran](https://github.com/Gopika-rajendiran)
- Email: gopika2376@gmail.com

---

<div align="center">

**Built as part of an AI/ML Internship Project**

*_SalesGenie AI _*

</div>
