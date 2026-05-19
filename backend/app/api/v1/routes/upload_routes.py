"""File upload routes"""
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File

from app.core.security import get_current_user
from app.core.response import success
from app.core.exceptions import BusinessException
from app.core.upload_validation import validate_upload
from app.schemas.common import AuthUser

router = APIRouter(tags=["upload"])

UPLOAD_DIR = Path(__file__).resolve().parents[3] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload", summary="文件上传", description="上传图片、文档、视频或压缩包文件（最大 50MB），返回访问 URL")
async def upload_file(
    file: UploadFile = File(...),
    _: AuthUser = Depends(get_current_user),
):
    if not file.filename:
        raise BusinessException(400, "未选择文件")

    content = await file.read()
    err = validate_upload(file.filename, len(content))
    if err:
        raise BusinessException(400, err)

    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4().hex[:12]}{ext}"
    filepath = UPLOAD_DIR / filename

    with open(filepath, "wb") as f:
        f.write(content)

    return success({
        "url": f"/uploads/{filename}",
        "filename": file.filename,
        "size": len(content),
    })
