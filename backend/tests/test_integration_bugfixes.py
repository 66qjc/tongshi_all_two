"""联调缺陷回归测试"""
import io
from pathlib import Path

from app.core.security import create_access_token, get_password_hash
from app.models.entities import Project, StoredFile, User
from tests.conftest import auth_header


class TestIntegrationBugfixes:
    """覆盖本轮前后端联调缺陷的后端回归测试"""

    def test_create_announcement_accepts_datetime_strings(self, client, teacher_token):
        payload = {
            "class_id": 1,
            "type": "announcement",
            "title": "带时间限制的公告",
            "content": "请按时完成",
            "start_time": "2026-05-19 09:00:00",
            "end_time": "2026-05-19 10:30:00",
        }

        create_resp = client.post(
            "/api/announcements",
            json=payload,
            headers=auth_header(teacher_token),
        )
        create_data = create_resp.json()

        assert create_data["code"] == 0
        assert "id" in create_data["data"]

        list_resp = client.get("/api/announcements", headers=auth_header(teacher_token))
        list_data = list_resp.json()

        assert list_data["code"] == 0
        created = next(item for item in list_data["data"] if item["id"] == create_data["data"]["id"])
        assert created["start_time"].startswith("2026-05-19T09:00:00")
        assert created["end_time"].startswith("2026-05-19T10:30:00")

    def test_create_material_persists_uploaded_url_and_size(self, client, teacher_token):
        payload = {
            "chapter_id": 1,
            "type": "pdf",
            "title": "测试讲义",
            "url": "/uploads/test-material.pdf",
            "size": "2 MB",
        }

        create_resp = client.post(
            "/api/materials",
            json=payload,
            headers=auth_header(teacher_token),
        )
        create_data = create_resp.json()

        assert create_data["code"] == 0

        list_resp = client.get("/api/materials", headers=auth_header(teacher_token))
        list_data = list_resp.json()

        assert list_data["code"] == 0
        created = next(item for item in list_data["data"] if item["id"] == create_data["data"]["id"])
        assert created["url"] == "/uploads/test-material.pdf"
        assert created["size"] == "2 MB"

    def test_batch_download_uses_standard_auth_header(self, client, db_session, teacher_token):
        upload_dir = Path(__file__).resolve().parents[1] / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        report_path = upload_dir / "test-report.pdf"
        report_path.write_bytes(b"%PDF-1.4 test report")

        try:
            db_session.add(Project(
                title="测试作品",
                author_id="2025001",
                major="自动化专业",
                description="测试描述",
                tags=["AI"],
                report_url="/uploads/test-report.pdf",
                status="approved",
                date="2026-05-19",
            ))
            db_session.commit()

            resp = client.get(
                "/api/teacher/projects/batch-download",
                headers=auth_header(teacher_token),
            )

            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("application/zip")
            assert resp.content.startswith(b"PK")
        finally:
            if report_path.exists():
                report_path.unlink()

    def test_course_detail_returns_chapters_and_counts(self, client, teacher_token):
        courses_resp = client.get("/api/questions/courses", headers=auth_header(teacher_token))
        course_id = courses_resp.json()["data"][0]["id"]

        resp = client.get(f"/api/questions/courses/{course_id}", headers=auth_header(teacher_token))
        data = resp.json()

        assert data["code"] == 0
        assert data["data"]["id"] == course_id
        assert data["data"]["chapter_count"] >= 1
        assert data["data"]["material_count"] >= 0
        assert data["data"]["chapters"][0]["course_name"] == data["data"]["name"]

    def test_teacher_can_create_update_and_delete_chapter(self, client, teacher_token):
        courses_resp = client.get("/api/questions/courses", headers=auth_header(teacher_token))
        course_id = courses_resp.json()["data"][0]["id"]

        create_resp = client.post(
            "/api/chapters",
            json={
                "num": "02",
                "title": "新增章节",
                "desc": "用于课程管理测试",
                "topics": ["课程管理", "章节维护"],
                "status": "即将发布",
                "sort_order": 2,
                "course_id": course_id,
                "day_of_week": "周二",
                "class_periods": "3-4",
                "schedule_note": "单周",
            },
            headers=auth_header(teacher_token),
        )
        create_data = create_resp.json()
        assert create_data["code"] == 0
        chapter_id = create_data["data"]["id"]

        update_resp = client.put(
            f"/api/chapters/{chapter_id}",
            json={
                "num": "02",
                "title": "已修改章节",
                "desc": "修改后的简介",
                "topics": ["更新"],
                "status": "已发布",
                "sort_order": 3,
                "course_id": course_id,
                "day_of_week": "周三",
                "class_periods": "5-6",
                "schedule_note": "",
            },
            headers=auth_header(teacher_token),
        )
        assert update_resp.json()["code"] == 0

        list_resp = client.get("/api/chapters", headers=auth_header(teacher_token))
        updated = next(item for item in list_resp.json()["data"] if item["id"] == chapter_id)
        assert updated["title"] == "已修改章节"
        assert updated["course_id"] == course_id
        assert updated["course_name"] == "测试课程"

        delete_resp = client.delete(f"/api/chapters/{chapter_id}", headers=auth_header(teacher_token))
        assert delete_resp.json()["code"] == 0

    def test_update_chapter_num_to_existing_returns_business_error(self, client, teacher_token):
        courses_resp = client.get("/api/questions/courses", headers=auth_header(teacher_token))
        course_id = courses_resp.json()["data"][0]["id"]
        create_resp = client.post(
            "/api/chapters",
            json={
                "num": "02",
                "title": "待改编号章节",
                "desc": "用于重复编号测试",
                "topics": [],
                "status": "即将发布",
                "sort_order": 2,
                "course_id": course_id,
                "day_of_week": "",
                "class_periods": "",
                "schedule_note": "",
            },
            headers=auth_header(teacher_token),
        )
        chapter_id = create_resp.json()["data"]["id"]

        resp = client.put(
            f"/api/chapters/{chapter_id}",
            json={
                "num": "01",
                "title": "待改编号章节",
                "desc": "用于重复编号测试",
                "topics": [],
                "status": "即将发布",
                "sort_order": 2,
                "course_id": course_id,
                "day_of_week": "",
                "class_periods": "",
                "schedule_note": "",
            },
            headers=auth_header(teacher_token),
        )
        data = resp.json()

        assert data["code"] == 400
        assert "章节编号已存在" in data["message"]

    def test_update_course_name_to_existing_returns_business_error(self, client, teacher_token):
        create_resp = client.post(
            "/api/questions/courses",
            json={"name": "重复名称课程"},
            headers=auth_header(teacher_token),
        )
        course_id = create_resp.json()["data"]["id"]

        resp = client.put(
            f"/api/questions/courses/{course_id}",
            json={"name": "测试课程"},
            headers=auth_header(teacher_token),
        )
        data = resp.json()

        assert data["code"] == 400
        assert "课程已存在" in data["message"]

    def test_delete_course_with_chapters_returns_business_error(self, client, teacher_token):
        courses_resp = client.get("/api/questions/courses", headers=auth_header(teacher_token))
        course_id = courses_resp.json()["data"][0]["id"]

        resp = client.delete(f"/api/questions/courses/{course_id}", headers=auth_header(teacher_token))
        data = resp.json()

        assert data["code"] == 400
        assert "课程下仍有章节" in data["message"]

    def test_delete_course_removes_empty_chapters(self, client, db_session, teacher_token):
        from app.models.entities import Chapter, Course

        course = Course(name="可删除空课程")
        db_session.add(course)
        db_session.flush()
        chapter = Chapter(
            num="99",
            title="空章节",
            desc="没有资料、题目和学习记录",
            topics=[],
            status="即将发布",
            sort_order=99,
            course_id=course.id,
        )
        db_session.add(chapter)
        db_session.commit()
        course_id = course.id
        chapter_id = chapter.id

        resp = client.delete(f"/api/questions/courses/{course_id}", headers=auth_header(teacher_token))
        data = resp.json()

        assert data["code"] == 0
        assert db_session.query(Course).filter(Course.id == course_id).first() is None
        assert db_session.query(Chapter).filter(Chapter.id == chapter_id).first() is None

    def test_teacher_delete_chapter_removes_learning_relations(self, client, db_session, teacher_token):
        from app.models.entities import Chapter, Material, Question, QuizAttempt, StudentProgress

        chapter = db_session.query(Chapter).filter(Chapter.num == "01").first()
        question = db_session.query(Question).filter(Question.chapter_id == chapter.id).first()
        material = Material(
            chapter_id=chapter.id,
            type="pdf",
            title="待级联删除资料",
            url="/uploads/delete-me.pdf",
            size="1 MB",
        )
        attempt = QuizAttempt(
            user_id="2025001",
            question_id=question.id,
            user_answer="B",
            is_correct=True,
        )
        progress = StudentProgress(
            user_id="2025001",
            chapter_id=chapter.id,
            learn_progress=80,
            questions_done=1,
            accuracy=100,
        )
        db_session.add_all([material, attempt, progress])
        db_session.commit()
        chapter_id = chapter.id
        question_id = question.id
        material_id = material.id
        attempt_id = attempt.id
        progress_id = progress.id

        resp = client.delete(f"/api/chapters/{chapter_id}", headers=auth_header(teacher_token))
        data = resp.json()

        assert data["code"] == 0
        assert db_session.query(Chapter).filter(Chapter.id == chapter_id).first() is None
        assert db_session.query(Material).filter(Material.id == material_id).first() is None
        assert db_session.query(Question).filter(Question.id == question_id).first() is None
        assert db_session.query(QuizAttempt).filter(QuizAttempt.id == attempt_id).first() is None
        assert db_session.query(StudentProgress).filter(StudentProgress.id == progress_id).first() is None

    def test_teacher_students_can_filter_by_class(self, client, db_session, teacher_token):
        from app.core.security import get_password_hash
        from app.models.entities import Class, StudentClassEnrollment, User

        cls = Class(name="筛选测试班", major="人工智能")
        student = User(
            id="2025998",
            name="筛选学生",
            hashed_password=get_password_hash("abc123"),
            role="student",
            major="人工智能",
        )
        db_session.add_all([cls, student])
        db_session.flush()
        db_session.add(StudentClassEnrollment(user_id=student.id, class_id=cls.id))
        db_session.commit()

        resp = client.get(f"/api/teacher/students?class_id={cls.id}", headers=auth_header(teacher_token))
        data = resp.json()

        assert data["code"] == 0
        items = data["data"]["items"]
        assert [item["id"] for item in items] == ["2025998"]
        assert items[0]["class_id"] == cls.id
        assert items[0]["class_name"] == "筛选测试班"

    def test_delete_class_removes_students_that_only_belong_to_that_class(self, client, db_session, teacher_token):
        from app.core.security import get_password_hash
        from app.models.entities import (
            Announcement,
            AnnouncementRead,
            Class,
            Project,
            ProjectLike,
            Question,
            QuizAttempt,
            StudentClassEnrollment,
            StudentProgress,
            TaskCompletion,
            User,
        )

        cls = Class(name="待删除班级", major="人工智能")
        student = User(
            id="2025997",
            name="待删除学生",
            hashed_password=get_password_hash("abc123"),
            role="student",
            major="人工智能",
        )
        db_session.add_all([cls, student])
        db_session.flush()
        db_session.add(StudentClassEnrollment(user_id=student.id, class_id=cls.id))
        question = db_session.query(Question).first()
        db_session.add(QuizAttempt(user_id=student.id, question_id=question.id, user_answer="B", is_correct=True))
        db_session.add(StudentProgress(user_id=student.id, chapter_id=question.chapter_id, learn_progress=50, questions_done=1, accuracy=100))
        project = Project(title="待删除作品", author_id=student.id, major="人工智能", description="测试", status="approved")
        db_session.add(project)
        db_session.flush()
        db_session.add(ProjectLike(user_id=student.id, project_id=project.id))
        ann = Announcement(class_id=cls.id, teacher_id="T001", type="quiz", title="测试任务")
        db_session.add(ann)
        db_session.flush()
        db_session.add(AnnouncementRead(user_id=student.id, announcement_id=ann.id))
        db_session.add(TaskCompletion(user_id=student.id, announcement_id=ann.id))
        db_session.commit()
        student_id = student.id
        class_id = cls.id
        project_id = project.id
        announcement_id = ann.id

        resp = client.delete(f"/api/classes/{class_id}", headers=auth_header(teacher_token))
        data = resp.json()

        assert data["code"] == 0
        assert db_session.query(User).filter(User.id == student_id).first() is None
        assert db_session.query(StudentClassEnrollment).filter(StudentClassEnrollment.user_id == student_id).count() == 0
        assert db_session.query(QuizAttempt).filter(QuizAttempt.user_id == student_id).count() == 0
        assert db_session.query(StudentProgress).filter(StudentProgress.user_id == student_id).count() == 0
        assert db_session.query(Project).filter(Project.id == project_id).first() is None
        assert db_session.query(ProjectLike).filter(ProjectLike.user_id == student_id).count() == 0
        assert db_session.query(AnnouncementRead).filter(AnnouncementRead.user_id == student_id).count() == 0
        assert db_session.query(TaskCompletion).filter(TaskCompletion.user_id == student_id).count() == 0
        assert db_session.query(Announcement).filter(Announcement.id == announcement_id).first() is None

    def test_delete_class_keeps_students_that_still_belong_to_other_classes(self, client, db_session, teacher_token):
        from app.core.security import get_password_hash
        from app.models.entities import Class, StudentClassEnrollment, User

        delete_cls = Class(name="删除其中一个班", major="人工智能")
        keep_cls = Class(name="保留班级", major="人工智能")
        student = User(
            id="2025996",
            name="多班级学生",
            hashed_password=get_password_hash("abc123"),
            role="student",
            major="人工智能",
        )
        db_session.add_all([delete_cls, keep_cls, student])
        db_session.flush()
        db_session.add_all([
            StudentClassEnrollment(user_id=student.id, class_id=delete_cls.id),
            StudentClassEnrollment(user_id=student.id, class_id=keep_cls.id),
        ])
        db_session.commit()
        delete_class_id = delete_cls.id
        keep_class_id = keep_cls.id

        resp = client.delete(f"/api/classes/{delete_class_id}", headers=auth_header(teacher_token))
        data = resp.json()

        assert data["code"] == 0
        assert db_session.query(User).filter(User.id == student.id).first() is not None
        assert db_session.query(StudentClassEnrollment).filter(
            StudentClassEnrollment.user_id == student.id,
            StudentClassEnrollment.class_id == delete_class_id,
        ).first() is None
        assert db_session.query(StudentClassEnrollment).filter(
            StudentClassEnrollment.user_id == student.id,
            StudentClassEnrollment.class_id == keep_class_id,
        ).first() is not None

    def test_get_file_by_file_id_returns_streamed_content(self, client, db_session, teacher_token):
        """通过 /api/files/{file_id} 应返回文件内容"""
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
            file_id = stored.id

            resp = client.get(f"/api/files/{file_id}", headers=auth_header(teacher_token))
            assert resp.status_code == 200
            assert resp.content.startswith(b"%PDF")
        finally:
            try:
                if test_file.exists():
                    test_file.unlink()
            except PermissionError:
                pass

    def test_get_file_by_file_id_supports_range_requests(self, client, db_session, teacher_token):
        """浏览器播放视频时应支持 Range 分段请求"""
        upload_dir = Path(__file__).resolve().parents[1] / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        test_file = upload_dir / "range-test.mp4"
        test_file.write_bytes(b"0123456789")

        try:
            stored = StoredFile(
                biz_type="material",
                storage_provider="local",
                object_key="range-test.mp4",
                original_name="range-test.mp4",
                stored_name="range-test.mp4",
                content_type="video/mp4",
                extension=".mp4",
                size_bytes=10,
                created_by="T001",
            )
            db_session.add(stored)
            db_session.commit()

            resp = client.get(
                f"/api/files/{stored.id}",
                headers={**auth_header(teacher_token), "Range": "bytes=0-3"},
            )

            assert resp.status_code == 206
            assert resp.content == b"0123"
            assert resp.headers["content-range"] == "bytes 0-3/10"
            assert resp.headers["accept-ranges"] == "bytes"
            assert resp.headers["content-length"] == "4"
        finally:
            try:
                if test_file.exists():
                    test_file.unlink()
            except PermissionError:
                pass

    def test_upload_returns_file_id_and_api_file_url(self, client, teacher_token):
        """上传接口应返回 file_id 和 /api/files/ 前缀的 URL"""
        pdf_content = b"%PDF-1.4 fake pdf content"
        resp = client.post(
            "/api/upload",
            files={"file": ("test-upload.pdf", io.BytesIO(pdf_content), "application/pdf")},
            headers=auth_header(teacher_token),
        )
        data = resp.json()

        assert data["code"] == 0
        assert data["data"]["file_id"] is not None
        assert data["data"]["file_id"] > 0
        assert data["data"]["url"].startswith("/api/files/")
        assert data["data"]["content_type"] == "application/pdf"
        assert data["data"]["storage_provider"] in {"local", "s3"}

    def test_upload_rejects_wrong_magic_number_even_if_extension_matches(self, client, teacher_token):
        """魔数不匹配的文件应被拒绝，即使扩展名正确"""
        # 伪造 PDF 扩展名但内容不是 PDF
        fake_content = b"This is not a real PDF file"
        resp = client.post(
            "/api/upload",
            files={"file": ("fake.pdf", io.BytesIO(fake_content), "application/pdf")},
            headers=auth_header(teacher_token),
        )
        data = resp.json()

        assert data["code"] == 400

    def test_create_material_persists_file_id(self, client, db_session, teacher_token):
        """创建资料时应持久化 file_id"""
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
        file_id = stored.id

        create_resp = client.post(
            "/api/materials",
            json={
                "chapter_id": 1,
                "type": "pdf",
                "title": "file_id 测试资料",
                "url": f"/api/files/{file_id}",
                "size": "0.1 MB",
                "file_id": file_id,
            },
            headers=auth_header(teacher_token),
        )
        assert create_resp.json()["code"] == 0

        list_resp = client.get("/api/materials", headers=auth_header(teacher_token))
        materials = list_resp.json()["data"]
        created = next(item for item in materials if item["id"] == create_resp.json()["data"]["id"])
        assert created["file_id"] == file_id
        assert created["url"].startswith("/api/files/")

    def test_create_project_persists_report_file_id(self, client, db_session, student_token):
        """创建作品时应持久化 report_file_id"""
        stored = StoredFile(
            biz_type="project_report",
            storage_provider="local",
            object_key="test-report.pdf",
            original_name="报告.pdf",
            stored_name="test-report.pdf",
            content_type="application/pdf",
            extension=".pdf",
            size_bytes=200,
            created_by="2025001",
        )
        db_session.add(stored)
        db_session.commit()
        file_id = stored.id

        resp = client.post(
            "/api/projects",
            json={
                "title": "file_id 作品测试",
                "description": "测试描述",
                "tags": ["AI"],
                "report_url": f"/api/files/{file_id}",
                "report_file_id": file_id,
            },
            headers=auth_header(student_token),
        )
        assert resp.json()["code"] == 0
        project_id = resp.json()["data"]["id"]

        detail = client.get(f"/api/projects/{project_id}", headers=auth_header(student_token))
        data = detail.json()["data"]
        assert data["report_file_id"] == file_id

    def test_reject_project_creates_student_notification(self, client, db_session, teacher_token, student_token):
        """教师驳回作品后，作者应收到个人通知"""
        project = Project(
            title="待审作品",
            author_id="2025001",
            major="自动化专业",
            description="测试描述",
            status="pending",
        )
        db_session.add(project)
        db_session.commit()

        resp = client.post(
            f"/api/teacher/projects/{project.id}/reject",
            json={"reason": "报告缺少说明"},
            headers=auth_header(teacher_token),
        )
        assert resp.json()["code"] == 0

        notices_resp = client.get("/api/notifications", headers=auth_header(student_token))
        notices_data = notices_resp.json()

        assert notices_data["code"] == 0
        assert len(notices_data["data"]) == 1
        notice = notices_data["data"][0]
        assert notice["type"] == "project_rejected"
        assert notice["title"] == "作品被驳回，请修改"
        assert notice["related_type"] == "project"
        assert notice["related_id"] == project.id
        assert notice["is_read"] is False
        assert "待审作品" in notice["content"]
        assert "报告缺少说明" in notice["content"]

    def test_student_can_read_own_rejected_project_but_other_student_cannot(self, client, db_session, student_token):
        """驳回作品仅作者本人、教师或管理员可查看"""
        other = User(
            id="2025002",
            name="其他学生",
            hashed_password=get_password_hash("abc123"),
            role="student",
            major="自动化专业",
        )
        project = Project(
            title="作者自己的驳回作品",
            author_id="2025001",
            major="自动化专业",
            description="测试描述",
            status="rejected",
            reject_reason="需要补充报告",
        )
        db_session.add_all([other, project])
        db_session.commit()
        other_token = create_access_token({"sub": "2025002"})

        owner_resp = client.get(f"/api/projects/{project.id}", headers=auth_header(student_token))
        other_resp = client.get(f"/api/projects/{project.id}", headers=auth_header(other_token))

        assert owner_resp.json()["code"] == 0
        assert owner_resp.json()["data"]["reject_reason"] == "需要补充报告"
        assert other_resp.json()["code"] in {403, 404}

    def test_rejected_project_cannot_be_liked(self, client, db_session, student_token):
        """未通过审核的作品不能被点赞"""
        project = Project(
            title="不可点赞驳回作品",
            author_id="2025001",
            major="自动化专业",
            description="测试描述",
            status="rejected",
        )
        db_session.add(project)
        db_session.commit()

        resp = client.post(f"/api/projects/{project.id}/like", headers=auth_header(student_token))
        data = resp.json()

        assert data["code"] == 400
        assert "未通过审核" in data["message"]

    def test_batch_download_returns_zip_for_approved_projects(self, client, db_session, teacher_token):
        """批量下载应返回 ZIP 格式"""
        upload_dir = Path(__file__).resolve().parents[1] / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        report_path = upload_dir / "batch-test-report.pdf"
        report_path.write_bytes(b"%PDF-1.4 batch test")

        try:
            db_session.add(Project(
                title="批量下载测试作品",
                author_id="2025001",
                major="自动化专业",
                description="测试",
                tags=[],
                report_url="/uploads/batch-test-report.pdf",
                status="approved",
                date="2026-05-25",
            ))
            db_session.commit()

            resp = client.get(
                "/api/teacher/projects/batch-download",
                headers=auth_header(teacher_token),
            )
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("application/zip")
            assert resp.content.startswith(b"PK")
        finally:
            try:
                if report_path.exists():
                    report_path.unlink()
            except PermissionError:
                pass

    def test_get_file_by_legacy_upload_url_still_works(self, client, teacher_token):
        """历史 /uploads/... 路径仍可正常访问"""
        upload_dir = Path(__file__).resolve().parents[1] / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        legacy_file = upload_dir / "legacy-test.txt"
        legacy_file.write_text("legacy content")

        try:
            resp = client.get("/uploads/legacy-test.txt")
            assert resp.status_code == 200
            assert resp.text == "legacy content"
        finally:
            if legacy_file.exists():
                legacy_file.unlink()
