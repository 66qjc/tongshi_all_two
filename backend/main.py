"""AI 通识课平台 — 后端服务
Layered architecture: routes → services → models (MySQL + SQLAlchemy)
"""
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.exceptions import BusinessException
from app.db.session import engine, Base
from app.api.v1 import api_router

# ── logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ── app factory ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI 通识课平台 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(",") if settings.allowed_origins != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# ── exception handlers ───────────────────────────────────────────────────────
@app.exception_handler(BusinessException)
async def business_exception_handler(request: Request, exc: BusinessException):
    return JSONResponse(status_code=200, content={
        "code": exc.code, "data": None, "message": exc.message,
    })


@app.exception_handler(SQLAlchemyError)
async def db_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"Database error: {exc}")
    return JSONResponse(status_code=200, content={
        "code": 500, "data": None, "message": "服务器内部错误",
    })


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(status_code=200, content={
        "code": 500, "data": None, "message": "服务器内部错误",
    })

# ── init DB + seed on first run ───────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)
    logger.info(f"Database tables ready ({settings.database_url.split(':')[0]})")
    try:
        from seed_data import seed
        from app.db.session import SessionLocal
        from app.models.entities import Chapter
        db = SessionLocal()
        count = db.query(Chapter).count()
        if count == 0:
            logger.info("Empty database, running seed...")
            seed()
        db.close()
    except Exception as e:
        logger.warning(f"Seed skipped: {e}")

# ── routers ───────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api")

# ── health check ──────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/")
def root():
    return {"message": "AI 通识课平台 API", "docs": "/docs"}

# ── run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8050, reload=True)
