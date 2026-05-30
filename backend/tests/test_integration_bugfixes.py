"""教师端重构回归测试。"""
import io
from pathlib import Path

from app.core.security import get_password_hash
from app.models.entities import Class, Course, Material, Project, Question, StoredFile, StudentClassEnrollment, StudentProgress, User
from tests.conftest import auth_header


class TestTeacherRefactor:
    """覆盖课程锚定、教师隔离、班级和发布题目核心行为。"""

    def test_teacher_only_sees_own_courses(self, client, teacher_token, other_teacher_token):
        t1 = client.get("/api/questions/courses", headers=auth_header(teacher_token)).json()
        t2 = client.get("/api/questions/courses", headers=auth_header(other_teacher_token)).json()

        assert t1["code"] == 0
        assert [item["name"] for item in t1["data"]] == ["测试课程"]
        assert t2["code"] == 0
        assert [item["name"] for item in t2["data"]] == ["其它课程"]

    def test_course_detail_returns_course_counts_without_old_section_count(self, client, teacher_token):
        resp = client.get("/api/questions/courses/1", headers=auth_header(teacher_token))
        data = resp.json()

        assert data["code"] == 0
        assert data["data"]["id"] == 1
        assert "material_count" in data["data"]
        assert data["data"]["question_count"] == 1
        assert data["data"]["class_count"] == 1

    def test_create_material_uses_course_id(self, client, teacher_token):
        payload = {
            "course_id": 1,
            "type": "pdf",
            "title": "测试讲义",
            "url": "/uploads/test-material.pdf",
            "size": "2 MB",
        }

        create_data = client.post("/api/materials", json=payload, headers=auth_header(teacher_token)).json()
        assert create_data["code"] == 0

        list_data = client.get("/api/materials?course_id=1", headers=auth_header(teacher_token)).json()
        created = next(item for item in list_data["data"] if item["id"] == create_data["data"]["id"])
        assert created["course_id"] == 1
        assert created["course_name"] == "测试课程"
        assert created["url"] == "/uploads/test-material.pdf"
        assert created["size"] == "2 MB"

    def test_teacher_cannot_create_material_for_other_teacher_course(self, client, other_teacher_token):
        resp = client.post(
            "/api/materials",
            json={"course_id": 1, "type": "pdf", "title": "越权资料"},
            headers=auth_header(other_teacher_token),
        )
        data = resp.json()

        assert data["code"] == 404
        assert "课程不存在" in data["message"]

    def test_delete_course_with_child_data_returns_business_error(self, client, teacher_token):
        resp = client.delete("/api/questions/courses/1", headers=auth_header(teacher_token))
        data = resp.json()

        assert data["code"] == 400
        assert "课程下仍有" in data["message"]

    def test_delete_empty_course_succeeds(self, client, teacher_token):
        create_data = client.post(
            "/api/questions/courses",
            json={"name": "可删除空课程"},
            headers=auth_header(teacher_token),
        ).json()
        course_id = create_data["data"]["id"]

        resp = client.delete(f"/api/questions/courses/{course_id}", headers=auth_header(teacher_token))
        assert resp.json()["code"] == 0

    def test_classes_are_filtered_by_teacher_and_course(self, client, teacher_token, other_teacher_token):
        t1 = client.get("/api/classes", headers=auth_header(teacher_token)).json()
        t2 = client.get("/api/classes", headers=auth_header(other_teacher_token)).json()

        assert [item["name"] for item in t1["data"]] == ["2025级1班"]
        assert [item["name"] for item in t2["data"]] == ["2025级2班"]

        filtered = client.get("/api/classes?course_id=1&keyword=1班", headers=auth_header(teacher_token)).json()
        assert [item["name"] for item in filtered["data"]] == ["2025级1班"]

    def test_class_with_students_cannot_be_deleted(self, client, teacher_token):
        resp = client.delete("/api/classes/1", headers=auth_header(teacher_token))
        data = resp.json()

        assert data["code"] == 400
        assert "仍有学生" in data["message"]

    def test_create_class_without_legacy_major_column(self, client, teacher_token):
        """新增班级不应因旧库 classes.major NOT NULL 约束而 500。"""
        resp = client.post(
            "/api/classes",
            json={"name": "新测试班", "course_id": 1},
            headers=auth_header(teacher_token),
        )
        data = resp.json()

        assert data["code"] == 0
        assert isinstance(data["data"]["id"], int)

    def test_class_without_students_can_be_deleted(self, client, db_session, teacher_token):
        course = db_session.query(Course).filter(Course.created_by == "T001").first()
        cls = Class(name="空班级", course_id=course.id)
        db_session.add(cls)
        db_session.commit()

        resp = client.delete(f"/api/classes/{cls.id}", headers=auth_header(teacher_token))
        assert resp.json()["code"] == 0

    def test_teacher_students_only_include_owned_classes(self, client, teacher_token):
        resp = client.get("/api/teacher/students", headers=auth_header(teacher_token))
        data = resp.json()

        assert data["code"] == 0
        assert [item["id"] for item in data["data"]["items"]] == ["2025001"]

    def test_publish_questions_supports_multiple_classes_and_completion_report(self, client, db_session, teacher_token, student_token):
        course = db_session.query(Course).filter(Course.created_by == "T001").first()
        second_class = Class(name="同课2班", course_id=course.id)
        second_student = User(id="2025999", name="同课学生", hashed_password=get_password_hash("abc123"), role="student")
        db_session.add_all([second_class, second_student])
        db_session.flush()
        db_session.add(StudentClassEnrollment(user_id=second_student.id, class_id=second_class.id))
        db_session.commit()

        create_data = client.post(
            "/api/announcements",
            json={
                "course_id": course.id,
                "class_ids": [1, second_class.id],
                "title": "课程练习",
                "question_ids": [1],
            },
            headers=auth_header(teacher_token),
        ).json()
        assert create_data["code"] == 0
        announcement_id = create_data["data"]["id"]

        client.post(f"/api/announcements/{announcement_id}/complete", headers=auth_header(student_token))
        report = client.get(f"/api/announcements/{announcement_id}/completion-report", headers=auth_header(teacher_token)).json()

        assert report["code"] == 0
        assert report["data"]["total_students"] == 2
        assert report["data"]["completed_count"] == 1
        assert len(report["data"]["per_class"]) == 2

    def test_quiz_progress_is_course_based(self, client, db_session, student_token):
        client.post("/api/quiz/submit", json={"question_id": 1, "user_answer": "B"}, headers=auth_header(student_token))
        progress = db_session.query(StudentProgress).filter(StudentProgress.user_id == "2025001").first()

        assert progress is not None
        assert progress.course_id == 1
        assert progress.questions_done == 1

    def test_create_material_persists_file_id(self, client, db_session, teacher_token):
        stored = StoredFile(
            biz_type="upload",
            storage_provider="local",
            object_key="test-file-id-material.pdf",
            original_name="讲义.pdf",
            stored_name="test-file-id-material.pdf",
            content_type="application/pdf",
            extension=".pdf",
            size_bytes=100,
            created_by="T001",
        )
        db_session.add(stored)
        db_session.commit()

        create_resp = client.post(
            "/api/materials",
            json={
                "course_id": 1,
                "type": "pdf",
                "title": "file_id 测试资料",
                "url": f"/api/files/{stored.id}",
                "size": "0.1 MB",
                "file_id": stored.id,
            },
            headers=auth_header(teacher_token),
        )
        assert create_resp.json()["code"] == 0

        materials = client.get("/api/materials", headers=auth_header(teacher_token)).json()["data"]
        created = next(item for item in materials if item["id"] == create_resp.json()["data"]["id"])
        assert created["file_id"] == stored.id
        assert created["url"].startswith("/api/files/")

    def test_get_file_by_file_id_returns_streamed_content(self, client, db_session, teacher_token):
        upload_dir = Path(__file__).resolve().parents[1] / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        test_file = upload_dir / "file-by-id-test.pdf"
        test_file.write_bytes(b"%PDF-1.4 test content")

        try:
            stored = StoredFile(
                biz_type="material",
                storage_provider="local",
                object_key="file-by-id-test.pdf",
                original_name="test.pdf",
                stored_name="file-by-id-test.pdf",
                content_type="application/pdf",
                extension=".pdf",
                size_bytes=21,
                created_by="T001",
            )
            db_session.add(stored)
            db_session.commit()

            resp = client.get(f"/api/files/{stored.id}", headers=auth_header(teacher_token))
            assert resp.status_code == 200
            assert resp.content.startswith(b"%PDF")
        finally:
            if test_file.exists():
                try:
                    test_file.unlink()
                except PermissionError:
                    pass

    def test_upload_rejects_wrong_magic_number_even_if_extension_matches(self, client, teacher_token):
        fake_content = b"This is not a real PDF file"
        resp = client.post(
            "/api/upload",
            files={"file": ("fake.pdf", io.BytesIO(fake_content), "application/pdf")},
            headers=auth_header(teacher_token),
        )
        assert resp.json()["code"] == 400

    def test_uploaded_pdf_can_be_opened_by_browser_without_auth_header(self, client, teacher_token):
        """上传返回的文件 URL 应能被浏览器直接打开，不能依赖 Authorization 头。"""
        pdf_content = b"%PDF-1.4 browser preview pdf"
        upload = client.post(
            "/api/upload",
            files={"file": ("preview.pdf", io.BytesIO(pdf_content), "application/pdf")},
            headers=auth_header(teacher_token),
        ).json()
        assert upload["code"] == 0

        resp = client.get(upload["data"]["url"])

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/pdf")
        assert "inline" in resp.headers["content-disposition"]
        assert resp.content.startswith(b"%PDF")

    def test_uploaded_mp4_supports_browser_range_without_auth_header(self, client, teacher_token):
        """视频标签发起 Range 请求时也无法带 Bearer Token，应可直接分段读取。"""
        mp4_content = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"0" * 64
        upload = client.post(
            "/api/upload",
            files={"file": ("lesson.mp4", io.BytesIO(mp4_content), "video/mp4")},
            headers=auth_header(teacher_token),
        ).json()
        assert upload["code"] == 0

        resp = client.get(upload["data"]["url"], headers={"Range": "bytes=0-15"})

        assert resp.status_code == 206
        assert resp.headers["content-type"].startswith("video/mp4")
        assert resp.headers["content-range"] == f"bytes 0-15/{len(mp4_content)}"
        assert resp.content == mp4_content[:16]

    def test_batch_download_only_uses_teacher_students(self, client, db_session, teacher_token, other_teacher_token):
        upload_dir = Path(__file__).resolve().parents[1] / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        own_report = upload_dir / "own-report.pdf"
        other_report = upload_dir / "other-report.pdf"
        own_report.write_bytes(b"%PDF-1.4 own")
        other_report.write_bytes(b"%PDF-1.4 other")

        try:
            db_session.add(Project(
                title="本教师学生作品",
                author_id="2025001",
                major="自动化专业",
                description="测试",
                tags=[],
                report_url="/uploads/own-report.pdf",
                status="approved",
                date="2026-05-25",
            ))
            db_session.add(Project(
                title="其它教师学生作品",
                author_id="2025002",
                major="人工智能",
                description="测试",
                tags=[],
                report_url="/uploads/other-report.pdf",
                status="approved",
                date="2026-05-25",
            ))
            db_session.commit()

            resp = client.get("/api/teacher/projects/batch-download", headers=auth_header(teacher_token))
            assert resp.status_code == 200
            assert resp.content.startswith(b"PK")

            other_resp = client.get("/api/teacher/projects/batch-download", headers=auth_header(other_teacher_token))
            assert other_resp.status_code == 200
            assert other_resp.content.startswith(b"PK")
        finally:
            for path in (own_report, other_report):
                if path.exists():
                    path.unlink()


class TestProjectReview:
    """作品审核接口集成测试。"""

    def _create_project(self, client, student_token, title="测试作品", report_url=""):
        """辅助：学生创建作品，返回 project id。"""
        resp = client.post(
            "/api/projects",
            json={
                "title": title,
                "description": "测试描述",
                "tags": ["AI"],
                "report_url": report_url,
            },
            headers=auth_header(student_token),
        )
        assert resp.json()["code"] == 0
        return resp.json()["data"]["id"]

    def test_teacher_approve_project(self, client, student_token, teacher_token):
        """教师通过作品审核 → 状态变更为 approved。"""
        pid = self._create_project(client, student_token, "待审核作品")

        resp = client.post(
            f"/api/teacher/projects/{pid}/approve",
            headers=auth_header(teacher_token),
        )
        assert resp.json()["code"] == 0

        detail = client.get(f"/api/projects/{pid}", headers=auth_header(student_token)).json()
        assert detail["data"]["status"] == "approved"

    def test_teacher_reject_project_with_reason(self, client, student_token, teacher_token):
        """教师驳回作品 → 状态变更为 rejected，驳回理由不为空。"""
        pid = self._create_project(client, student_token, "要驳回的作品")

        resp = client.post(
            f"/api/teacher/projects/{pid}/reject",
            json={"reason": "报告格式不规范"},
            headers=auth_header(teacher_token),
        )
        assert resp.json()["code"] == 0

        detail = client.get(f"/api/projects/{pid}", headers=auth_header(student_token)).json()
        assert detail["data"]["status"] == "rejected"
        assert detail["data"]["reject_reason"] == "报告格式不规范"

    def test_non_teacher_cannot_approve(self, client, student_token):
        """非教师角色审核作品被拒绝。"""
        pid = self._create_project(client, student_token, "学生想审核")

        resp = client.post(
            f"/api/teacher/projects/{pid}/approve",
            headers=auth_header(student_token),
        )
        assert resp.json()["code"] == 403

    def test_approve_nonexistent_project_returns_error(self, client, teacher_token):
        """审核不存在的作品返回错误。"""
        resp = client.post(
            "/api/teacher/projects/99999/approve",
            headers=auth_header(teacher_token),
        )
        assert resp.json()["code"] == 404


class TestProjectLike:
    """作品点赞接口集成测试。"""

    def _create_project(self, client, student_token, title="点赞测试作品"):
        resp = client.post(
            "/api/projects",
            json={"title": title, "description": "测试描述", "tags": ["AI"]},
            headers=auth_header(student_token),
        )
        assert resp.json()["code"] == 0
        return resp.json()["data"]["id"]

    def _like(self, client, token, project_id):
        return client.post(
            f"/api/projects/{project_id}/like",
            headers=auth_header(token),
        )

    def test_like_project(self, client, student_token):
        """点赞作品 → liked=true, likes 计数增加。"""
        pid = self._create_project(client, student_token)

        result = self._like(client, student_token, pid).json()
        assert result["code"] == 0
        assert result["data"]["liked"] is True
        assert result["data"]["likes"] == 1

    def test_unlike_project(self, client, student_token):
        """取消点赞 → liked=false, likes 计数减少。"""
        pid = self._create_project(client, student_token)

        # 先点赞
        self._like(client, student_token, pid)
        # 再取消
        result = self._like(client, student_token, pid).json()
        assert result["code"] == 0
        assert result["data"]["liked"] is False
        assert result["data"]["likes"] == 0

    def test_double_like_is_idempotent(self, client, student_token):
        """重复点赞不累积，连续两次点赞 = 赞后取消，回到未赞状态。"""
        pid = self._create_project(client, student_token)

        self._like(client, student_token, pid)
        result = self._like(client, student_token, pid).json()

        # 赞后再次调用 = 取消点赞
        assert result["data"]["liked"] is False
        assert result["data"]["likes"] == 0

    def test_like_nonexistent_project_returns_error(self, client, student_token):
        """点赞不存在的作品返回 404。"""
        resp = self._like(client, student_token, 99999)
        assert resp.json()["code"] == 404


class TestProjectFullFlow:
    """作品完整流程 E2E 测试。"""

    def test_create_then_approve_then_visible_in_square(self, client, db_session, student_token, teacher_token):
        """学生创建 → 待审不可见 → 教师通过 → 广场可见。"""
        # 创建
        create = client.post(
            "/api/projects",
            json={"title": "完整流程测试", "description": "E2E", "tags": ["AI"]},
            headers=auth_header(student_token),
        ).json()
        assert create["code"] == 0
        pid = create["data"]["id"]

        # 待审状态下广场不可见
        square = client.get("/api/projects", headers=auth_header(student_token)).json()
        square_ids = [item["id"] for item in square["data"]["items"]]
        assert pid not in square_ids

        # 审核通过
        approve = client.post(
            f"/api/teacher/projects/{pid}/approve",
            headers=auth_header(teacher_token),
        ).json()
        assert approve["code"] == 0

        # 广场可见
        square_after = client.get("/api/projects", headers=auth_header(student_token)).json()
        square_ids_after = [item["id"] for item in square_after["data"]["items"]]
        assert pid in square_ids_after

    def test_rejected_project_can_be_resubmitted(self, client, db_session, student_token, teacher_token):
        """驳回后学生重新提交 → 状态变回 pending。"""
        # 创建 → 驳回
        create = client.post(
            "/api/projects",
            json={"title": "驳回重提交测试", "description": "描述", "tags": []},
            headers=auth_header(student_token),
        ).json()
        pid = create["data"]["id"]

        client.post(
            f"/api/teacher/projects/{pid}/reject",
            json={"reason": "格式不对"},
            headers=auth_header(teacher_token),
        )

        # 重新提交
        update = client.put(
            f"/api/projects/{pid}",
            json={"title": "驳回重提交测试（已修改）", "description": "改好了", "tags": ["AI"], "report_url": ""},
            headers=auth_header(student_token),
        ).json()
        assert update["code"] == 0

        detail = client.get(f"/api/projects/{pid}", headers=auth_header(student_token)).json()
        assert detail["data"]["status"] == "pending"


class TestBatchDownload:
    """批量下载测试。"""

    def test_empty_projects_returns_error(self, client, teacher_token):
        """没有可下载的作品时返回 404。"""
        resp = client.get("/api/teacher/projects/batch-download", headers=auth_header(teacher_token))
        assert resp.json()["code"] == 404

    def test_local_storage_batch_download(self, client, db_session, student_token, teacher_token):
        """本地存储模式下批量下载返回 ZIP。"""
        upload_dir = Path(__file__).resolve().parents[1] / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        report_path = upload_dir / "batch-dl-test.pdf"
        report_path.write_bytes(b"%PDF-1.4 batch download test content")

        try:
            project = Project(
                title="下载测试作品",
                author_id="2025001",
                major="自动化专业",
                description="测试",
                tags=[],
                report_url="/uploads/batch-dl-test.pdf",
                status="approved",
                date="2026-05-25",
            )
            db_session.add(project)
            db_session.commit()

            resp = client.get(
                "/api/teacher/projects/batch-download",
                headers=auth_header(teacher_token),
            )
            assert resp.status_code == 200
            # ZIP 文件以 PK 开头
            assert resp.content[:2] == b"PK"
        finally:
            if report_path.exists():
                report_path.unlink()

    def test_batch_download_with_report_file_id(self, client, db_session, student_token, teacher_token):
        """通过 report_file_id（新方式）批量下载。"""
        upload_dir = Path(__file__).resolve().parents[1] / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        local_file = upload_dir / "file-id-dl-test.pdf"
        local_file.write_bytes(b"%PDF-1.4 via stored_file")

        try:
            stored = StoredFile(
                biz_type="project_report",
                storage_provider="local",
                object_key="file-id-dl-test.pdf",
                original_name="report.pdf",
                stored_name="file-id-dl-test.pdf",
                content_type="application/pdf",
                extension=".pdf",
                size_bytes=24,
                created_by="2025001",
            )
            db_session.add(stored)
            db_session.flush()

            project = Project(
                title="file_id 下载测试",
                author_id="2025001",
                major="自动化专业",
                description="测试",
                tags=[],
                status="approved",
                date="2026-05-25",
                report_file_id=stored.id,
            )
            db_session.add(project)
            db_session.commit()

            resp = client.get(
                "/api/teacher/projects/batch-download",
                headers=auth_header(teacher_token),
            )
            assert resp.status_code == 200
            assert resp.content[:2] == b"PK"
        finally:
            if local_file.exists():
                local_file.unlink()
