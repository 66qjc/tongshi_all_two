"""个人页面路由：错题本 + 收藏作品"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.response import success
from app.schemas.common import AuthUser
from app.services.quiz_service import get_wrong_questions
from app.services.project_service import list_liked_projects

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/wrong-questions", summary="错题本", description="返回当前用户最近一次答错的所有题目")
def wrong_questions(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """获取错题本：每道题只保留最近一次答题，且答错的题"""
    return success(get_wrong_questions(db, current_user.id))


@router.get("/liked-projects", summary="收藏作品", description="返回当前用户点赞（收藏）过的所有作品")
def liked_projects(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """获取用户收藏的作品列表"""
    return success(list_liked_projects(db, current_user.id))
