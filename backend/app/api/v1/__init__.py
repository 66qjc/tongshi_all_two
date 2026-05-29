"""API v1 router aggregator"""
from fastapi import APIRouter

from app.api.v1.routes.auth_routes import router as auth_router
from app.api.v1.routes.class_routes import router as class_router
from app.api.v1.routes.announcement_routes import router as announcement_router
from app.api.v1.routes.material_routes import router as material_router
from app.api.v1.routes.question_routes import router as question_router
from app.api.v1.routes.quiz_routes import router as quiz_router
from app.api.v1.routes.project_routes import router as project_router
from app.api.v1.routes.teacher_routes import router as teacher_router
from app.api.v1.routes.portfolio_routes import router as portfolio_router
from app.api.v1.routes.upload_routes import router as upload_router
from app.api.v1.routes.file_routes import router as file_router
from app.api.v1.routes.admin_routes import router as admin_router
from app.api.v1.routes.profile_routes import router as profile_router
from app.api.v1.routes.showcase_routes import router as showcase_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(class_router)
api_router.include_router(announcement_router)
api_router.include_router(material_router)
api_router.include_router(question_router)
api_router.include_router(quiz_router)
api_router.include_router(project_router)
api_router.include_router(teacher_router)
api_router.include_router(portfolio_router)
api_router.include_router(upload_router)
api_router.include_router(file_router)
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(profile_router)
api_router.include_router(showcase_router)
