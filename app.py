"""
app.py
Streamlit frontend for SalesGenie AI — Modules 1, 2, and 3 fully wired up.
Run with: streamlit run app.py --server.port 8502
(or via run_all.py which starts backend + frontend together)
"""

import os
import requests
import streamlit as st
# pyrefly: ignore [missing-import]
import plotly.graph_objects as go
from dotenv import load_dotenv

load_dotenv()

FASTAPI_URL = os.getenv("FASTAPI_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="SalesGenie AI", layout="wide", initial_sidebar_state="expanded")

# --------------------------------------------------------------------------
# DARK THEME STYLING (matches the reference screenshot)
# --------------------------------------------------------------------------
st.markdown("""
<style>
    body, .stApp { background-color: #0e1117; color: #e6e6e6; }
    section[data-testid="stSidebar"] {
        background-color: #12141c;
        border-right: 1px solid #262730;
    }
    .sg-title { font-size: 28px; font-weight: 800; color: #38bdf8; margin-bottom: 0px; }
    .sg-subtitle { font-size: 13px; color: #9ca3af; margin-top: 0px; margin-bottom: 24px; }
    .sg-nav-header {
        font-size: 12px; color: #6b7280; letter-spacing: 1px;
        text-transform: uppercase; margin: 18px 0 6px 0;
    }
    .sg-page-title { font-size: 42px; font-weight: 800; color: #f5f5f5; margin-bottom: 4px; }
    .sg-page-subtitle { font-size: 15px; color: #9ca3af; margin-bottom: 28px; }
    .sg-error-box {
        background-color: #3a1620; border: 1px solid #7f1d3a; color: #fca5a5;
        padding: 16px 20px; border-radius: 8px; font-size: 15px;
    }
    .sg-success-box {
        background-color: #10261c; border: 1px solid #16543a; color: #86efac;
        padding: 14px 18px; border-radius: 8px; font-size: 14px;
    }
    .sg-card {
        background-color: #161923; border: 1px solid #262730; border-radius: 10px;
        padding: 20px; margin-bottom: 16px;
    }
    .sg-badge {
        display: inline-block; background-color: #1e3a5f; color: #7dd3fc;
        font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 12px;
        letter-spacing: 0.5px;
    }
    .sg-factor { font-weight: 700; color: #f5f5f5; font-size: 14px; margin-bottom: 2px; }
    .sg-factor-detail { color: #9ca3af; font-size: 13px; margin-bottom: 14px; }
    div[data-testid="stRadio"] label { font-size: 15px; padding: 4px 0; }
    .stButton>button {
        background-color: #0ea5e9; color: white; border: none; border-radius: 6px;
        font-weight: 600;
    }
    .stButton>button:hover { background-color: #0284c7; }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------
# API HELPERS
# --------------------------------------------------------------------------
def backend_alive() -> bool:
    try:
        r = requests.get(f"{FASTAPI_URL}/", timeout=2)
        return r.status_code == 200
    except requests.exceptions.RequestException:
        return False


def api_get(path, **kwargs):
    return requests.get(f"{FASTAPI_URL}{path}", timeout=kwargs.pop("timeout", 10), **kwargs)


def api_post(path, **kwargs):
    return requests.post(f"{FASTAPI_URL}{path}", timeout=kwargs.pop("timeout", 30), **kwargs)


def api_put(path, **kwargs):
    return requests.put(f"{FASTAPI_URL}{path}", timeout=kwargs.pop("timeout", 10), **kwargs)


def api_delete(path, **kwargs):
    return requests.delete(f"{FASTAPI_URL}{path}", timeout=kwargs.pop("timeout", 10), **kwargs)


def safe_json(resp):
    try:
        return resp.json()
    except ValueError:
        return {"detail": resp.text.strip() or f"Empty response (HTTP {resp.status_code})"}

def fetch_leads(q: str = None):
    params = {"q": q} if q else {}
    resp = api_get("/leads", params=params)
    resp.raise_for_status()
    return resp.json()


def lead_label(l: dict) -> str:
    seg = f" · {l['segment']}" if l.get("segment") else ""
    return f"{l['company_name']} — {l.get('contact_name') or 'No contact'}{seg}"


TECH_STACK_OPTIONS = [
    "AWS", "GCP", "Azure", "Python", "Java", "Go", "Node.js", "React",
    "Kubernetes", "Docker", "PostgreSQL", "MongoDB", "Kafka", "TensorFlow", "Terraform",
]
SEGMENTS = ["Enterprise", "Mid-Market", "Startup"]


# --------------------------------------------------------------------------
# SIDEBAR
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="sg-title">SalesGenie AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="sg-subtitle">Lead Management Platform</div>', unsafe_allow_html=True)
    st.markdown('<div class="sg-nav-header">Navigation</div>', unsafe_allow_html=True)

    page = st.radio(
        label="Navigation",
        options=[
            "Dashboard",
            "Lead Management",
            "Add Lead",
            "Lead Intelligence",
            "AI Outreach",
            "Lead Scoring",
            "Sales Interactions",
        ],
        index=1,
        label_visibility="collapsed",
    )

if not backend_alive():
    st.markdown(
        '<div class="sg-error-box">Unable to connect to the FastAPI backend. '
        f'Make sure it is running at <b>{FASTAPI_URL}</b> '
        '(<code>uvicorn main:app --reload --port 8000</code> or run <code>python run_all.py</code>).</div>',
        unsafe_allow_html=True,
    )
    st.stop()


# --------------------------------------------------------------------------
# MODULE 1 — LEAD MANAGEMENT
# --------------------------------------------------------------------------
def render_lead_management():
    st.markdown('<div class="sg-page-title">Lead Management</div>', unsafe_allow_html=True)
    st.markdown('<div class="sg-page-subtitle">View, search, edit, and remove prospects.</div>', unsafe_allow_html=True)

    search = st.text_input("Search by company, contact, or industry", placeholder="e.g. TechCorp")

    try:
        leads = fetch_leads(search or None)
    except Exception as e:
        st.error(f"Could not load leads: {e}")
        return

    if not leads:
        st.info("No leads found. Add one from the 'Add Lead' page, or run seed_data.py for sample data.")
        return

    st.caption(f"{len(leads)} lead(s) found")
    table_rows = [
        {
            "Company": l["company_name"],
            "Contact": l.get("contact_name") or "—",
            "Industry": l.get("industry") or "—",
            "Segment": l.get("segment") or "—",
            "Stage": l.get("lead_status") or "—",
            "Location": l.get("location") or "—",
        }
        for l in leads
    ]
    st.dataframe(table_rows, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Edit or Delete a Lead")

    label_to_lead = {lead_label(l): l for l in leads}
    selected_label = st.selectbox("Select a lead", list(label_to_lead.keys()))
    lead = label_to_lead[selected_label]

    try:
        stages_resp = api_get("/leads/stages")
        stages = stages_resp.json()["stages"] if stages_resp.status_code == 200 else \
            ["New", "Contacted", "Qualified", "Proposal", "Negotiation", "Closed Won", "Closed Lost"]
    except Exception:
        stages = ["New", "Contacted", "Qualified", "Proposal", "Negotiation", "Closed Won", "Closed Lost"]

    with st.form(f"edit_lead_{lead['lead_id']}"):
        c1, c2 = st.columns(2)
        with c1:
            company_name = st.text_input("Company Name", value=lead["company_name"])
            contact_name = st.text_input("Contact Name", value=lead.get("contact_name") or "")
            title = st.text_input("Title", value=lead.get("title") or "")
            email = st.text_input("Email", value=lead.get("email") or "")
            phone = st.text_input("Phone", value=lead.get("phone") or "")
            industry = st.text_input("Industry", value=lead.get("industry") or "")
        with c2:
            company_size = st.text_input("Company Size", value=lead.get("company_size") or "")
            annual_revenue = st.text_input("Annual Revenue", value=lead.get("annual_revenue") or "")
            location = st.text_input("Location", value=lead.get("location") or "")
            funding_stage = st.text_input("Funding Stage", value=lead.get("funding_stage") or "")
            segment = st.selectbox("Segment", SEGMENTS,
                                    index=SEGMENTS.index(lead["segment"]) if lead.get("segment") in SEGMENTS else 0)
            lead_status = st.selectbox("Lead Stage", stages,
                                        index=stages.index(lead["lead_status"]) if lead.get("lead_status") in stages else 0)

        tech_stack = st.multiselect("Technology Stack", TECH_STACK_OPTIONS, default=lead.get("tech_stack") or [])

        col_save, col_delete = st.columns([1, 1])
        save_clicked = col_save.form_submit_button("💾 Save Changes", type="primary")
        delete_clicked = col_delete.form_submit_button("🗑️ Delete Lead")

    if save_clicked:
        payload = {
            "company_name": company_name, "contact_name": contact_name, "title": title,
            "email": email, "phone": phone, "industry": industry, "company_size": company_size,
            "annual_revenue": annual_revenue, "location": location, "funding_stage": funding_stage,
            "segment": segment, "lead_status": lead_status, "tech_stack": tech_stack,
        }
        resp = api_put(f"/leads/{lead['lead_id']}", json=payload)
        if resp.status_code == 200:
            st.markdown('<div class="sg-success-box">Lead updated successfully.</div>', unsafe_allow_html=True)
            st.rerun()
        else:
            st.error(f"Update failed: {resp.text}")

    if delete_clicked:
        resp = api_delete(f"/leads/{lead['lead_id']}")
        if resp.status_code == 200:
            st.markdown('<div class="sg-success-box">Lead deleted.</div>', unsafe_allow_html=True)
            st.rerun()
        else:
            st.error(f"Delete failed: {resp.text}")

    st.markdown("---")
    st.subheader("Engagement History")
    try:
        hist = api_get(f"/leads/{lead['lead_id']}/interactions").json()
    except Exception:
        hist = []

    if hist:
        for h in hist:
            with st.expander(f"{h['interaction_type']} · {h.get('interaction_date', '')[:10]}"):
                st.write(h.get("summary") or "No summary.")
                if h.get("action_items"):
                    st.caption(f"Action items: {h['action_items']}")
    else:
        st.caption("No interactions logged yet.")

    with st.expander("➕ Log a new interaction"):
        with st.form(f"log_interaction_{lead['lead_id']}"):
            itype = st.selectbox("Type", ["Call", "Email", "Meeting", "Note"])
            summary = st.text_area("Summary")
            action_items = st.text_input("Action items (optional)")
            logged = st.form_submit_button("Log Interaction")
        if logged:
            resp = api_post(f"/leads/{lead['lead_id']}/interactions",
                             json={"interaction_type": itype, "summary": summary, "action_items": action_items})
            if resp.status_code == 200:
                st.success("Interaction logged.")
                st.rerun()
            else:
                st.error(f"Failed: {resp.text}")


# --------------------------------------------------------------------------
# MODULE 1 — ADD LEAD
# --------------------------------------------------------------------------
def render_add_lead():
    st.markdown('<div class="sg-page-title">Add Lead</div>', unsafe_allow_html=True)
    st.markdown('<div class="sg-page-subtitle">Create a new prospect record.</div>', unsafe_allow_html=True)

    with st.form("add_lead_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            company_name = st.text_input("Company Name *")
            contact_name = st.text_input("Contact Name")
            title = st.text_input("Title")
            email = st.text_input("Email")
            phone = st.text_input("Phone")
            industry = st.text_input("Industry")
        with c2:
            company_size = st.text_input("Company Size", placeholder="e.g. 250-500 employees")
            annual_revenue = st.text_input("Annual Revenue", placeholder="e.g. $45M - $60M")
            location = st.text_input("Location")
            funding_stage = st.text_input("Funding Stage", placeholder="e.g. Series C - $28M")
            segment = st.selectbox("Segment", SEGMENTS)
            lead_status = st.selectbox("Initial Stage", ["New", "Contacted", "Qualified"])

        tech_stack = st.multiselect("Technology Stack", TECH_STACK_OPTIONS)

        submitted = st.form_submit_button("➕ Add Lead", type="primary")

    if submitted:
        if not company_name.strip():
            st.error("Company Name is required.")
            return
        payload = {
            "company_name": company_name, "contact_name": contact_name, "title": title,
            "email": email, "phone": phone, "industry": industry, "company_size": company_size,
            "annual_revenue": annual_revenue, "location": location, "funding_stage": funding_stage,
            "segment": segment, "lead_status": lead_status, "tech_stack": tech_stack,
        }
        resp = api_post("/leads", json=payload)
        if resp.status_code == 200:
            st.markdown(f'<div class="sg-success-box">Lead "{company_name}" added successfully.</div>',
                        unsafe_allow_html=True)
        else:
            st.error(f"Failed to add lead: {resp.text}")


# --------------------------------------------------------------------------
# MODULE 2 — LEAD INTELLIGENCE
# --------------------------------------------------------------------------
def score_gauge(score: int):
    color = "#22c55e" if score >= 75 else "#eab308" if score >= 45 else "#ef4444"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"font": {"size": 40, "color": "#f5f5f5"}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#6b7280"},
            "bar": {"color": color},
            "bgcolor": "#161923",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 45], "color": "#2a1a1a"},
                {"range": [45, 75], "color": "#2a2410"},
                {"range": [75, 100], "color": "#0f2a1a"},
            ],
        },
    ))
    fig.update_layout(
        height=220, margin=dict(l=20, r=20, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)", font={"color": "#f5f5f5"},
    )
    return fig


def render_lead_intelligence():
    st.markdown('<div class="sg-page-title">Lead Intelligence</div>', unsafe_allow_html=True)
    st.markdown('<div class="sg-page-subtitle">AI-powered company analysis and qualification scoring.</div>', unsafe_allow_html=True)

    try:
        leads = fetch_leads()
    except Exception as e:
        st.error(f"Could not load leads: {e}")
        return
    if not leads:
        st.info("No leads yet. Add one from the 'Add Lead' page first.")
        return

    label_to_lead = {lead_label(l): l for l in leads}
    selected_label = st.selectbox("Select a lead to analyze", list(label_to_lead.keys()))
    lead = label_to_lead[selected_label]

    col_profile, col_intel = st.columns([1, 1])

    with col_profile:
        st.markdown('<div class="sg-card">', unsafe_allow_html=True)
        st.markdown(f"### {lead['company_name']}")
        st.caption(f"{lead.get('industry') or 'Unknown industry'} · {lead.get('segment') or 'Unsegmented'}")
        st.write(f"**Company Size:** {lead.get('company_size') or '—'}")
        st.write(f"**Annual Revenue:** {lead.get('annual_revenue') or '—'}")
        st.write(f"**Location:** {lead.get('location') or '—'}")
        st.write(f"**Funding Stage:** {lead.get('funding_stage') or '—'}")
        if lead.get("tech_stack"):
            st.write("**Tech Stack:** " + ", ".join(lead["tech_stack"]))
        st.write(f"**Pipeline Stage:** {lead.get('lead_status') or '—'}")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_intel:
        st.markdown('<span class="sg-badge">AI POWERED</span>', unsafe_allow_html=True)
        st.write("")

        try:
            insight_resp = api_get(f"/intelligence/{lead['lead_id']}")
            insight = insight_resp.json() if insight_resp.status_code == 200 else None
        except Exception:
            insight = None

        btn_label = "🔄 Regenerate Insights" if insight else "✨ Generate Lead Intelligence"
        if st.button(btn_label, type="primary"):
            with st.spinner("Analyzing company profile..."):
                gen_resp = api_post(f"/intelligence/generate/{lead['lead_id']}")
                if gen_resp.status_code == 200:
                    insight = gen_resp.json()
                    st.rerun()
                else:
                    st.error(f"Generation failed: {gen_resp.json().get('detail', gen_resp.text)}")

        if insight:
            st.plotly_chart(score_gauge(insight["qualification_score"]), use_container_width=True)
            st.markdown(f"**{insight['score_label']}**")
            st.progress(insight["qualification_score"] / 100)

            if insight.get("business_needs"):
                st.write(f"**Business Needs:** {insight['business_needs']}")
            if insight.get("opportunities"):
                st.write(f"**Opportunity:** {insight['opportunities']}")
            if insight.get("industry_analysis"):
                st.write(f"**Industry Fit:** {insight['industry_analysis']}")

            if insight.get("reasoning"):
                st.markdown("---")
                st.markdown("**Qualification Factors**")
                for item in insight["reasoning"]:
                    st.markdown(f'<div class="sg-factor">▸ {item["factor"]}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="sg-factor-detail">{item["detail"]}</div>', unsafe_allow_html=True)
        else:
            st.caption("No insights generated yet for this lead. Click the button above.")


# --------------------------------------------------------------------------
# MODULE 4 — LEAD SCORING & RECOMMENDATIONS
# --------------------------------------------------------------------------
def render_lead_scoring():
    st.markdown('<div class="sg-page-title">Lead Scoring & Recommendations</div>', unsafe_allow_html=True)
    st.markdown('<div class="sg-page-subtitle">Rank prospects and run simulated What-If analyses.</div>', unsafe_allow_html=True)

    tab_rank, tab_score, tab_sim = st.tabs([
        "🏆 Priority Rankings",
        "📊 Score & AI Recommendations",
        "🧪 What-If Simulator"
    ])

    with tab_rank:
        st.subheader("Lead Priority Pipeline")
        try:
            resp = api_get("/scoring/ranking/list")
            if resp.status_code == 200:
                rankings = resp.json()
            else:
                st.error(f"Failed to load rankings (HTTP {resp.status_code}): {resp.text}")
                rankings = []
        except Exception as e:
            st.error(f"Could not load rankings: {e}")
            rankings = []
        
        if rankings and isinstance(rankings, list):
            table_rows = [
                {
                    "Company": r["company_name"],
                    "Score": r["score"],
                    "Classification": r["classification"],
                    "Industry": r.get("industry") or "—",
                    "Status": r.get("lead_status") or "—",
                }
                for r in rankings
            ]
            st.dataframe(table_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No scores available. Recalculate scoring for a lead under the 'Score & AI Recommendations' tab.")

    with tab_score:
        try:
            leads = fetch_leads()
        except Exception as e:
            st.error(f"Could not load leads: {e}")
            return
        if not leads:
            st.warning("No leads found. Add some leads first.")
            return

        label_to_lead = {lead_label(l): l for l in leads}
        selected_label = st.selectbox("Select Lead to Score", list(label_to_lead.keys()), key="score_lead_select")
        lead = label_to_lead[selected_label]
        lead_id = lead["lead_id"]

        col_profile, col_score = st.columns([1, 1])

        with col_profile:
            st.markdown('<div class="sg-card">', unsafe_allow_html=True)
            st.markdown(f"### {lead['company_name']}")
            st.caption(f"{lead.get('industry') or 'Unknown industry'} · {lead.get('segment') or 'Unsegmented'}")
            st.write(f"**Company Size:** {lead.get('company_size') or '—'}")
            st.write(f"**Annual Revenue:** {lead.get('annual_revenue') or '—'}")
            st.write(f"**Location:** {lead.get('location') or '—'}")
            st.write(f"**Funding Stage:** {lead.get('funding_stage') or '—'}")
            if lead.get("tech_stack"):
                st.write("**Tech Stack:** " + ", ".join(lead["tech_stack"]))
            st.write(f"**Pipeline Stage:** {lead.get('lead_status') or '—'}")
            st.markdown('</div>', unsafe_allow_html=True)

        with col_score:
            try:
                score_resp = api_get(f"/scoring/{lead_id}")
                score_data = score_resp.json() if score_resp.status_code == 200 else None
            except Exception:
                score_data = None

            btn_label = "🔄 Recalculate Score" if score_data else "✨ Calculate Lead Score"
            if st.button(btn_label, type="primary", key="calc_score_btn"):
                with st.spinner("Calculating score and generating recommendations..."):
                    gen_resp = api_post(f"/scoring/generate/{lead_id}")
                    if gen_resp.status_code == 200:
                        st.success("Lead score generated successfully!")
                        st.rerun()
                    else:
                        st.error(f"Generation failed: {gen_resp.text}")

            if score_data:
                st.plotly_chart(score_gauge(score_data["score"]), use_container_width=True, key=f"score_gauge_{lead_id}")
                st.markdown(f"**Priority Level:** `{score_data['classification']}`")
                
                conf = score_data.get("confidence_score", 0)
                st.markdown(f"**Data Confidence Score:** {conf}%")
                st.progress(conf / 100)

                st.markdown("---")
                st.markdown("**Scoring Breakdown**")
                explanation = score_data.get("explanation", {})
                for factor, points in explanation.items():
                    st.write(f"**{factor}:** {points} pts")

                st.markdown("---")
                st.markdown("**AI Recommendations & Next Steps**")
                st.markdown(score_data.get("recommendations", "No recommendations found."))
            else:
                st.caption("No score generated yet. Click the button above.")

    with tab_sim:
        st.subheader("What-If Score Simulator")
        st.caption("Adjust the parameters below to see how they impact the lead score in real time. This will not modify the database.")
        
        sim_label_to_lead = {lead_label(l): l for l in leads}
        sim_selected_label = st.selectbox("Select Lead to Simulate", list(sim_label_to_lead.keys()), key="sim_lead_select")
        sim_lead = sim_label_to_lead[sim_selected_label]
        sim_lead_id = sim_lead["lead_id"]

        with st.form("what_if_simulator_form"):
            c1, c2 = st.columns(2)
            with c1:
                comp_size = st.text_input("Company Size", value=sim_lead.get("company_size") or "")
                ann_rev = st.text_input("Annual Revenue", value=sim_lead.get("annual_revenue") or "")
                funding = st.text_input("Funding Stage", value=sim_lead.get("funding_stage") or "")
                industry = st.text_input("Industry", value=sim_lead.get("industry") or "")
                
                hiring_trend = st.selectbox("Hiring Trend", ["Stable", "Growing", "Declining"])
                website_eng = st.selectbox("Website Engagement", ["Low", "Medium", "High"])

            with c2:
                email_open = st.selectbox("Email Open Rate", ["No Outreach", "Sent but Not Opened", "Opened"])
                email_reply = st.selectbox("Email Reply Status", ["No Reply", "Replied"])
                linkedin_eng = st.selectbox("LinkedIn Engagement", ["No Engagement", "Engaged"])
                recent_news = st.selectbox("Recent News", ["No News", "Positive News"])
                demo_booked = st.checkbox("Demo/Meeting Booked", value=False)

            run_sim = st.form_submit_button("🧪 Run Simulation", type="primary")

        if run_sim:
            payload = {
                "lead_id": sim_lead_id,
                "company_size": comp_size or None,
                "annual_revenue": ann_rev or None,
                "funding_stage": funding or None,
                "industry": industry or None,
                "hiring_trend": hiring_trend,
                "website_engagement": website_eng,
                "email_open_rate": email_open,
                "email_reply": email_reply,
                "linkedin_engagement": linkedin_eng,
                "recent_news": recent_news,
                "demo_booked": demo_booked
            }
            with st.spinner("Simulating..."):
                sim_resp = api_post("/scoring/simulate", json=payload)
                if sim_resp.status_code == 200:
                    sim_data = sim_resp.json()
                    st.success("Simulation Complete!")
                    
                    sc1, sc2 = st.columns([1, 1])
                    with sc1:
                        st.plotly_chart(score_gauge(sim_data["score"]), use_container_width=True, key=f"sim_gauge_{sim_lead_id}")
                        st.markdown(f"**Simulated Classification:** `{sim_data['classification']}`")
                        st.markdown(f"**Simulated Data Confidence:** {sim_data.get('confidence_score', 0)}%")
                    with sc2:
                        st.markdown("**Simulated Scoring Explanation**")
                        for factor, points in sim_data.get("explanation", {}).items():
                            st.write(f"**{factor}:** {points} pts")
                        st.markdown("---")
                        st.markdown("**Simulated AI recommendations**")
                        st.markdown(sim_data.get("recommendations", ""))
                else:
                    st.error(f"Simulation failed: {sim_resp.text}")


# --------------------------------------------------------------------------
# MODULE 3 — AI OUTREACH GENERATION
# --------------------------------------------------------------------------
def render_outreach():
    st.markdown('<div class="sg-page-title">AI Outreach Generation</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sg-page-subtitle">Generate personalized Cold Emails and Follow-up Emails using AI.</div>',
        unsafe_allow_html=True,
    )

    try:
        leads = fetch_leads()
    except Exception as e:
        st.error(f"Could not load leads: {e}")
        return
    if not leads:
        st.warning("No leads found in the database yet. Add some leads first, "
                    "or run seed_data.py to insert sample leads.")
        return

    label_to_lead = {lead_label(l): l for l in leads}

    col1, col2 = st.columns([2, 1])
    with col1:
        selected_label = st.selectbox("Select Lead", list(label_to_lead.keys()))
        selected_lead_id = label_to_lead[selected_label]["lead_id"]
    with col2:
        email_type = st.selectbox("Email Type", ["cold_email", "follow_up"],
                                   format_func=lambda x: "Cold Email" if x == "cold_email" else "Follow-up Email")

    col3, col4 = st.columns([1, 1])
    with col3:
        tone = st.selectbox("Tone", ["professional", "friendly", "direct", "consultative"])
    with col4:
        extra_context = st.text_input("Extra context (optional)", placeholder="e.g. mention their recent funding round")

    if "generated_email" not in st.session_state:
        st.session_state.generated_email = None

    if st.button("✨ Generate Email", type="primary"):
        with st.spinner("Generating personalized email..."):
            try:
                payload = {
                    "lead_id": selected_lead_id, "email_type": email_type,
                    "tone": tone, "extra_context": extra_context or None,
                }
                resp = api_post("/outreach/generate", json=payload)
                if resp.status_code != 200:
                    st.error(f"Generation failed: {safe_json(resp).get('detail', resp.text)}")
                else:
                    st.session_state.generated_email = safe_json(resp)
            except requests.exceptions.Timeout:
                st.error("The AI took too long to respond (timed out after 30s). Try again.")
            except requests.exceptions.ConnectionError:
                st.error("Lost connection to the backend mid-request. Is it still running?")
            except Exception as e:
                st.error(f"Request failed: {e}")

    if st.session_state.generated_email:
        st.markdown("---")
        st.subheader("Generated Email")
        subject = st.text_input("Subject", value=st.session_state.generated_email["subject"])
        body = st.text_area("Body", value=st.session_state.generated_email["body"], height=220)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 Save as Draft"):
                _save_campaign(selected_lead_id, email_type, tone, subject, body, "draft")
        with c2:
            if st.button("📤 Save & Mark Sent"):
                _save_campaign(selected_lead_id, email_type, tone, subject, body, "sent")

    st.markdown("---")
    st.subheader("Outreach History for this Lead")
    try:
        history = api_get(f"/outreach/history/{selected_lead_id}").json()
    except Exception:
        history = []

    if not history:
        st.caption("No outreach sent to this lead yet.")
    else:
        for c in history:
            status_emoji = "✅" if c["campaign_status"] == "sent" else "📝"
            with st.expander(f"{status_emoji} {c['email_subject']}  ·  {c['email_type']}  ·  {c['campaign_status']}"):
                st.write(c["email_content"])


def _save_campaign(lead_id, email_type, tone, subject, body, status):
    try:
        payload = {
            "lead_id": lead_id, "email_type": email_type, "tone": tone,
            "subject": subject, "body": body, "status": status,
        }
        resp = api_post("/outreach/save", json=payload)
        if resp.status_code == 200:
            st.markdown(f'<div class="sg-success-box">Saved as {status}.</div>', unsafe_allow_html=True)
        else:
            st.error(f"Save failed: {resp.text}")
    except Exception as e:
        st.error(f"Save failed: {e}")


# --------------------------------------------------------------------------
# MODULE 5 — SALES INTERACTIONS / CONVERSATION INTELLIGENCE
# --------------------------------------------------------------------------
def render_sales_interactions():
    st.markdown('<div class="sg-page-title">Sales Interactions</div>', unsafe_allow_html=True)
    st.markdown('<div class="sg-page-subtitle">Log, review, and analyze every touchpoint with your prospects.</div>', unsafe_allow_html=True)

    try:
        leads = fetch_leads()
    except Exception as e:
        st.error(f"Could not load leads: {e}")
        return
    if not leads:
        st.info("No leads yet. Add one from the 'Add Lead' page first.")
        return

    label_to_lead = {lead_label(l): l for l in leads}
    selected_label = st.selectbox("Select a lead", list(label_to_lead.keys()), key="ci_lead_select")
    lead = label_to_lead[selected_label]
    lead_id = lead["lead_id"]

    # ── AI Summary banner ───────────────────────────────────────────────────
    col_hdr, col_ai = st.columns([3, 1])
    with col_hdr:
        st.markdown(f"### {lead['company_name']} — Interaction Log")
    with col_ai:
        if st.button("🤖 AI Conversation Summary", type="primary", key="ai_sum_btn"):
            with st.spinner("Generating AI summary..."):
                try:
                    resp = api_post(f"/conversation/summarize/{lead_id}")
                    if resp.status_code == 200:
                        st.session_state["ci_summary"] = resp.json()
                    else:
                        st.error(f"Summary failed: {resp.text}")
                except Exception as exc:
                    st.error(f"Request failed: {exc}")

    if st.session_state.get("ci_summary") and st.session_state["ci_summary"]["lead_id"] == lead_id:
        sd = st.session_state["ci_summary"]
        with st.expander("📋 AI Conversation Summary", expanded=True):
            st.caption(f"{sd['total_interactions']} interaction(s) analysed · Generated {sd['generated_at'][:19].replace('T',' ')} UTC")
            st.markdown(sd["summary"])

    st.markdown("---")

    # ── Fetch interactions ───────────────────────────────────────────────────
    try:
        interactions = api_get(f"/conversation/{lead_id}").json()
    except Exception:
        interactions = []

    # ── Log new interaction ──────────────────────────────────────────────────
    with st.expander("➕ Log a New Interaction", expanded=not interactions):
        ITYPES = ["Call", "Email", "Meeting", "Note", "Demo",
                  "LinkedIn", "Website Visit", "Email Reply", "Email Opened"]
        with st.form("log_new_interaction_form"):
            c1, c2 = st.columns(2)
            with c1:
                itype   = st.selectbox("Interaction Type", ITYPES)
                summary = st.text_area("Summary", height=100)
            with c2:
                action_items = st.text_input("Action Items (optional)")
                log_date_str = st.text_input("Date (optional, YYYY-MM-DD)", placeholder="leave blank for today")
            log_btn = st.form_submit_button("📝 Log Interaction", type="primary")

        if log_btn:
            payload: dict = {
                "lead_id": lead_id,
                "interaction_type": itype,
                "summary": summary,
                "action_items": action_items or None,
            }
            if log_date_str.strip():
                try:
                    payload["interaction_date"] = log_date_str.strip() + "T00:00:00"
                except ValueError:
                    pass
            resp = api_post("/conversation/log", json=payload)
            if resp.status_code == 200:
                st.success("Interaction logged!")
                st.session_state.pop("ci_summary", None)   # invalidate stale summary
                st.rerun()
            else:
                st.error(f"Failed: {resp.text}")

    # ── Interaction cards ────────────────────────────────────────────────────
    if not interactions:
        st.caption("No interactions logged yet for this lead.")
    else:
        st.caption(f"{len(interactions)} interaction(s) — most recent first")

        for ix in interactions:
            date_label = (ix.get("interaction_date") or "")[:10] or "No date"
            itype_label = ix.get("interaction_type") or "Unknown"

            TYPE_EMOJI = {
                "Call": "📞", "Email": "✉️", "Meeting": "🤝", "Note": "📝",
                "Demo": "🖥️", "LinkedIn": "💼", "Website Visit": "🌐",
                "Email Reply": "↩️", "Email Opened": "👁️",
            }
            emoji = TYPE_EMOJI.get(itype_label, "📌")

            with st.expander(f"{emoji} {itype_label} · {date_label}"):
                edit_key = f"edit_mode_{ix['interaction_id']}"
                if edit_key not in st.session_state:
                    st.session_state[edit_key] = False

                if st.session_state[edit_key]:
                    # ── Edit form ────────────────────────────────────────
                    with st.form(f"edit_form_{ix['interaction_id']}"):
                        new_type    = st.selectbox("Type", ITYPES,
                                                   index=ITYPES.index(itype_label) if itype_label in ITYPES else 0)
                        new_summary = st.text_area("Summary", value=ix.get("summary") or "")
                        new_items   = st.text_input("Action Items", value=ix.get("action_items") or "")
                        c_save, c_cancel = st.columns(2)
                        save_edit   = c_save.form_submit_button("💾 Save", type="primary")
                        cancel_edit = c_cancel.form_submit_button("Cancel")

                    if save_edit:
                        resp = api_put(f"/conversation/{ix['interaction_id']}",
                                       json={"interaction_type": new_type,
                                             "summary": new_summary,
                                             "action_items": new_items or None})
                        if resp.status_code == 200:
                            st.success("Updated!")
                            st.session_state[edit_key] = False
                            st.rerun()
                        else:
                            st.error(f"Update failed: {resp.text}")

                    if cancel_edit:
                        st.session_state[edit_key] = False
                        st.rerun()

                else:
                    # ── Read-only view ────────────────────────────────────
                    st.write(ix.get("summary") or "No summary.")
                    if ix.get("action_items"):
                        st.caption(f"⚡ Action items: {ix['action_items']}")

                    col_edit, col_del, _ = st.columns([1, 1, 4])
                    if col_edit.button("✏️ Edit", key=f"edit_btn_{ix['interaction_id']}"):
                        st.session_state[edit_key] = True
                        st.rerun()

                    if col_del.button("🗑️ Delete", key=f"del_btn_{ix['interaction_id']}"):
                        resp = api_delete(f"/conversation/{ix['interaction_id']}")
                        if resp.status_code == 200:
                            st.success("Deleted.")
                            st.rerun()
                        else:
                            st.error(f"Delete failed: {resp.text}")


# --------------------------------------------------------------------------
# MODULE 6 — DASHBOARD & ANALYTICS
# --------------------------------------------------------------------------
def _kpi_card(label: str, value, sub: str = "", color: str = "#38bdf8") -> str:
    return (
        f'<div style="background:#161923;border:1px solid #262730;border-radius:10px;'
        f'padding:18px 22px;margin-bottom:4px;">'
        f'<div style="font-size:12px;color:#9ca3af;letter-spacing:1px;text-transform:uppercase">{label}</div>'
        f'<div style="font-size:34px;font-weight:800;color:{color};margin:4px 0">{value}</div>'
        f'<div style="font-size:12px;color:#6b7280">{sub}</div>'
        f'</div>'
    )


def render_dashboard():
    st.markdown('<div class="sg-page-title">Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sg-page-subtitle">Real-time sales analytics and pipeline overview.</div>',
                unsafe_allow_html=True)

    # ── Fetch all data ───────────────────────────────────────────────────────
    try:
        summary      = api_get("/dashboard/summary").json()
        pipeline     = api_get("/dashboard/pipeline").json()
        score_dist   = api_get("/dashboard/scoring-distribution").json()
        outreach     = api_get("/dashboard/outreach-stats").json()
        top_leads    = api_get("/dashboard/top-leads").json()
        timeline     = api_get("/dashboard/activity-timeline").json()
    except Exception as e:
        st.error(f"Could not load dashboard data: {e}")
        return

    # ── KPI Cards ────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(_kpi_card("Total Leads", summary.get("total_leads", 0),
                               f"{summary.get('scored_leads', 0)} scored"), unsafe_allow_html=True)
    with k2:
        qualified = summary.get("leads_by_status", {}).get("Qualified", 0)
        st.markdown(_kpi_card("Qualified Leads", qualified,
                               "in Qualified stage", color="#22c55e"), unsafe_allow_html=True)
    with k3:
        st.markdown(_kpi_card("Outreach Sent", outreach.get("sent", 0),
                               f"{outreach.get('reached_leads', 0)} leads reached",
                               color="#a78bfa"), unsafe_allow_html=True)
    with k4:
        avg = summary.get("avg_score", 0)
        st.markdown(_kpi_card("Avg Lead Score", avg,
                               "across all scored leads",
                               color="#f59e0b"), unsafe_allow_html=True)

    st.markdown("")

    # ── Row 1: Pipeline funnel + Score distribution donut ───────────────────
    col_pipe, col_donut = st.columns([1, 1])

    with col_pipe:
        st.markdown("#### 🏗️ Pipeline Funnel")
        if pipeline:
            stages = [p["stage"] for p in pipeline]
            counts = [p["count"] for p in pipeline]
            fig_pipe = go.Figure(go.Bar(
                x=stages,
                y=counts,
                marker_color=[
                    "#38bdf8", "#818cf8", "#a78bfa",
                    "#f59e0b", "#fb923c", "#22c55e", "#ef4444",
                ][:len(stages)],
                text=counts,
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>%{y} leads<extra></extra>",
            ))
            fig_pipe.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#e6e6e6",
                xaxis=dict(showgrid=False, tickangle=-20),
                yaxis=dict(showgrid=True, gridcolor="#262730"),
                margin=dict(l=10, r=10, t=10, b=50),
                height=280,
            )
            st.plotly_chart(fig_pipe, use_container_width=True)
        else:
            st.caption("No pipeline data yet.")

    with col_donut:
        st.markdown("#### 🥇 Score Tiers")
        tiers = score_dist.get("tier_breakdown", {})
        total_scored = score_dist.get("total_scored", 0)
        if total_scored:
            TIER_COLORS = {
                "Platinum": "#e2e8f0",
                "Gold":     "#f59e0b",
                "Silver":   "#94a3b8",
                "Bronze":   "#b45309",
                "Low Priority": "#374151",
            }
            tier_labels = list(tiers.keys())
            tier_vals   = list(tiers.values())
            tier_colors = [TIER_COLORS.get(t, "#6b7280") for t in tier_labels]

            fig_donut = go.Figure(go.Pie(
                labels=tier_labels,
                values=tier_vals,
                hole=0.55,
                marker_colors=tier_colors,
                textinfo="label+percent",
                textfont_size=12,
                hovertemplate="<b>%{label}</b><br>%{value} leads (%{percent})<extra></extra>",
            ))
            fig_donut.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#e6e6e6",
                margin=dict(l=0, r=0, t=10, b=10),
                height=280,
                showlegend=True,
                legend=dict(font_color="#9ca3af"),
                annotations=[dict(
                    text=f"<b>{total_scored}</b><br>scored",
                    x=0.5, y=0.5, font_size=14, font_color="#f5f5f5",
                    showarrow=False
                )],
            )
            st.plotly_chart(fig_donut, use_container_width=True)
        else:
            st.caption("No scored leads yet. Visit Lead Scoring to generate scores.")

    st.markdown("---")

    # ── Row 2: Industry breakdown + Outreach breakdown ───────────────────────
    col_ind, col_out = st.columns([1, 1])

    with col_ind:
        st.markdown("#### 🏭 Leads by Industry")
        industries = summary.get("leads_by_industry", [])
        if industries:
            ind_names  = [i["industry"] for i in industries]
            ind_counts = [i["count"]    for i in industries]
            fig_ind = go.Figure(go.Bar(
                y=ind_names,
                x=ind_counts,
                orientation="h",
                marker_color="#38bdf8",
                text=ind_counts,
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>%{x} leads<extra></extra>",
            ))
            fig_ind.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#e6e6e6",
                xaxis=dict(showgrid=True, gridcolor="#262730"),
                yaxis=dict(showgrid=False, autorange="reversed"),
                margin=dict(l=10, r=40, t=10, b=10),
                height=280,
            )
            st.plotly_chart(fig_ind, use_container_width=True)
        else:
            st.caption("No industry data yet.")

    with col_out:
        st.markdown("#### 📧 Outreach Overview")
        if outreach.get("total", 0):
            out_labels = ["Sent", "Draft"]
            out_vals   = [outreach.get("sent", 0), outreach.get("draft", 0)]
            fig_out = go.Figure(go.Pie(
                labels=out_labels,
                values=out_vals,
                hole=0.45,
                marker_colors=["#22c55e", "#6b7280"],
                textinfo="label+value",
                hovertemplate="<b>%{label}</b><br>%{value} campaigns<extra></extra>",
            ))
            fig_out.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#e6e6e6",
                margin=dict(l=0, r=0, t=10, b=10),
                height=280,
                legend=dict(font_color="#9ca3af"),
            )
            st.plotly_chart(fig_out, use_container_width=True)

            by_type = outreach.get("by_type", {})
            if by_type:
                st.caption("By email type: " + "  |  ".join(f"{k}: {v}" for k, v in by_type.items()))
        else:
            st.caption("No outreach campaigns yet.")

    st.markdown("---")

    # ── Row 3: Top leads leaderboard ─────────────────────────────────────────
    st.markdown("#### 🏆 Top Leads by Score")
    if top_leads:
        TIER_BADGE = {
            "Platinum": "⬜ Platinum",
            "Gold":     "🥇 Gold",
            "Silver":   "🥈 Silver",
            "Bronze":   "🥉 Bronze",
            "Low Priority": "⬛ Low",
        }
        table_rows = [
            {
                "Company":        r["company_name"],
                "Industry":       r.get("industry") or "—",
                "Segment":        r.get("segment") or "—",
                "Stage":          r.get("lead_status") or "—",
                "Score":          r["score"],
                "Tier":           TIER_BADGE.get(r["classification"], r["classification"]),
                "Confidence %":   r.get("confidence", 0),
            }
            for r in top_leads
        ]
        st.dataframe(table_rows, use_container_width=True, hide_index=True)
    else:
        st.caption("No scored leads yet.")

    st.markdown("---")

    # ── Row 4: Activity timeline ─────────────────────────────────────────────
    st.markdown("#### ⏱️ Recent Activity")
    if timeline:
        TYPE_EMOJI = {
            "Call": "📞", "Email": "✉️", "Meeting": "🤝", "Note": "📝",
            "Demo": "🖥️", "LinkedIn": "💼", "Website Visit": "🌐",
            "Email Reply": "↩️", "Email Opened": "👁️",
        }
        for item in timeline:
            date_str  = (item.get("interaction_date") or "")[:10] or "Unknown date"
            itype     = item.get("interaction_type") or "Note"
            emoji     = TYPE_EMOJI.get(itype, "📌")
            company   = item.get("company_name", "Unknown")
            summary_t = item.get("summary") or "No summary."
            st.markdown(
                f"{emoji} **{company}** · `{itype}` · {date_str}  "
                f"<span style='color:#9ca3af;font-size:13px'>{summary_t[:100]}</span>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("No activity recorded yet.")


# --------------------------------------------------------------------------
# ROUTER
# --------------------------------------------------------------------------
if page == "Lead Management":
    render_lead_management()
elif page == "Add Lead":
    render_add_lead()
elif page == "Lead Intelligence":
    render_lead_intelligence()
elif page == "AI Outreach":
    render_outreach()
elif page == "Lead Scoring":
    render_lead_scoring()
elif page == "Dashboard":
    render_dashboard()
elif page == "Sales Interactions":
    render_sales_interactions()
