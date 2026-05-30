"""文件上传路由"""
from fastapi import APIRouter, Depends, UploadFile, File

from app.core.security import get_current_user
from app.core.response import success
from app.core.exceptions import BusinessException
from app.core.upload_validation import validate_upload, detect_content_type
from app.db.session import get_db
from app.schemas.common import AuthUser
from app.services.file_service import (
    _get_adapter,
    create_stored_file_record,
    generate_object_key,
    get_active_storage_provider,
)

router = APIRouter(tags=["upload"])


@router.post("/upload", summary="文件上传", description="上传图片、文档、视频或压缩包文件，返回访问 URL")
async def upload_file(
    file: UploadFile = File(...),
    current_user: AuthUser = Depends(get_current_user),
    db=Depends(get_db),
):
    if not file.filename:
        raise BusinessException(400, "未选择文件")

    content = await file.read()
    err = validate_upload(file.filename, len(content), content=content)
    if err:
        raise BusinessException(400, err)

    content_type = detect_content_type(content, file.filename)
    object_key = generate_object_key(file.filename)

    adapter = _get_adapter()
    stored = adapter.save_bytes(content=content, object_key=object_key, content_type=content_type)

    stored_file = create_stored_file_record(
        db,
        biz_type="upload",
        original_name=file.filename,
        content_type=content_type,
        size_bytes=len(content),
        stored=stored,
        created_by=current_user.id,
    )
    db.commit()

    return success({
        "file_id": stored_file.id,
        "url": f"/api/files/{stored_file.id}",
        "filename": file.filename,
        "size": len(content),
        "content_type": content_type,
        "storage_provider": get_active_storage_provider(),
    })
