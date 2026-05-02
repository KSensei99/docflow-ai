"""
DocFlow AI — Local Invoice Intelligence Pipeline
================================================
FastAPI application entry point.

Stack: FastAPI + Ollama (local LLM) + Qdrant (vector store) + Tesseract OCR
No cloud APIs. Everything runs locally.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.routers import documents, review, catalog
from app.services.llm import llm_service
from app.services.matcher import matcher


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: check services, init Qdrant collection."""
    logger.info("=" * 60)
    logger.info("DocFlow AI — Starting up")
    logger.info(f"  Ollama: {settings.ollama_base_url} (model: {settings.ollama_model})")
    logger.info(f"  Qdrant: {settings.qdrant_host}:{settings.qdrant_port}")
    logger.info(f"  Confidence threshold: {settings.confidence_threshold}")
    logger.info("=" * 60)

    # Init Qdrant collection
    try:
        matcher.init_collection()
    except Exception as e:
        logger.warning(f"Qdrant init skipped (not running?): {e}")

    # Health check Ollama
    ollama_ok = await llm_service.check_health()
    if not ollama_ok:
        logger.warning(
            "Ollama not reachable at startup. "
            "Make sure it's running and the model is pulled."
        )

    yield

    logger.info("DocFlow AI — Shutdown complete")


app = FastAPI(
    title="DocFlow AI",
    description=(
        "Local AI pipeline for invoice processing. "
        "OCR → LLM extraction → semantic catalog matching → confidence scoring. "
        "No cloud APIs — runs fully on-premise."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS (for local UI / n8n integration)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(documents.router)
app.include_router(review.router)
app.include_router(catalog.router)


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "DocFlow AI",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    ollama_ok = await llm_service.check_health()
    return {
        "api": "ok",
        "ollama": "ok" if ollama_ok else "unavailable",
        "catalog_items": matcher.catalog_count(),
        "upload_dir": str(settings.upload_dir),
        "output_dir": str(settings.output_dir),
    }
