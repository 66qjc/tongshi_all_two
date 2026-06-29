"""课程资料预览生成服务。"""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.entities import Material, MaterialPreview, StoredFile
from app.services.file_service import _get_adapter, create_stored_file_record, generate_object_key
from app.services.storage_service import StoredObject


def ensure_material_preview(db: Session, material_id: int) -> MaterialPreview:
    """确保资料存在预览记录，不存在则创建 pending 记录。"""
    preview = db.query(MaterialPreview).filter(MaterialPreview.material_id == material_id).first()
    if preview:
        return preview
    preview = MaterialPreview(material_id=material_id, status="pending")
    db.add(preview)
    db.flush()
    return preview


def mark_material_preview_failed(db: Session, material_id: int, message: str) -> MaterialPreview:
    """将预览记录标记为失败并记录错误信息。"""
    preview = ensure_material_preview(db, material_id)
    preview.status = "failed"
    preview.error_message = message[:256]
    preview.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(preview)
    return preview


def generate_material_preview(db: Session, material_id: int) -> MaterialPreview:
    """根据资料类型生成预览（PDF 封面/摘要、视频封面/元数据）。"""
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material or not material.file_id:
        return mark_material_preview_failed(db, material_id, "资料文件不存在")
    stored = db.query(StoredFile).filter(StoredFile.id == material.file_id).first()
    if not stored:
        return mark_material_preview_failed(db, material_id, "资料文件不存在")

    preview = ensure_material_preview(db, material_id)
    preview.status = "processing"
    preview.error_message = ""
    db.commit()

    try:
        if material.type == "pdf":
            preview = _generate_pdf_preview(db, material, stored, preview)
        elif material.type == "video":
            preview = _generate_video_preview(db, material, stored, preview)
        else:
            preview.status = "ready"
        preview.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(preview)
        return preview
    except Exception as exc:
        return mark_material_preview_failed(db, material_id, f"预览生成失败：{exc}")


def _open_local_file_path(stored: StoredFile) -> Path:
    """打开本地存储文件的实际路径。"""
    if stored.storage_provider != "local":
        raise RuntimeError("当前试点仅支持本地文件预览生成")
    object_key = stored.object_key
    if object_key.startswith("/uploads/"):
        object_key = object_key[len("/uploads/"):]
    adapter = _get_adapter("local")
    file_path = Path(adapter.root_dir) / object_key
    if not file_path.is_file():
        raise RuntimeError("资料文件不存在")
    return file_path


def _save_preview_image(db: Session, image_bytes: bytes, filename: str, created_by: str) -> StoredFile:
    """将预览图片保存到存储并创建 StoredFile 记录。"""
    object_key = generate_object_key(filename)
    adapter = _get_adapter("local")
    stored_obj = adapter.save_bytes(content=image_bytes, object_key=object_key, content_type="image/png")
    return create_stored_file_record(
        db,
        biz_type="material_preview",
        original_name=filename,
        content_type="image/png",
        size_bytes=stored_obj.size_bytes,
        stored=stored_obj,
        created_by=created_by,
    )


def _generate_pdf_preview(db: Session, material: Material, stored: StoredFile, preview: MaterialPreview) -> MaterialPreview:
    """生成 PDF 预览：提取封面图片和前 3 页文字摘要。"""
    import fitz

    file_path = _open_local_file_path(stored)
    doc = fitz.open(file_path)
    try:
        preview.page_count = doc.page_count
        text_parts = []
        for page_index in range(min(3, doc.page_count)):
            text_parts.append(doc.load_page(page_index).get_text("text"))
        summary = " ".join(" ".join(text_parts).split())
        preview.summary = summary[:200] if summary else "该 PDF 暂未提取到可读文字。"

        if doc.page_count > 0:
            page = doc.load_page(0)
            pix = page.get_pixmap(matrix=fitz.Matrix(0.35, 0.35), alpha=False)
            cover = _save_preview_image(db, pix.tobytes("png"), f"material-{material.id}-cover.png", stored.created_by)
            preview.cover_file_id = cover.id
        preview.status = "ready"
        return preview
    finally:
        doc.close()


def _generate_video_preview(db: Session, material: Material, stored: StoredFile, preview: MaterialPreview) -> MaterialPreview:
    """生成视频预览：通过 ffprobe 读取元数据，ffmpeg 截取封面帧。"""
    file_path = _open_local_file_path(stored)
    probe = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration",
            "-of", "default=noprint_wrappers=1",
            str(file_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if probe.returncode != 0:
        raise RuntimeError("无法读取视频元数据")

    width = ""
    height = ""
    duration = 0
    for line in probe.stdout.splitlines():
        if line.startswith("width="):
            width = line.split("=", 1)[1]
        elif line.startswith("height="):
            height = line.split("=", 1)[1]
        elif line.startswith("duration="):
            raw = line.split("=", 1)[1]
            try:
                duration = int(float(raw))
            except ValueError:
                duration = 0
    preview.duration_seconds = duration
    preview.resolution = f"{width}x{height}" if width and height else ""

    object_key = generate_object_key(f"material-{material.id}-video-cover.png")
    adapter = _get_adapter("local")
    cover_path = Path(adapter.root_dir) / object_key
    cover_path.parent.mkdir(parents=True, exist_ok=True)
    capture = subprocess.run(
        [
            "ffmpeg",
            "-y", "-ss", "3",
            "-i", str(file_path),
            "-frames:v", "1",
            str(cover_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if capture.returncode == 0 and cover_path.is_file():
        stored_obj = StoredObject(
            storage_provider="local",
            bucket_name="",
            object_key=object_key,
            stored_name=Path(object_key).name,
            content_type="image/png",
            size_bytes=cover_path.stat().st_size,
        )
        cover = create_stored_file_record(
            db,
            biz_type="material_preview",
            original_name=f"material-{material.id}-video-cover.png",
            content_type="image/png",
            size_bytes=stored_obj.size_bytes,
            stored=stored_obj,
            created_by=stored.created_by,
        )
        preview.cover_file_id = cover.id

    preview.status = "ready"
    return preview
