"""
main.py
FastAPI backend entrypoint for SalesGenie AI.
Run with:  uvicorn main:app --reload --port 8000
(or just run `python run_all.py` to launch backend + frontend together)
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from database.connection import init_db
from modules.module1_leads import router as leads_router
from modules.module2_intelligence import router as intelligence_router
from modules.module3_outreach import router as outreach_router
from modules.module4_scoring import router as scoring_router
from modules.module5_conversation import router as conversation_router
from modules.module6_dashboard import router as dashboard_router

app = FastAPI(title="SalesGenie AI Backend", version="0.1.0")

# Allow the Streamlit frontend (different port) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


logger = logging.getLogger("salesgenie")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Unexpected server error: {exc}"},
    )


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def root():
    return {"message": "SalesGenie AI backend is running."}


# Mount each module under its own prefix.
app.include_router(leads_router, prefix="/leads", tags=["Module 1 - Leads"])
app.include_router(intelligence_router, prefix="/intelligence", tags=["Module 2 - Intelligence"])
app.include_router(outreach_router, prefix="/outreach", tags=["Module 3 - Outreach"])
app.include_router(scoring_router, prefix="/scoring", tags=["Module 4 - Scoring"])
app.include_router(conversation_router, prefix="/conversation", tags=["Module 5 - Conversation"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["Module 6 - Dashboard"])
