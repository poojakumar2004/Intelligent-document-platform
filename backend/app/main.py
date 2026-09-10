import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse

from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.core.logging import logger
from backend.app.api.routes.documents import router as documents_router
from backend.app.repositories.document_repository import DocumentRepository

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="End-to-End AI-Powered Financial Document Extraction, Validation, and Dashboard Platform.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event
@app.on_event("startup")
def on_startup():
    logger.info("Initializing application services...")
    init_db()
    logger.info("Application started successfully.")

# Mount API routes
app.include_router(documents_router, prefix=settings.API_V1_STR)

# Frontend directories
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"
TEMPLATES_DIR = FRONTEND_DIR / "templates"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# UI Routes
@app.get("/", response_class=HTMLResponse)
def index_page(request: Request):
    """
    Renders main dashboard page.
    """
    documents = DocumentRepository.list_all()
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"documents": documents, "version": settings.VERSION}
    )

@app.get("/view/{document_name}", response_class=HTMLResponse)
def view_document_page(request: Request, document_name: str):
    """
    Renders detailed result view for a processed document.
    """
    doc = DocumentRepository.get_by_name(document_name)
    if not doc:
        return RedirectResponse(url="/?error=DocumentNotFound")
    return templates.TemplateResponse(
        request=request,
        name="document_result.html",
        context={"doc": doc, "version": settings.VERSION}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
