"""资料预览生成服务测试"""
from pathlib import Path

import fitz

from app.core.config import settings
from app.models.entities import Material, MaterialPreview, StoredFile


def _write_pdf(object_key: str, text: str = "AI literacy course summary sample") -> Path:
    """写入可抽取文本的简易 PDF。

    测试使用 ASCII 文本，避免本机默认字体无法嵌入中文导致提取为空点号。
    """
    target = Path(settings.local_upload_dir) / object_key
    target.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(target)
    doc.close()
    return target


def _stored_pdf(db_session, object_key: str = "course/summary-demo.pdf") -> StoredFile:
    _write_pdf(object_key)
    stored = StoredFile(
        biz_type="material",
        storage_provider="local",
        bucket_name="",
        object_key=object_key,
        original_name="summary-demo.pdf",
        stored_name="summary-demo.pdf",
        content_type="application/pdf",
        extension=".pdf",
        size_bytes=1024,
        created_by="T001",
    )
    db_session.add(stored)
    db_session.commit()
    db_session.refresh(stored)
    return stored


def test_ensure_material_preview_creates_pending_record(db_session):
    from app.services.material_preview_service import ensure_material_preview

    material = Material(course_id=1, type="pdf", title="PDF 资料", file_id=None)
    db_session.add(material)
    db_session.commit()
    db_session.refresh(material)

    preview = ensure_material_preview(db_session, material.id)

    assert preview.material_id == material.id
    assert preview.status == "pending"


def test_mark_material_preview_failed_records_message(db_session):
    from app.services.material_preview_service import mark_material_preview_failed

    material = Material(course_id=1, type="pdf", title="PDF 资料", file_id=None)
    db_session.add(material)
    db_session.commit()
    db_session.refresh(material)

    preview = mark_material_preview_failed(db_session, material.id, "解析失败")

    assert preview.status == "failed"
    assert preview.error_message == "解析失败"


def test_generate_preview_rejects_missing_file(db_session):
    from app.services.material_preview_service import generate_material_preview

    material = Material(course_id=1, type="pdf", title="PDF 资料", file_id=None)
    db_session.add(material)
    db_session.commit()
    db_session.refresh(material)

    preview = generate_material_preview(db_session, material.id)

    assert preview.status == "failed"
    assert "文件不存在" in preview.error_message


def test_generate_pdf_preview_extracts_summary(db_session):
    from app.services.material_preview_service import generate_material_preview

    stored = _stored_pdf(db_session)
    material = Material(course_id=1, type="pdf", title="PDF 摘要资料", file_id=stored.id)
    db_session.add(material)
    db_session.commit()
    db_session.refresh(material)

    preview = generate_material_preview(db_session, material.id)

    assert preview.status == "ready"
    assert "AI literacy course summary sample" in (preview.summary or "")
    assert preview.page_count == 1
    assert preview.cover_file_id is not None


def test_bootstrap_material_preview_generates_pdf_summary(db_session):
    from app.services.material_preview_service import bootstrap_material_preview

    stored = _stored_pdf(db_session, object_key="course/bootstrap-summary.pdf")
    material = Material(course_id=1, type="pdf", title="创建即摘要", file_id=stored.id)
    db_session.add(material)
    db_session.commit()
    db_session.refresh(material)

    preview = bootstrap_material_preview(db_session, material)

    assert preview.status == "ready"
    assert "AI literacy course summary sample" in (preview.summary or "")


def test_hydrate_material_preview_for_read_generates_pending_pdf(db_session):
    from app.services.material_preview_service import hydrate_material_preview_for_read
    from app.services.material_service import format_material_preview_for_material

    stored = _stored_pdf(db_session, object_key="course/hydrate-summary.pdf")
    material = Material(course_id=1, type="pdf", title="懒加载摘要", file_id=stored.id)
    db_session.add(material)
    db_session.flush()
    db_session.add(MaterialPreview(material_id=material.id, status="pending"))
    db_session.commit()
    db_session.refresh(material)

    hydrate_material_preview_for_read(db_session, material)
    data = format_material_preview_for_material(db_session, material)

    assert data is not None
    assert data["status"] == "ready"
    assert "AI literacy course summary sample" in data["summary"]


def test_hydrate_material_preview_skips_non_pdf(db_session):
    from app.services.material_preview_service import hydrate_material_preview_for_read

    material = Material(course_id=1, type="link", title="外链", url="https://example.com")
    db_session.add(material)
    db_session.commit()
    db_session.refresh(material)

    hydrate_material_preview_for_read(db_session, material)

    assert material.preview is None
