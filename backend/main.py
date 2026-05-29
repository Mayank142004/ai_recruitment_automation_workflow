"""
AI Recruitment Automation Workflow — FastAPI Application Entry Point

Endpoints:
    GET  /health           — Health check
    POST /api/submit       — Submit candidate application
    GET  /api/candidates   — List candidates with filters
    GET  /api/candidates/{id} — Get candidate detail
    PATCH /api/candidates/{id}/status — Manual status override
    POST /api/score/{id}   — Re-score candidate
    POST /api/notify/{id}  — Manually trigger notifications
    GET  /api/analytics    — Dashboard statistics
    GET  /api/roles        — List available roles
    GET  /api/task/{task_id} — Check async task status
"""

import os
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add parent directory to path so imports work correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from models.database import init_db
from routers import candidates, scoring, communications


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()
    yield


app = FastAPI(
    title="AI Recruitment Automation API",
    description="Automated hiring pipeline with AI scoring, NLP, and workflow automation. 100% free-tier APIs.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware — allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(candidates.router, prefix="/api", tags=["Candidates"])
app.include_router(scoring.router, prefix="/api", tags=["Scoring"])
app.include_router(communications.router, prefix="/api", tags=["Communications"])


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "ai-recruitment-api", "version": "1.0.0"}


@app.get("/api/health", tags=["Health"])
async def api_health_check():
    """API health check endpoint."""
    return {"status": "ok", "service": "ai-recruitment-api", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
