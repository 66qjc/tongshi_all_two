# 课程大文件预览加速实施计划

> **给执行代理：** 必须使用 `subagent-driven-development`（推荐）或 `executing-plans` 逐任务执行本计划。步骤使用复选框（`- [x]`）跟踪。

**目标：** 落地课程大文件预览加速试点，让 1GB 级 PDF / 视频经后端鉴权后由 Nginx 传输，并在学生端、教师端展示图文资料卡片与站内预览。

**架构：** 后端新增 `MaterialPreview` 元数据和资料专用文件接口，资料文件访问走 Routes -> Services -> Models，鉴权通过后本地存储返回 `X-Accel-Redirect`，旧 `/api/files/{id}` 保留作为回退。前端复用统一 `MaterialPreviewDialog` 和资料预览数据，在学生课程详情、教师资料管理、教师课程详情三处展示同一套图文资料卡片。

**技术栈：** FastAPI、SQLAlchemy、MySQL/SQLite、Nginx `X-Accel-Redirect`、Vue 3 `<script setup lang="ts">`、Element Plus、PyMuPDF、ffmpeg/ffprobe、qpdf（可选）。

---

## 前置说明

本计划基于已敲定方案：

- `docs/superpowers/plans/2026-06-28-large-material-preview-pilot.md`

执行前必须注意：

- 当前工作区已有多处未提交改动，实施时不得回滚无关文件。
- 本计划涉及前端、后端、数据库结构和部署配置，必须分任务执行并逐步验证。
- 第一轮只支持本地存储的 `X-Accel-Redirect`，S3 / MinIO / CDN 只保留扩展点。
- 第一轮 PDF 站内预览可以先使用浏览器原生 PDF 预览或 `vue-pdf-embed`，目标是验证链路，不做复杂阅读器。
- 第一轮视频只做 `preload="metadata"` 和原文件播放，不做 HLS。

---

## 文件结构

### 后端新增/修改

- Modify: `backend/app/models/entities.py`
  - 新增 `MaterialPreview` ORM。
  - `Material` 增加 `preview` relationship。
- Modify: `backend/app/schemas/common.py`
  - 新增 `MaterialPreviewOut`。
  - `MaterialOut` 增加 `preview` 字段。
- Modify: `backend/app/db/schema_compat.py`
  - 兼容创建 `material_previews` 表和索引。
- Modify: `backend/requirements.txt`
  - 增加 `PyMuPDF`。
- Modify: `backend/app/services/file_service.py`
  - 增加本地对象 key 规范化和 `X-Accel-Redirect` 内部路径构造。
- Modify: `backend/app/services/material_service.py`
  - 增加资料文件访问权限校验、预览格式化和资料文件定位。
- Create: `backend/app/services/material_preview_service.py`
  - 生成 PDF 封面、PDF 摘要、视频封面和视频元数据。
- Modify: `backend/app/api/v1/routes/material_routes.py`
  - 新增 `GET /materials/{material_id}/file`。
  - 新增 `POST /materials/{material_id}/preview/rebuild`。
  - `MaterialOut` 返回预览数据。
- Modify: `backend/app/api/v1/routes/upload_routes.py`
  - 上传返回后不直接生成预览；资料创建后由资料路由触发。
- Modify: `deploy/nginx.conf`
  - 增加 `/_protected_uploads/` internal 目录。

### 后端测试

- Create: `backend/tests/test_material_file_acceleration.py`
  - 权限、`X-Accel-Redirect`、Range 相关头。
- Create: `backend/tests/test_material_preview_service.py`
  - PDF / 视频预览服务的可测分支。
- Modify: `backend/tests/test_schema_compat.py`
  - 校验 `material_previews` 表。
- Modify: `backend/tests/test_integration_bugfixes.py`
  - 如已有资料接口断言，需要补充 `preview` 字段兼容。

### 前端新增/修改

- Modify: `frontend/src/api/material.ts`
  - 增加 `MaterialPreview` 类型。
  - `Material` 增加 `preview`。
  - 增加 `getMaterialFileUrl(materialId)` 和 `rebuildMaterialPreview(materialId)`。
- Create: `frontend/src/components/common/MaterialPreviewDialog.vue`
  - 学生端和教师端共用 PDF / 视频预览弹窗。
- Create: `frontend/src/components/common/MaterialRichCard.vue`
  - 学生端和教师端共用图文资料卡片。
- Modify: `frontend/src/views/CourseDetailView.vue`
  - 使用 `MaterialRichCard` 展示阶段资料和未分类资料。
  - 接入 `MaterialPreviewDialog`。
- Modify: `frontend/src/views/teacher/TeacherMaterials.vue`
  - 从纯表格改为筛选 + 图文资料列表或混合列表。
  - 接入预览、重建预览。
- Modify: `frontend/src/views/teacher/TeacherCourseDetail.vue`
  - 阶段资料卡片升级为图文资料卡片。
  - 接入统一预览。
- Modify: `frontend/tests/local-file-preview-static.test.mjs`
  - 更新旧的“新窗口打开”断言。
- Create: `frontend/tests/material-preview-static.test.mjs`
  - 静态校验学生端和教师端图文卡片、统一预览入口。
- Modify: `frontend/tests/nginx-local-file-preview-static.test.mjs`
  - 校验 `/_protected_uploads/` internal 配置。

### 文档

- Modify: `docs/superpowers/project-map.md`
  - 增加 `MaterialPreview`、资料专用文件接口、教师端/学生端图文预览约定。
- Modify: `docs/superpowers/frontend-guidelines.md`
  - 增加教师端资料必须支持图文卡片和站内预览的验收规则。
- Modify: `backend/docs/项目修改记录.md`
  - 记录本次改动、验证命令、服务器部署影响。

---

## 任务 1：后端模型、Schema 和数据库兼容

**文件：**
- 修改：`backend/app/models/entities.py`
- 修改：`backend/app/schemas/common.py`
- 修改：`backend/app/db/schema_compat.py`
- 修改：`backend/tests/test_schema_compat.py`

- [x] **Step 1: 写 schema 兼容失败测试**

在 `backend/tests/test_schema_compat.py` 增加测试：

```python
def test_ensure_schema_compatibility_creates_material_previews_table():
    from sqlalchemy import create_engine, inspect
    from sqlalchemy.pool import StaticPool
    from app.db.schema_compat import ensure_schema_compatibility

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    with engine.begin() as conn:
        conn.exec_driver_sql("""
            CREATE TABLE materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER,
                type VARCHAR(16) NOT NULL,
                title VARCHAR(128) NOT NULL,
                url VARCHAR(512) DEFAULT '',
                file_id INTEGER
            )
        """)

    ensure_schema_compatibility(engine)

    inspector = inspect(engine)
    assert "material_previews" in inspector.get_table_names()
    columns = {col["name"] for col in inspector.get_columns("material_previews")}
    assert {
        "id",
        "material_id",
        "status",
        "cover_file_id",
        "summary",
        "page_count",
        "duration_seconds",
        "resolution",
        "error_message",
        "created_at",
        "updated_at",
    }.issubset(columns)
```

- [x] **Step 2: 运行测试确认失败**

运行：

```powershell
py -m pytest backend\tests\test_schema_compat.py::test_ensure_schema_compatibility_creates_material_previews_table -q
```

预期：失败，原因是 `material_previews` 表尚未创建。

- [x] **Step 3: 新增 ORM 模型**

在 `backend/app/models/entities.py` 的 `Material` 后增加 relationship：

```python
    preview = relationship(
        "MaterialPreview",
        back_populates="material",
        uselist=False,
        cascade="all, delete-orphan",
    )
```

在 `StoredFile` 前新增：

```python
class MaterialPreview(Base):
    """课程资料预览元数据。"""
    __tablename__ = "material_previews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    status = Column(String(16), nullable=False, default="pending")
    cover_file_id = Column(Integer, ForeignKey("stored_files.id"), nullable=True, index=True)
    summary = Column(Text, default="")
    page_count = Column(Integer, nullable=False, default=0)
    duration_seconds = Column(Integer, nullable=False, default=0)
    resolution = Column(String(32), default="")
    error_message = Column(String(256), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    material = relationship("Material", back_populates="preview")
    cover_file = relationship("StoredFile", foreign_keys=[cover_file_id])
```

- [x] **Step 4: 新增 Schema**

在 `backend/app/schemas/common.py` 的 `MaterialOut` 前增加：

```python
class MaterialPreviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str = "pending"
    cover_file_id: Optional[int] = None
    summary: str = ""
    page_count: int = 0
    duration_seconds: int = 0
    resolution: str = ""
    error_message: str = ""
```

并在 `MaterialOut` 增加：

```python
    preview: Optional[MaterialPreviewOut] = None
```

- [x] **Step 5: 增加兼容建表逻辑**

在 `backend/app/db/schema_compat.py` 中 `stored_files` 和 `materials` 均确认存在后加入：

```python
        inspector = inspect(conn)
        table_names = set(inspector.get_table_names())
        if "materials" in table_names and "material_previews" not in table_names:
            dialect_name = conn.dialect.name
            if dialect_name == "sqlite":
                conn.execute(text("""
                    CREATE TABLE material_previews (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        material_id INTEGER NOT NULL UNIQUE,
                        status VARCHAR(16) NOT NULL DEFAULT 'pending',
                        cover_file_id INTEGER,
                        summary TEXT DEFAULT '',
                        page_count INTEGER NOT NULL DEFAULT 0,
                        duration_seconds INTEGER NOT NULL DEFAULT 0,
                        resolution VARCHAR(32) DEFAULT '',
                        error_message VARCHAR(256) DEFAULT '',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(material_id) REFERENCES materials(id) ON DELETE CASCADE,
                        FOREIGN KEY(cover_file_id) REFERENCES stored_files(id)
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE material_previews (
                        id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        material_id INTEGER NOT NULL UNIQUE,
                        status VARCHAR(16) NOT NULL DEFAULT 'pending',
                        cover_file_id INTEGER NULL,
                        summary TEXT,
                        page_count INTEGER NOT NULL DEFAULT 0,
                        duration_seconds INTEGER NOT NULL DEFAULT 0,
                        resolution VARCHAR(32) DEFAULT '',
                        error_message VARCHAR(256) DEFAULT '',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        CONSTRAINT fk_material_previews_material_id
                            FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE CASCADE,
                        CONSTRAINT fk_material_previews_cover_file_id
                            FOREIGN KEY (cover_file_id) REFERENCES stored_files(id)
                    )
                """))
            conn.execute(text(
                "CREATE INDEX ix_material_previews_material_id ON material_previews (material_id)"
            ))
            conn.execute(text(
                "CREATE INDEX ix_material_previews_cover_file_id ON material_previews (cover_file_id)"
            ))
```

- [x] **Step 6: 运行测试确认通过**

运行：

```powershell
py -m pytest backend\tests\test_schema_compat.py::test_ensure_schema_compatibility_creates_material_previews_table -q
```

预期：通过。

---

## 任务 2：资料文件鉴权和 Nginx 内部跳转

**文件：**
- 新建：`backend/tests/test_material_file_acceleration.py`
- 修改：`backend/app/services/file_service.py`
- 修改：`backend/app/services/material_service.py`
- 修改：`backend/app/api/v1/routes/material_routes.py`
- 修改：`deploy/nginx.conf`
- 修改：`frontend/tests/nginx-local-file-preview-static.test.mjs`

- [x] **Step 1: 写后端失败测试**

创建 `backend/tests/test_material_file_acceleration.py`：

```python
from app.models.entities import Course, Material, StoredFile
from tests.conftest import auth_header


def _stored_file(db_session, created_by="T001", object_key="course/test.pdf", content_type="application/pdf"):
    stored = StoredFile(
        biz_type="material",
        storage_provider="local",
        bucket_name="",
        object_key=object_key,
        original_name="test.pdf",
        stored_name="test.pdf",
        content_type=content_type,
        extension=".pdf",
        size_bytes=1024,
        created_by=created_by,
    )
    db_session.add(stored)
    db_session.flush()
    return stored


def _material(db_session, course_id=1, file_id=None, type_="pdf"):
    material = Material(
        course_id=course_id,
        type=type_,
        title="大文件资料",
        url=f"/api/files/{file_id}" if file_id else "",
        size="1 KB",
        file_id=file_id,
    )
    db_session.add(material)
    db_session.commit()
    db_session.refresh(material)
    return material


def test_material_file_returns_x_accel_redirect_for_owner_teacher(client, db_session, teacher_token):
    stored = _stored_file(db_session)
    material = _material(db_session, file_id=stored.id)

    response = client.get(f"/api/materials/{material.id}/file", headers=auth_header(teacher_token))

    assert response.status_code == 200
    assert response.headers["x-accel-redirect"] == f"/_protected_uploads/{stored.object_key}"
    assert response.headers["content-type"].startswith("application/pdf")
    assert "inline" in response.headers["content-disposition"]


def test_material_file_allows_enrolled_student(client, db_session, student_token):
    stored = _stored_file(db_session)
    material = _material(db_session, file_id=stored.id)

    response = client.get(f"/api/materials/{material.id}/file", headers=auth_header(student_token))

    assert response.status_code == 200
    assert response.headers["x-accel-redirect"] == f"/_protected_uploads/{stored.object_key}"


def test_material_file_rejects_other_teacher(client, db_session, other_teacher_token):
    stored = _stored_file(db_session)
    material = _material(db_session, file_id=stored.id)

    response = client.get(f"/api/materials/{material.id}/file", headers=auth_header(other_teacher_token))
    data = response.json()

    assert data["code"] == 404


def test_material_file_rejects_student_not_in_course(client, db_session, student_token):
    other_course = db_session.query(Course).filter(Course.created_by == "T002").first()
    stored = _stored_file(db_session, created_by="T002", object_key="course/other.pdf")
    material = _material(db_session, course_id=other_course.id, file_id=stored.id)

    response = client.get(f"/api/materials/{material.id}/file", headers=auth_header(student_token))
    data = response.json()

    assert data["code"] == 404


def test_material_file_rejects_path_traversal_object_key(client, db_session, teacher_token):
    stored = _stored_file(db_session, object_key="../secret.pdf")
    material = _material(db_session, file_id=stored.id)

    response = client.get(f"/api/materials/{material.id}/file", headers=auth_header(teacher_token))
    data = response.json()

    assert data["code"] == 400
```

- [x] **Step 2: 运行测试确认失败**

运行：

```powershell
py -m pytest backend\tests\test_material_file_acceleration.py -q
```

预期：失败，原因是接口和服务方法尚不存在。

- [x] **Step 3: 增加内部路径构造**

在 `backend/app/services/file_service.py` 增加：

```python
def normalize_local_object_key(object_key: str) -> str:
    """规范化本地 object_key，禁止目录穿越。"""
    cleaned = object_key.replace("\\", "/").lstrip("/")
    if cleaned.startswith("uploads/"):
        cleaned = cleaned[len("uploads/"):]
    parts = [part for part in cleaned.split("/") if part]
    if any(part == ".." for part in parts):
        raise ValueError("文件路径不合法")
    return "/".join(parts)


def build_x_accel_redirect_path(object_key: str) -> str:
    """构建 Nginx 内部跳转路径。"""
    safe_key = normalize_local_object_key(object_key)
    return f"/_protected_uploads/{safe_key}"
```

- [x] **Step 4: 增加资料文件定位和权限服务**

在 `backend/app/services/material_service.py` 增加：

```python
from app.models.entities import StoredFile
from app.services.file_service import build_x_accel_redirect_path


def resolve_material_file_for_user(db: Session, material_id: int, user_id: str, role: str):
    """校验资料访问权限并返回资料、文件记录和 Nginx 内部路径。"""
    material = db.query(Material).join(Course, Course.id == Material.course_id).filter(Material.id == material_id).first()
    if not material:
        return None, None, ""
    if not can_view_course_materials(db, material.course_id, user_id, role):
        return None, None, ""
    if not material.file_id:
        raise BusinessException(404, "资料文件不存在")

    stored = db.query(StoredFile).filter(StoredFile.id == material.file_id).first()
    if not stored:
        raise BusinessException(404, "资料文件不存在")
    if stored.storage_provider != "local":
        raise BusinessException(400, "当前试点仅支持本地文件预览")
    try:
        accel_path = build_x_accel_redirect_path(stored.object_key)
    except ValueError:
        raise BusinessException(400, "资料文件路径不合法")
    return material, stored, accel_path
```

- [x] **Step 5: 新增路由**

在 `backend/app/api/v1/routes/material_routes.py` 增加 import：

```python
from urllib.parse import quote
from fastapi.responses import Response
from app.services.material_service import resolve_material_file_for_user
```

增加路由：

```python
@router.get("/materials/{material_id}/file", summary="预览资料文件", description="鉴权后通过 Nginx 内部跳转传输资料文件")
def open_material_file(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    material, stored, accel_path = resolve_material_file_for_user(db, material_id, current_user.id, current_user.role)
    if not material:
        raise BusinessException(404, "资料不存在")

    filename = stored.original_name or stored.stored_name or material.title or "material"
    encoded = quote(filename, encoding="utf-8")
    headers = {
        "X-Accel-Redirect": accel_path,
        "Content-Disposition": f"inline; filename*=UTF-8''{encoded}",
        "Accept-Ranges": "bytes",
        "Cache-Control": "private, max-age=0",
    }
    if stored.size_bytes:
        headers["Content-Length"] = str(stored.size_bytes)
    return Response(content=b"", media_type=stored.content_type or "application/octet-stream", headers=headers)
```

- [x] **Step 6: 修改 Nginx 配置**

在 `deploy/nginx.conf` 的 `server` 内增加：

```nginx
    location /_protected_uploads/ {
        internal;
        alias /var/www/tongshi/uploads/;
        sendfile on;
        tcp_nopush on;
        aio threads;
        add_header Accept-Ranges bytes;
        add_header Cache-Control "private, max-age=0";
    }
```

部署时将 `/var/www/tongshi/uploads/` 替换为服务器实际 `LOCAL_UPLOAD_DIR` 对应目录。

- [x] **Step 7: 更新 Nginx 静态测试**

修改 `frontend/tests/nginx-local-file-preview-static.test.mjs`，增加断言：

```javascript
assert.match(nginxConfig, /location\s+\/_protected_uploads\/\s*\{[\s\S]*internal;/, 'Nginx 应配置内部受保护上传目录。')
assert.match(nginxConfig, /location\s+\/_protected_uploads\/\s*\{[\s\S]*alias\s+\/var\/www\/tongshi\/uploads\//, 'Nginx 内部上传目录应映射到生产上传目录。')
assert.match(nginxConfig, /location\s+\/_protected_uploads\/\s*\{[\s\S]*sendfile\s+on;/, 'Nginx 内部文件传输应启用 sendfile。')
```

- [x] **Step 8: 运行后端和 Nginx 测试**

运行：

```powershell
py -m pytest backend\tests\test_material_file_acceleration.py -q
node frontend\tests\nginx-local-file-preview-static.test.mjs
```

预期：全部通过。

---

## 任务 3：资料预览生成服务

**文件：**
- 修改：`backend/requirements.txt`
- 新建：`backend/app/services/material_preview_service.py`
- 新建：`backend/tests/test_material_preview_service.py`
- 修改：`backend/app/services/material_service.py`
- 修改：`backend/app/api/v1/routes/material_routes.py`

- [x] **Step 1: 增加依赖**

在 `backend/requirements.txt` 增加：

```text
PyMuPDF
```

服务器另需安装：

```bash
ffmpeg
ffprobe
qpdf
```

- [x] **Step 2: 写失败测试**

创建 `backend/tests/test_material_preview_service.py`：

```python
from pathlib import Path

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
```

- [x] **Step 3: 运行测试确认失败**

运行：

```powershell
py -m pytest backend\tests\test_material_preview_service.py -q
```

预期：失败，服务文件不存在。

- [x] **Step 4: 实现预览服务基础状态**

创建 `backend/app/services/material_preview_service.py`：

```python
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
    preview = db.query(MaterialPreview).filter(MaterialPreview.material_id == material_id).first()
    if preview:
        return preview
    preview = MaterialPreview(material_id=material_id, status="pending")
    db.add(preview)
    db.flush()
    return preview


def mark_material_preview_failed(db: Session, material_id: int, message: str) -> MaterialPreview:
    preview = ensure_material_preview(db, material_id)
    preview.status = "failed"
    preview.error_message = message[:256]
    preview.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(preview)
    return preview


def generate_material_preview(db: Session, material_id: int) -> MaterialPreview:
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
```

- [x] **Step 5: 实现 PDF 预览**

在同一文件增加：

```python
def _open_local_file_path(stored: StoredFile) -> Path:
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
    object_key = generate_object_key(filename)
    adapter = _get_adapter("local")
    stored = adapter.save_bytes(content=image_bytes, object_key=object_key, content_type="image/png")
    return create_stored_file_record(
        db,
        biz_type="material_preview",
        original_name=filename,
        content_type="image/png",
        size_bytes=stored.size_bytes,
        stored=stored,
        created_by=created_by,
    )


def _generate_pdf_preview(db: Session, material: Material, stored: StoredFile, preview: MaterialPreview) -> MaterialPreview:
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
```

- [x] **Step 6: 实现视频预览**

在同一文件增加：

```python
def _generate_video_preview(db: Session, material: Material, stored: StoredFile, preview: MaterialPreview) -> MaterialPreview:
    file_path = _open_local_file_path(stored)
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,duration",
            "-of",
            "default=noprint_wrappers=1",
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
            "-y",
            "-ss",
            "3",
            "-i",
            str(file_path),
            "-frames:v",
            "1",
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
```

- [x] **Step 7: 资料创建后创建 pending 预览记录**

在 `backend/app/services/material_service.py` 的 `create_material` commit 前后加入：

```python
    db.add(material)
    db.flush()
    from app.services.material_preview_service import ensure_material_preview
    ensure_material_preview(db, material.id)
    db.commit()
```

避免重复 `db.add(material)` / `db.commit()`。

- [x] **Step 8: 新增重建预览路由**

在 `backend/app/api/v1/routes/material_routes.py` 增加：

```python
from app.services.material_preview_service import generate_material_preview
```

增加：

```python
@router.post("/materials/{material_id}/preview/rebuild", summary="重新生成资料预览")
def rebuild_material_preview(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("teacher")),
):
    material, _, _ = resolve_material_file_for_user(db, material_id, current_user.id, current_user.role)
    if not material:
        raise BusinessException(404, "资料不存在")
    preview = generate_material_preview(db, material_id)
    return success({
        "status": preview.status,
        "cover_file_id": preview.cover_file_id,
        "summary": preview.summary,
        "page_count": preview.page_count,
        "duration_seconds": preview.duration_seconds,
        "resolution": preview.resolution,
        "error_message": preview.error_message,
    })
```

- [x] **Step 9: 运行预览服务测试**

运行：

```powershell
py -m pytest backend\tests\test_material_preview_service.py -q
```

预期：通过。

---

## 任务 4：后端接口统一返回预览数据

**文件：**
- 修改：`backend/app/services/material_service.py`
- 修改：`backend/app/services/course_response_service.py`
- 修改：`backend/app/api/v1/routes/material_routes.py`
- 修改：`backend/tests/test_integration_bugfixes.py`
- 修改：`backend/tests/test_material_file_acceleration.py`

- [x] **Step 1: 新增格式化函数测试**

在 `backend/tests/test_material_file_acceleration.py` 增加：

```python
def test_course_contents_include_material_preview(client, db_session, student_token):
    from app.models.entities import MaterialPreview

    stored = _stored_file(db_session)
    material = _material(db_session, file_id=stored.id)
    preview = MaterialPreview(
        material_id=material.id,
        status="ready",
        summary="这是一段资料摘要",
        page_count=12,
    )
    db_session.add(preview)
    db_session.commit()

    response = client.get("/api/courses/1/contents", headers=auth_header(student_token))
    data = response.json()

    assert data["code"] == 0
    target = next(item for item in data["data"] if item["id"] == material.id)
    assert target["preview"]["status"] == "ready"
    assert target["preview"]["summary"] == "这是一段资料摘要"
    assert target["preview"]["page_count"] == 12
```

- [x] **Step 2: 运行测试确认失败**

运行：

```powershell
py -m pytest backend\tests\test_material_file_acceleration.py::test_course_contents_include_material_preview -q
```

预期：失败，`preview` 字段尚未返回。

- [x] **Step 3: 增加预览格式化函数**

在 `backend/app/services/material_service.py` 增加：

```python
def format_material_preview(preview) -> dict | None:
    if not preview:
        return None
    return {
        "status": preview.status,
        "cover_file_id": preview.cover_file_id,
        "summary": preview.summary or "",
        "page_count": preview.page_count or 0,
        "duration_seconds": preview.duration_seconds or 0,
        "resolution": preview.resolution or "",
        "error_message": preview.error_message or "",
    }
```

- [x] **Step 4: 更新各处 material 格式化**

在 `backend/app/api/v1/routes/material_routes.py` 的 `_format_material` 增加：

```python
        "preview": format_material_preview(m.preview),
```

并 import：

```python
from app.services.material_service import format_material_preview
```

在 `backend/app/services/course_response_service.py` 的 `_format_material` 增加同样字段，并 import：

```python
from app.services.material_service import format_material_preview
```

- [x] **Step 5: 运行后端相关测试**

运行：

```powershell
py -m pytest backend\tests\test_material_file_acceleration.py backend\tests\test_material_preview_service.py backend\tests\test_schema_compat.py -q
```

预期：通过。

---

## 任务 5：前端 API、统一卡片和预览弹窗

**文件：**
- 修改：`frontend/src/api/material.ts`
- 新建：`frontend/src/components/common/MaterialPreviewDialog.vue`
- 新建：`frontend/src/components/common/MaterialRichCard.vue`
- 新建：`frontend/tests/material-preview-static.test.mjs`

- [x] **Step 1: 写前端静态失败测试**

创建 `frontend/tests/material-preview-static.test.mjs`：

```javascript
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

const materialApi = read('src/api/material.ts')
const card = read('src/components/common/MaterialRichCard.vue')
const dialog = read('src/components/common/MaterialPreviewDialog.vue')
const courseDetail = read('src/views/CourseDetailView.vue')
const teacherMaterials = read('src/views/teacher/TeacherMaterials.vue')
const teacherCourseDetail = read('src/views/teacher/TeacherCourseDetail.vue')

assert.match(materialApi, /interface MaterialPreview/, '资料 API 应定义 MaterialPreview 类型。')
assert.match(materialApi, /preview\?: MaterialPreview/, 'Material 类型应包含 preview 字段。')
assert.match(materialApi, /\/materials\/\$\{materialId\}\/file/, '资料文件 URL 应使用资料专用文件接口。')
assert.match(materialApi, /preview\/rebuild/, '资料 API 应提供重建预览接口。')

assert.match(card, /coverUrl/, '图文资料卡片应展示封面。')
assert.match(card, /summaryText/, '图文资料卡片应展示摘要。')
assert.match(card, /预览生成中/, '图文资料卡片应展示预览生成中状态。')
assert.match(card, /预览生成失败/, '图文资料卡片应展示预览失败状态。')

assert.match(dialog, /<video/, '统一预览弹窗应支持视频。')
assert.match(dialog, /pdf/, '统一预览弹窗应支持 PDF。')
assert.match(dialog, /新窗口打开原文件/, '统一预览弹窗应保留新窗口打开入口。')

assert.match(courseDetail, /MaterialRichCard/, '学生课程详情应使用图文资料卡片。')
assert.match(courseDetail, /MaterialPreviewDialog/, '学生课程详情应使用统一预览弹窗。')
assert.match(teacherMaterials, /MaterialRichCard/, '教师资料管理应使用图文资料卡片或混合列表。')
assert.match(teacherMaterials, /rebuildMaterialPreview/, '教师资料管理应提供重建预览入口。')
assert.match(teacherCourseDetail, /MaterialRichCard/, '教师课程详情应使用图文资料卡片。')
assert.match(teacherCourseDetail, /MaterialPreviewDialog/, '教师课程详情应使用统一预览弹窗。')

console.log('material preview static checks passed')
```

- [x] **Step 2: 运行测试确认失败**

运行：

```powershell
node frontend\tests\material-preview-static.test.mjs
```

预期：失败，组件和 API 尚未实现。

- [x] **Step 3: 扩展 API 类型**

修改 `frontend/src/api/material.ts`：

```ts
export interface MaterialPreview {
  status: 'pending' | 'processing' | 'ready' | 'failed'
  cover_file_id?: number | null
  summary: string
  page_count: number
  duration_seconds: number
  resolution: string
  error_message: string
}
```

在 `Material` 增加：

```ts
  preview?: MaterialPreview | null
```

增加：

```ts
export function getMaterialFileUrl(materialId: number) {
  return `/api/materials/${materialId}/file`
}

export function rebuildMaterialPreview(materialId: number) {
  return http.post<any, MaterialPreview>(`/materials/${materialId}/preview/rebuild`)
}
```

- [x] **Step 4: 创建统一预览弹窗**

创建 `frontend/src/components/common/MaterialPreviewDialog.vue`：

```vue
<script setup lang="ts">
import { computed } from 'vue'
import type { Material } from '@/api/material'
import { getMaterialFileUrl } from '@/api/material'
import { resolveFileUrl } from '@/utils/url'

const props = defineProps<{
  visible: boolean
  material: Material | null
}>()

const emit = defineEmits<{ (e: 'update:visible', val: boolean): void }>()

const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val),
})

const previewUrl = computed(() => {
  if (!props.material) return ''
  return resolveFileUrl(getMaterialFileUrl(props.material.id))
})

const isVideo = computed(() => props.material?.type === 'video')
const isPdf = computed(() => props.material?.type === 'pdf')

function openInNewWindow() {
  if (previewUrl.value) window.open(previewUrl.value, '_blank', 'noopener')
}
</script>

<template>
  <el-dialog v-model="dialogVisible" :title="material?.title || '资料预览'" width="80%" destroy-on-close>
    <div v-if="material && previewUrl" class="material-preview-dialog">
      <video v-if="isVideo" class="preview-video" :src="previewUrl" controls preload="metadata" />
      <object v-else-if="isPdf" class="preview-pdf" :data="previewUrl" type="application/pdf">
        <div class="preview-fallback">浏览器无法直接预览 PDF，请使用新窗口打开原文件。</div>
      </object>
      <div v-else class="preview-fallback">该资料类型暂不支持站内预览。</div>
    </div>
    <div v-else class="preview-fallback">暂无可预览的资料文件。</div>
    <template #footer>
      <el-button @click="dialogVisible = false">关闭</el-button>
      <el-button type="primary" :disabled="!previewUrl" @click="openInNewWindow">新窗口打开原文件</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.material-preview-dialog {
  min-height: 60vh;
}

.preview-video,
.preview-pdf {
  width: 100%;
  height: 68vh;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-alt);
}

.preview-fallback {
  padding: 48px 0;
  text-align: center;
  color: var(--color-text-muted);
}
</style>
```

- [x] **Step 5: 创建图文资料卡片**

创建 `frontend/src/components/common/MaterialRichCard.vue`：

```vue
<script setup lang="ts">
import { computed } from 'vue'
import type { Material } from '@/api/material'
import { resolveFileUrl } from '@/utils/url'

const props = defineProps<{
  material: Material
  manage?: boolean
}>()

const emit = defineEmits<{
  (e: 'preview', material: Material): void
  (e: 'edit', material: Material): void
  (e: 'delete', material: Material): void
  (e: 'rebuild', material: Material): void
}>()

const coverUrl = computed(() => {
  const fileId = props.material.preview?.cover_file_id
  return fileId ? resolveFileUrl(`/api/files/${fileId}`) : ''
})

const summaryText = computed(() => {
  return props.material.preview?.summary || '该资料暂未生成摘要，可直接打开原文件查看。'
})

const metaText = computed(() => {
  const parts = [props.material.size]
  if (props.material.type === 'pdf' && props.material.preview?.page_count) {
    parts.push(`${props.material.preview.page_count} 页`)
  }
  if (props.material.type === 'video' && props.material.preview?.duration_seconds) {
    const minutes = Math.max(1, Math.round(props.material.preview.duration_seconds / 60))
    parts.push(`${minutes} 分钟`)
  }
  if (props.material.preview?.resolution) parts.push(props.material.preview.resolution)
  if (props.material.date) parts.push(props.material.date)
  return parts.filter(Boolean).join(' · ')
})

const statusText = computed(() => {
  const status = props.material.preview?.status
  if (status === 'ready') return '预览就绪'
  if (status === 'processing') return '预览生成中'
  if (status === 'failed') return '预览生成失败'
  return '预览生成中'
})
</script>

<template>
  <article class="material-rich-card">
    <div class="cover">
      <img v-if="coverUrl" :src="coverUrl" :alt="material.title" />
      <span v-else>{{ material.type === 'video' ? '视频' : 'PDF' }}</span>
    </div>
    <div class="body">
      <div class="title-row">
        <el-tag size="small" effect="plain">{{ material.type === 'video' ? '视频' : 'PDF' }}</el-tag>
        <el-tag size="small" :type="material.preview?.status === 'failed' ? 'danger' : 'info'" effect="plain">{{ statusText }}</el-tag>
      </div>
      <h3>{{ material.title }}</h3>
      <p class="summary">{{ summaryText }}</p>
      <p class="meta">{{ metaText }}</p>
      <p v-if="material.preview?.status === 'failed' && material.preview.error_message" class="error">
        {{ material.preview.error_message }}
      </p>
      <div class="actions">
        <el-button type="primary" size="small" @click="emit('preview', material)">预览</el-button>
        <template v-if="manage">
          <el-button size="small" @click="emit('edit', material)">编辑</el-button>
          <el-button size="small" @click="emit('rebuild', material)">重建预览</el-button>
          <el-button type="danger" text size="small" @click="emit('delete', material)">删除</el-button>
        </template>
      </div>
    </div>
  </article>
</template>

<style scoped>
.material-rich-card {
  display: grid;
  grid-template-columns: 132px minmax(0, 1fr);
  gap: 16px;
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-card);
}

.cover {
  aspect-ratio: 4 / 3;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: var(--radius-sm);
  background: var(--color-bg-alt);
  color: var(--color-text-muted);
  font-weight: 700;
}

.cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.body {
  min-width: 0;
}

.title-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

h3 {
  margin: 0 0 8px;
  font-size: 1rem;
  color: var(--color-text);
}

.summary {
  margin: 0 0 8px;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.meta,
.error {
  margin: 0 0 8px;
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

.error {
  color: var(--color-danger);
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

@media (max-width: 640px) {
  .material-rich-card {
    grid-template-columns: 1fr;
  }
}
</style>
```

- [x] **Step 6: 运行静态测试确认组件基础通过**

运行：

```powershell
node frontend\tests\material-preview-static.test.mjs
```

预期：仍可能因页面未接入而失败，但 API 和组件相关断言应通过。

---

## 任务 6：学生端课程详情接入图文卡片

**文件：**
- 修改：`frontend/src/views/CourseDetailView.vue`
- 修改：`frontend/tests/material-preview-static.test.mjs`

- [x] **Step 1: 接入组件**

在 `frontend/src/views/CourseDetailView.vue` 中增加：

```ts
import MaterialRichCard from '@/components/common/MaterialRichCard.vue'
import MaterialPreviewDialog from '@/components/common/MaterialPreviewDialog.vue'
import type { Material } from '@/api/material'
```

增加状态：

```ts
const previewVisible = ref(false)
const selectedMaterial = ref<Material | null>(null)

function previewMaterial(material: Material) {
  selectedMaterial.value = material
  previewVisible.value = true
}
```

- [x] **Step 2: 替换资料卡片模板**

将阶段资料中的 `.material-card` 替换为：

```vue
<MaterialRichCard
  v-for="m in stage.materials"
  :key="m.id"
  :material="m"
  @preview="previewMaterial"
/>
```

未分类资料同样替换。

在页面底部加入：

```vue
<MaterialPreviewDialog v-model:visible="previewVisible" :material="selectedMaterial" />
```

- [x] **Step 3: 清理旧 openMaterial 逻辑**

删除或停用 `openMaterial` 和 `materialUrl` 中只为旧卡片服务的点击逻辑。保留 `resolveFileUrl` import 仅在仍被使用时保留，否则删除。

- [x] **Step 4: 运行静态测试**

运行：

```powershell
node frontend\tests\material-preview-static.test.mjs
```

预期：学生端相关断言通过。

---

## 任务 7：教师端资料管理接入图文卡片

**文件：**
- 修改：`frontend/src/views/teacher/TeacherMaterials.vue`
- 修改：`frontend/tests/material-preview-static.test.mjs`

- [x] **Step 1: 接入组件和 API**

在 `frontend/src/views/teacher/TeacherMaterials.vue` 中增加：

```ts
import MaterialRichCard from '@/components/common/MaterialRichCard.vue'
import MaterialPreviewDialog from '@/components/common/MaterialPreviewDialog.vue'
import { rebuildMaterialPreview } from '@/api/material'
```

增加：

```ts
const previewVisible = ref(false)
const selectedMaterial = ref<Material | null>(null)

function previewMaterial(row: Material) {
  selectedMaterial.value = row
  previewVisible.value = true
}

async function handleRebuildPreview(row: Material) {
  try {
    await rebuildMaterialPreview(row.id)
    ElMessage.success('预览已重新生成')
    await loadMaterials()
  } catch {
    ElMessage.error('预览重建失败，请稍后重试')
  }
}
```

- [x] **Step 2: 替换资料主体展示**

保留筛选栏和分页，将 `el-table` 改为图文列表：

```vue
<div v-loading="loading" class="materials-rich-list">
  <MaterialRichCard
    v-for="row in materials"
    :key="row.id"
    :material="row"
    manage
    @preview="previewMaterial"
    @delete="handleDelete"
    @rebuild="handleRebuildPreview"
  />
</div>
```

如果仍需要编辑入口，补充 `@edit` 并实现或暂时不显示编辑按钮。第一轮教师资料管理现有页面没有编辑资料功能，只保留删除和重建预览即可；如使用 `MaterialRichCard` 的 `manage` 默认显示编辑，需要在组件中增加 `editable?: boolean` 控制，或者在本页面忽略 `edit` 事件并后续实现。

- [x] **Step 3: 增加弹窗**

模板底部加入：

```vue
<MaterialPreviewDialog v-model:visible="previewVisible" :material="selectedMaterial" />
```

- [x] **Step 4: 增加列表样式**

在 scoped style 增加：

```css
.materials-rich-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: var(--space-md);
  min-height: 240px;
}
```

- [x] **Step 5: 运行静态测试**

运行：

```powershell
node frontend\tests\material-preview-static.test.mjs
```

预期：教师资料管理相关断言通过。

---

## 任务 8：教师端课程详情接入图文卡片

**文件：**
- 修改：`frontend/src/views/teacher/TeacherCourseDetail.vue`
- 修改：`frontend/tests/material-preview-static.test.mjs`

- [x] **Step 1: 接入组件**

在 `frontend/src/views/teacher/TeacherCourseDetail.vue` 增加：

```ts
import MaterialRichCard from '@/components/common/MaterialRichCard.vue'
import MaterialPreviewDialog from '@/components/common/MaterialPreviewDialog.vue'
import { rebuildMaterialPreview, type Material } from '@/api/material'
```

增加状态和方法：

```ts
const previewVisible = ref(false)
const selectedMaterial = ref<Material | null>(null)

function previewMaterial(material: Material) {
  selectedMaterial.value = material
  previewVisible.value = true
}

async function handleRebuildPreview(material: Material) {
  try {
    await rebuildMaterialPreview(material.id)
    ElMessage.success('预览已重新生成')
    await loadCourse()
  } catch {
    ElMessage.error('预览重建失败，请稍后重试')
  }
}
```

- [x] **Step 2: 替换阶段资料卡片**

将原 `.material-card` 内容替换为：

```vue
<MaterialRichCard
  v-for="material in stage.materials"
  :key="material.id"
  :material="material"
  manage
  @preview="previewMaterial"
  @edit="openEditMaterial"
  @delete="handleDeleteMaterial"
  @rebuild="handleRebuildPreview"
/>
```

未分类资料同样替换。

- [x] **Step 3: 增加弹窗**

模板底部加入：

```vue
<MaterialPreviewDialog v-model:visible="previewVisible" :material="selectedMaterial" />
```

- [x] **Step 4: 运行静态测试**

运行：

```powershell
node frontend\tests\material-preview-static.test.mjs
```

预期：通过。

---

## 任务 9：更新旧静态测试和前端构建

**文件：**
- 修改：`frontend/tests/local-file-preview-static.test.mjs`
- 修改：`frontend/tests/material-preview-static.test.mjs`

- [x] **Step 1: 更新旧测试断言**

`frontend/tests/local-file-preview-static.test.mjs` 中旧断言：

```javascript
assert.match(courseDetail, /target="_blank"/, '学生课程资料应通过新窗口打开文件。')
assert.match(teacherMaterials, /window\.open\(url,\s*'_blank'/, '教师资料管理应通过新窗口打开文件。')
```

改为：

```javascript
assert.match(courseDetail, /MaterialPreviewDialog/, '学生课程资料应通过站内预览弹窗打开。')
assert.match(teacherMaterials, /MaterialPreviewDialog/, '教师资料管理应通过站内预览弹窗打开。')
```

旧 `/api/files/${id}` 断言改为同时接受资料专用接口：

```javascript
assert.match(courseDetail + teacherMaterials, /\/materials\/\$\{.*\}\/file|\/api\/materials\//, '课程资料应使用资料专用文件接口。')
```

- [x] **Step 2: 运行前端静态测试**

运行：

```powershell
node frontend\tests\local-file-preview-static.test.mjs
node frontend\tests\material-preview-static.test.mjs
node frontend\tests\nginx-local-file-preview-static.test.mjs
```

预期：通过。

- [x] **Step 3: 运行前端构建**

运行：

```powershell
cd frontend
npm run build
```

预期：通过，无 TypeScript 错误。

---

## 任务 10：文档同步和服务器部署说明

**文件：**
- 修改：`docs/superpowers/project-map.md`
- 修改：`docs/superpowers/frontend-guidelines.md`
- 修改：`backend/docs/项目修改记录.md`
- 修改：`docs/superpowers/plans/2026-06-28-large-material-preview-pilot.md`

- [x] **Step 1: 更新项目地图**

在 `docs/superpowers/project-map.md` 长期约定中补充：

```markdown
- 课程资料预览使用 `material_previews` 保存封面、摘要、页数、时长和处理状态。
- 课程资料大文件打开优先走 `/api/materials/{material_id}/file`，后端鉴权后由 Nginx 内部目录传输。
- 学生端和教师端资料展示统一使用图文资料卡片和站内预览；旧 `/api/files/{id}` 保留给图片、作品报告等通用文件访问。
```

- [x] **Step 2: 更新教师端前端验收**

在 `docs/superpowers/frontend-guidelines.md` 的资料管理规则中补充：

```markdown
- 资料管理和教师课程详情中的资料必须展示图文信息，包括封面、摘要、类型、大小、页数或时长、预览状态；不能只展示标题。
- 教师端资料预览与学生端共用站内预览组件，教师可检查 PDF / 视频实际打开效果。
```

- [x] **Step 3: 更新修改记录**

在 `backend/docs/项目修改记录.md` 增加本次记录：

```markdown
## 2026-06-28 课程大文件预览加速试点

- 新增 `material_previews` 资料预览元数据。
- 新增资料专用文件接口 `/api/materials/{material_id}/file`，后端鉴权后支持 Nginx `X-Accel-Redirect`。
- 学生端课程详情、教师端资料管理、教师端课程详情接入图文资料卡片和统一站内预览。
- 服务器部署影响：需要拉代码、执行数据库兼容建表、重启后端、重新构建前端、reload Nginx；服务器需安装或确认 `ffmpeg`、`ffprobe`、`qpdf`、`PyMuPDF`。
```

- [x] **Step 4: 标记试点方案状态**

在 `docs/superpowers/plans/2026-06-28-large-material-preview-pilot.md` 中将状态改为：

```markdown
> 状态：第一版实施中
```

或者实施完成后改为：

```markdown
> 状态：第一版已实施，待服务器压测
```

- [x] **Step 5: 运行最终验证命令**

运行：

```powershell
py -m pytest backend\tests\test_material_file_acceleration.py backend\tests\test_material_preview_service.py backend\tests\test_schema_compat.py -q
node frontend\tests\local-file-preview-static.test.mjs
node frontend\tests\material-preview-static.test.mjs
node frontend\tests\nginx-local-file-preview-static.test.mjs
cd frontend
npm run build
```

预期：全部通过。

---

## 服务器部署检查清单

实施合并到服务器前，必须确认：

- [ ] 服务器 `LOCAL_UPLOAD_DIR` 与 Nginx `alias` 指向同一上传目录。
- [ ] Nginx 已包含 `location /_protected_uploads/ { internal; ... }`。
- [ ] 后端 `.env` 中 `ALLOW_QUERY_TOKEN_FOR_FILES=true`，否则 `<video>` / `<object>` / 新窗口链接无法带 Authorization。
- [ ] 服务器安装 `ffmpeg`、`ffprobe`、`qpdf`。
- [ ] 后端 Python 环境安装 `PyMuPDF`。
- [ ] 拉代码后重启后端，触发 `ensure_schema_compatibility` 创建 `material_previews`。
- [ ] 前端重新构建并部署。
- [ ] Nginx reload。
- [ ] 使用 1GB PDF 和 1GB 视频做基线对比和复测。

服务器复测命令：

```powershell
curl.exe -I -H "Range: bytes=0-1048575" "https://域名/api/materials/资料ID/file?token=测试token"
curl.exe -L -o NUL -w "time_starttransfer=%{time_starttransfer} time_total=%{time_total} speed=%{speed_download}\n" -H "Range: bytes=0-1048575" "https://域名/api/materials/资料ID/file?token=测试token"
```

验收标准：

- 返回 200 或 206，Nginx 生产环境 Range 请求应能返回 206。
- 响应头包含 `Accept-Ranges: bytes`。
- 后端普通 API 不被 1GB 文件传输阻塞。
- 学生端和教师端都能看到图文资料卡片。
- 学生端和教师端都能站内预览 PDF / 视频。

---

## 计划自检

- Spec 覆盖：已覆盖大文件鉴权直传、Nginx 内部目录、预览元数据、PDF / 视频轻量预览、学生端图文卡片、教师端图文卡片、统一预览、测试和部署影响。
- 占位内容检查：本文档未发现占位项或未指定文件路径的实施项。
- Type consistency：后端统一使用 `MaterialPreview` / `MaterialPreviewOut` / `preview`；前端统一使用 `MaterialPreview` / `MaterialRichCard` / `MaterialPreviewDialog`；资料文件接口统一为 `/api/materials/{material_id}/file`。
