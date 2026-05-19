"""API v1 router aggregator"""
from fastapi import APIRouter

from app.api.v1.routes.auth_routes import router as auth_router
from app.api.v1.routes.chapter_routes import router as chapter_router
from app.api.v1.routes.material_routes import router as material_router
from app.api.v1.routes.question_routes import router as question_router
from app.api.v1.routes.quiz_routes import router as quiz_router
from app.api.v1.routes.project_routes import router as project_router
from app.api.v1.routes.teacher_routes import router as teacher_router
from app.api.v1.routes.portfolio_routes import router as portfolio_router
from app.api.v1.routes.upload_routes import router as upload_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(chapter_router)
api_router.include_router(material_router)
api_router.include_router(question_router)
api_router.include_router(quiz_router)
api_router.include_router(project_router)
api_router.include_router(teacher_router)
api_router.include_router(portfolio_router)
api_router.include_router(upload_router)
