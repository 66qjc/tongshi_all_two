"""联调缺陷回归测试"""
from pathlib import Path

from app.models.entities import Project
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
        assert [item["id"] for item in data["data"]] == ["2025998"]
        assert data["data"][0]["class_id"] == cls.id
        assert data["data"][0]["class_name"] == "筛选测试班"

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
