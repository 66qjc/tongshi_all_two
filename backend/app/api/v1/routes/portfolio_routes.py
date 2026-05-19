"""Portfolio routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.response import success
from app.core.exceptions import BusinessException
from app.schemas.common import AuthUser
from app.services.portfolio_service import get_portfolio

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("")
def portfolio(db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = get_portfolio(db, current_user.id)
    if not data:
        raise BusinessException(404, "用户不存在")
    return success(data)
