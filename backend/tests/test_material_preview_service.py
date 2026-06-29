"""资料预览生成服务测试"""
from app.models.entities import Material, MaterialPreview, StoredFile


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
