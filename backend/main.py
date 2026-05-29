"""AI 通识课平台 — 后端服务
Layered architecture: routes → services → models (MySQL + SQLAlchemy)
支持多 worker 部署：seed 逻辑通过文件锁互斥，避免重复执行。
"""
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

if sys.platform != "win32":
    import fcntl

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.exceptions import BusinessException
from app.db.session import engine, Base
from app.db.schema_compat import ensure_schema_compatibility
from app.api.v1 import api_router

# ── logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ── seed 互斥锁 ──────────────────────────────────────────────────────────────
_SEED_LOCK_FILE = Path(__file__).resolve().parent / ".seed_lock"


def _seed_if_empty():
    """带文件锁的种子数据初始化，多 worker 下仅第一个 worker 执行。Windows 下无 fcntl，跳过锁。"""
    lock_fd = None
    locked = False
    if sys.platform != "win32":
        try:
            lock_fd = open(_SEED_LOCK_FILE, "w")
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except (IOError, OSError):
            logger.info("Seed lock held by another worker, skipping.")
            return

    try:
        from seed_data import seed
        from app.db.session import SessionLocal
        from app.models.entities import Course
        db = SessionLocal()
        try:
            count = db.query(Course).count()
            if count == 0:
                logger.info("Empty database, running seed...")
                seed()
            else:
                logger.info("Database already seeded, skipping.")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Seed error: {e}")
    finally:
        if locked and lock_fd:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()


# ── lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：建表 + 种子数据
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility(engine)
    logger.info(f"Database tables ready ({settings.database_url.split(':')[0]})")
    _seed_if_empty()

    yield  # 服务器运行中...

    # 关闭时：在此释放资源（如连接池等）

# ── app factory ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI 通识课平台 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
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
