"""API v1 router aggregator"""
from fastapi import APIRouter

from app.api.v1.routes.auth_routes import router as auth_router
from app.api.v1.routes.class_routes import router as class_router
from app.api.v1.routes.announcement_routes import router as announcement_router
from app.api.v1.routes.material_routes import router as material_router
from app.api.v1.routes.question_routes import router as question_router
from app.api.v1.routes.course_routes import router as course_router
from app.api.v1.routes.quiz_routes import router as quiz_router
from app.api.v1.routes.project_routes import router as project_router
from app.api.v1.routes.teacher_routes import router as teacher_router
from app.api.v1.routes.portfolio_routes import router as portfolio_router
from app.api.v1.routes.upload_routes import router as upload_router
from app.api.v1.routes.file_routes import router as file_router
from app.api.v1.routes.admin_routes import router as admin_router
from app.api.v1.routes.admin_public_course_routes import router as admin_public_course_router
from app.api.v1.routes.profile_routes import router as profile_router
from app.api.v1.routes.showcase_routes import router as showcase_router
from app.api.v1.routes.stage_routes import router as stage_router
from app.api.v1.routes.notification_routes import router as notification_router
from app.api.v1.routes.public_learning_routes import router as public_learning_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(class_router)
api_router.include_router(announcement_router)
api_router.include_router(material_router)
api_router.include_router(question_router)
api_router.include_router(course_router)
api_router.include_router(quiz_router)
api_router.include_router(project_router)
api_router.include_router(teacher_router)
api_router.include_router(portfolio_router)
api_router.include_router(upload_router)
api_router.include_router(file_router)
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(admin_public_course_router, prefix="/admin", tags=["admin-public-courses"])
api_router.include_router(profile_router)
api_router.include_router(showcase_router)
api_router.include_router(stage_router)
api_router.include_router(notification_router)
api_router.include_router(public_learning_router)
