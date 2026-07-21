# SalesGenie AI — Developer Hub & Documentation

SalesGenie AI is an advanced, production-grade B2B Sales Intelligence and AI-powered Outreach Automation platform. It enables sales representatives and business developers to manage prospects, generate AI-driven qualification insights, and compose personalized email copy tailored to target segments.

The platform is architected as an asynchronous backend API powered by **FastAPI**, backed by a relational **PostgreSQL** database managed via **SQLAlchemy ORM**, and driven by an intuitive front-end interface built on **Streamlit**.

---

## 1. System Architecture

```mermaid
graph TD
    Streamlit[Streamlit Frontend :8502] -->|HTTP REST| FastAPI[FastAPI Backend :8000]
    FastAPI -->|SQLAlchemy ORM| PostgreSQL[(PostgreSQL Database)]
    FastAPI -->|OpenAI SDK / API| LLM[LLM API: Groq / OpenAI]
```

### Stack Components
- **Frontend**: Streamlit (`app.py`), styled with a customized premium dark UI theme.
- **Backend**: FastAPI (`main.py`) serving as a modular API Gateway mounting six decoupled domain routers.
- **Database**: PostgreSQL with SQLAlchemy ORM representing schema definitions in `database/models.py` and managing connections in `database/connection.py`.
- **AI Core**: Groq API (defaulting to Llama-3.3-70b) with dynamic fallback to OpenAI API (GPT-4o-mini).

---

## 2. Directory Layout

```
salesgenie/
├── .env                  # Local environment configuration (git-ignored)
├── .env.example          # Environment variables template
├── .gitignore            # Git exclusion definitions
├── requirements.txt      # Python dependencies
├── main.py               # FastAPI backend entrypoint (mounts all modules)
├── app.py                # Streamlit dashboard interface
├── run_all.py            # Co-orchestrator running both frontend and backend
├── seed_data.py          # Database seeding script for mock leads & insights
├── database/
│   ├── __init__.py
│   ├── connection.py     # Connection engine, sessionmaker, and table initializer
│   └── models.py         # SQLAlchemy schemas (User, Lead, CompanyInsight, etc.)
└── modules/
    ├── __init__.py
    ├── module1_leads.py          # Lead management CRUD & CRM activity logger
    ├── module2_intelligence.py   # AI prospect qualification scoring & reasoning
    ├── module3_outreach.py       # Personalized AI cold-outreach & follow-up generator
    ├── module4_scoring.py        # Lead scoring & recommendation stubs (Milestone 2)
    ├── module5_conversation.py   # Conversation intelligence stubs (Milestone 3)
    └── module6_dashboard.py      # Sales analytics stubs (Milestone 4)
```

---

## 3. Database Schema

All domain entities are modeled in SQLAlchemy using the declarative base. The backend utilizes an **idempotent auto-migration** routine on startup (`Base.metadata.create_all`) to ensure tables are configured without manuals.

```mermaid
erDiagram
    users ||--o{ leads : "manages"
    leads ||--o{ company_insights : "has"
    leads ||--o{ outreach_campaigns : "receives"
    leads ||--o{ sales_interactions : "has"

    users {
        int user_id PK
        string name
        string email UK
        string role
        string department
        timestamp created_at
    }

    leads {
        int lead_id PK
        string company_name
        string industry
        string contact_name
        string title
        string email
        string phone
        string company_size
        string annual_revenue
        string location
        string funding_stage
        string[] tech_stack
        string lead_status
        string segment
        int created_by FK
        timestamp created_at
        timestamp updated_at
    }

    company_insights {
        int insight_id PK
        int lead_id FK
        int qualification_score
        string score_label
        text business_needs
        text opportunities
        text industry_analysis
        jsonb reasoning
        timestamp generated_at
    }

    outreach_campaigns {
        int campaign_id PK
        int lead_id FK
        string email_type
        string tone
        string email_subject
        text email_content
        string campaign_status
        timestamp created_at
    }

    sales_interactions {
        int interaction_id PK
        int lead_id FK
        string interaction_type
        text summary
        text action_items
        timestamp interaction_date
    }
```

### Table Definitions & Constraints
1. **`users`**: Represents internal team members using the platform.
2. **`leads`**: Central catalog of target prospects. Columns include company identifiers, financial profiling, contact details, technology list (represented via PostgreSQL `ARRAY(String)`), pipeline lifecycle stages (`lead_status`), and classification (`segment`).
3. **`company_insights`**: Stores generated AI evaluations. Uses `ondelete="CASCADE"` on the `lead_id` foreign key. Includes a `reasoning` column defined as `JSONB` to capture structured factor arrays.
4. **`outreach_campaigns`**: Logs AI-generated messages. Links back to the targeted lead. Captures metadata like tone, layout structure, and delivery state (`draft` vs `sent`).
5. **`sales_interactions`**: Activity feed logs (Calls, Emails, Meetings, Notes) to record CRM engagements.

---

## 4. Module & API Architecture

### Module 1: Lead Management & CRM (`modules/module1_leads.py`)
Responsible for prospect records and CRM timeline logs.
- `GET /leads`
  - **Query Parameters**:
    - `q` (Optional): String filter matching `company_name`, `contact_name`, or `industry` case-insensitively.
    - `status` (Optional): Stage filtering (`New`, `Contacted`, `Qualified`, etc.).
    - `segment` (Optional): Market segmenting (`Enterprise`, `Mid-Market`, `Startup`).
  - **Returns**: Array of full lead profiles sorted chronologically (`created_at DESC`).
- `POST /leads`: Instantiates a lead. Accepts `LeadCreate` Pydantic payload.
- `GET /leads/{lead_id}`: Retrieves profile details. Raises `404` error if non-existent.
- `PUT /leads/{lead_id}`: Updates fields. Automatically updates `updated_at` timestamps.
- `DELETE /leads/{lead_id}`: Removes lead and cascades deletes to related insights, campaigns, and logs.
- `GET /leads/stages`: Returns valid lead pipeline states (`LEAD_STAGES`).
- `POST /leads/{lead_id}/interactions`: Log activities like Calls, Emails, and Meetings with description notes.
- `GET /leads/{lead_id}/interactions`: Retrieve chronological timeline activity history.

### Module 2: Lead Intelligence (`modules/module2_intelligence.py`)
Evaluates prospects against business fit using an LLM.
- `POST /intelligence/generate/{lead_id}`: 
  1. Pulls the target lead profile.
  2. Compiles a detailed evaluation prompt defining the saas solution fit.
  3. Deserializes the JSON response returned by the LLM.
  4. Stores the analysis in `company_insights` with numeric qualification scores, textual opportunity details, and structured factors.
- `GET /intelligence/{lead_id}`: Returns the latest generated report.
- `GET /intelligence/{lead_id}/history`: Returns a historical log of all generated evaluations.
- `GET /intelligence/health`: Reports LLM connector states (`llm_configured: true/false`).

### Module 3: AI Outreach Generation (`modules/module3_outreach.py`)
Drafts contextual cold emails and follow-ups.
- `POST /outreach/generate`: Composes drafts using lead profiles and Module 2 insights.
  - **Pydantic Body**:
    ```json
    {
      "lead_id": 1,
      "email_type": "cold_email",
      "tone": "consultative",
      "extra_context": "Mention their recent series B"
    }
    ```
- `POST /outreach/save`: Commits a draft or registers an outreach campaign.
- `GET /outreach/history/{lead_id}`: Returns all saved campaigns and statuses for the lead.
- `PATCH /outreach/mark-sent/{campaign_id}`: Promotes draft campaigns to `sent` delivery states.

### Modules 4, 5 & 6 (Future Milestones)
Currently mounted as stub endpoints returning `501` or placeholder objects under:
- `GET /scoring/status` (Lead Scoring - Milestone 2)
- `GET /conversation/status` (Conversation Intelligence - Milestone 3)
- `GET /dashboard/status` (Sales Analytics - Milestone 4)

---

## 5. LLM Integration & Prompt Engine

SalesGenie AI features a unified client abstraction supporting **Groq** and **OpenAI**. 

### Client Initialization
The module reads keys from environment variables:
1. If `GROQ_API_KEY` is present, it wraps it with the `OpenAI` client pointing to the Groq backend.
2. If `GROQ_API_KEY` is absent but `OPENAI_API_KEY` is active, it connects to standard OpenAI endpoints.
3. If neither is available, the generation routes raise an HTTP `503 Service Unavailable` error instead of throwing a stack trace:
   ```python
   raise HTTPException(
       status_code=503,
       detail="LLM not configured. Set GROQ_API_KEY or OPENAI_API_KEY in your .env file."
   )
   ```

### Prompt Constraints & Guardrails
- **Output Constraints**: Prompts instruct the LLM to output valid raw JSON. System prompts use `"You are a precise assistant that only outputs valid JSON."` to ensure structured parsing.
- **Outreach Rules**: The cold email generation prompt enforces specific constraints:
  - Text length must be under 150 words.
  - Must address the specific tech stack and industry.
  - Placeholders must not be used (e.g. `[Your Name]` is banned, defaulting to `"The SalesGenie Team"`).

---

## 6. Local Setup Instructions

Follow these steps to set up a local development sandbox.

### Prerequisites
- Python 3.10 or higher.
- PostgreSQL server (running locally or remotely).

### Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/Divyabharathi23012007/SalesGenieAI.git
   cd SalesGenieAI
   ```

2. **Initialize Python Environment**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**
   Copy the provided configuration template:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and fill in the required keys:
   ```dotenv
   DATABASE_URL=postgresql://postgres:your_password@localhost:5432/salesgenie
   GROQ_API_KEY=gsk_yourKeyGoesHere
   ```

4. **Prepare the Database**
   Log into your PostgreSQL CLI or interface and create the target database:
   ```sql
   CREATE DATABASE salesgenie;
   ```
   *Note: Table schemas are auto-created on API boot.*

5. **Seed Sample Data (Optional)**
   Pre-populate the tables with four mock leads and an analytical evaluation to test Module 3:
   ```bash
   python seed_data.py
   ```

---

## 7. Running the Platform

Use the unified process orchestrator to boot both the FastAPI service and Streamlit client simultaneously:

```bash
python run_all.py
```

- **Backend Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Frontend Client**: [http://localhost:8502](http://localhost:8502)

To run backend or frontend independently:
- **FastAPI**: `uvicorn main:app --reload --port 8000`
- **Streamlit**: `streamlit run app.py --server.port 8502`

---

## 8. Extension Guide for Feature Developers

When building features on top of SalesGenie AI, adhere to the following rules:

### Schema Updates
- Database entities are centrally declared in [models.py](file:///e:/SKY/Moon/salesgenie/salesgenie/database/models.py).
- If you add columns to `leads`, `company_insights`, or `outreach_campaigns`, verify that column types align perfectly with data parameters used in the modules.

### Transitioning Stubs to Production
1. **Module 4 (Scoring)**:
   - File: `modules/module4_scoring.py`.
   - Goal: Transition the `/scoring/status` stub into an evaluation model. Inject the DB session and utilize lead parameters (revenue, company size, and funding stage) to compute custom fit scores.
2. **Module 5 (Conversations)**:
   - File: `modules/module5_conversation.py`.
   - Goal: Expand the router to consume audio file uploads or transcript logs, parse them with an LLM, and log call insights in `sales_interactions`.
3. **Module 6 (Dashboard)**:
   - File: `modules/module6_dashboard.py`.
   - Goal: Aggregate and serve pipeline volume metrics, conversion rates, and campaign statistics to feed Streamlit dashboard cards.

---

## 9. Troubleshooting

### "Unable to connect to the FastAPI backend"
- Verify that `FASTAPI_URL` in `.env` matches the port your FastAPI process is listening on.
- Check terminal output of `run_all.py` for binding errors (such as port 8000 already in use).
- Ensure your local machine permits connections across local loops.

### LLM Error: 502 Bad Gateway / JSONDecodeError
- This happens when the API receives non-JSON data from the models. Retry the request. If it persists, inspect backend logs to view the raw LLM output.