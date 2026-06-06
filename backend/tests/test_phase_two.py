"""阶段二回归测试：分页、搜索、同步状态、完成报告分页。"""
from app.core.security import get_password_hash
from app.models.entities import (
    Announcement, AnnouncementClass, Class, Course, Material,
    Question, StudentClassEnrollment, TaskCompletion, User,
)
from tests.conftest import auth_header


class TestQuestionPagination:
    """题库分页和关键词搜索测试。"""

    def test_questions_support_pagination(self, client, teacher_token):
        """题库列表返回分页结构。"""
        resp = client.get("/api/questions?page=1&page_size=10", headers=auth_header(teacher_token))
        data = resp.json()
        assert data["code"] == 0
        assert "items" in data["data"]
        assert "total" in data["data"]
        assert "page" in data["data"]
        assert "page_size" in data["data"]

    def test_questions_support_keyword_search(self, client, teacher_token, db_session):
        """题库支持关键词搜索。"""
        # 创建一个有特定题干的题目
        course = db_session.query(Course).filter(Course.created_by == "T001").first()
        q = Question(type="choice", course_id=course.id, stem="人工智能基础测试题",
                     options=["A", "B"], answer="A", explanation="")
        db_session.add(q)
        db_session.commit()

        resp = client.get("/api/questions?keyword=人工智能", headers=auth_header(teacher_token))
        data = resp.json()
        assert data["code"] == 0
        stems = [item["stem"] for item in data["data"]["items"]]
        assert "人工智能基础测试题" in stems

    def test_questions_filter_by_course_and_type(self, client, teacher_token):
        """题库支持课程和题型筛选。"""
        resp = client.get("/api/questions?type=choice&course_id=1", headers=auth_header(teacher_token))
        data = resp.json()
        assert data["code"] == 0
        for item in data["data"]["items"]:
            assert item["type"] == "choice"
            assert item["course_id"] == 1


class TestStudentQuestionAccess:
    """学生端题目访问权限回归测试。"""

    def test_student_cannot_use_teacher_question_list(self, client, student_token):
        """学生不能直接访问教师端题库列表。"""
        resp = client.get("/api/questions", headers=auth_header(student_token))
        data = resp.json()

        assert data["code"] == 403

    def test_student_cannot_fetch_other_course_questions(self, client, student_token, db_session):
        """学生不能通过课程题目接口读取未加入课程题目。"""
        other_course = db_session.query(Course).filter(Course.created_by == "T002").first()

        resp = client.get(
            f"/api/questions/course/{other_course.id}",
            headers=auth_header(student_token),
        )
        data = resp.json()

        assert data["code"] == 404
        assert "课程不存在" in data["message"]

    def test_student_cannot_submit_other_course_question(self, client, student_token, db_session):
        """学生不能提交未加入课程的题目来获取答案或解析。"""
        other_course = db_session.query(Course).filter(Course.created_by == "T002").first()
        question = Question(
            type="choice",
            course_id=other_course.id,
            stem="未加入课程题目",
            options=["A", "B"],
            answer="A",
            explanation="未加入课程解析",
        )
        db_session.add(question)
        db_session.commit()

        resp = client.post(
            "/api/quiz/submit",
            json={"question_id": question.id, "user_answer": "A"},
            headers=auth_header(student_token),
        )
        data = resp.json()

        assert data["code"] == 404
        assert "题目不存在" in data["message"]


class TestCourseSearch:
    """课程关键词搜索测试。"""

    def test_teacher_course_search(self, client, teacher_token):
        """教师端课程支持关键词搜索。"""
        resp = client.get("/api/courses?keyword=测试", headers=auth_header(teacher_token))
        data = resp.json()
        assert data["code"] == 0
        names = [c["name"] for c in data["data"]]
        assert "测试课程" in names

    def test_student_course_search(self, client, student_token):
        """学生端课程支持关键词搜索。"""
        resp = client.get("/api/courses?keyword=测试", headers=auth_header(student_token))
        data = resp.json()
        assert data["code"] == 0
        # 学生只能看到自己班级关联的课程
        names = [c["name"] for c in data["data"]]
        assert "测试课程" in names

    def test_student_search_other_course_returns_empty(self, client, student_token):
        """学生搜索非自己课程返回空结果。"""
        resp = client.get("/api/courses?keyword=其它", headers=auth_header(student_token))
        data = resp.json()
        assert data["code"] == 0
        assert len(data["data"]) == 0

    def test_teacher_courses_support_owned_pagination(self, client, teacher_token, db_session):
        """教师端已添加课程支持分页，且不影响旧数组响应。"""
        db_session.add_all([
            Course(name="分页课程A", created_by="T001"),
            Course(name="分页课程B", created_by="T001"),
        ])
        db_session.commit()

        paged = client.get(
            "/api/courses?scope=owned&page=1&page_size=2",
            headers=auth_header(teacher_token),
        ).json()
        legacy = client.get("/api/courses", headers=auth_header(teacher_token)).json()

        assert paged["code"] == 0
        assert "items" in paged["data"]
        assert paged["data"]["total"] >= 3
        assert len(paged["data"]["items"]) == 2
        assert legacy["code"] == 0
        assert isinstance(legacy["data"], list)


class TestMaterialPagination:
    """资料分页和搜索测试。"""

    def test_materials_support_pagination(self, client, teacher_token, db_session):
        """教师端资料列表返回分页结构。"""
        # 创建一些资料
        course = db_session.query(Course).filter(Course.created_by == "T001").first()
        for i in range(3):
            m = Material(course_id=course.id, type="pdf", title=f"测试资料{i+1}",
                        url="/test.pdf", size="1 MB", date="2026-06-04")
            db_session.add(m)
        db_session.commit()

        resp = client.get("/api/materials?page=1&page_size=2", headers=auth_header(teacher_token))
        data = resp.json()
        assert data["code"] == 0
        assert "items" in data["data"]
        assert data["data"]["total"] >= 3
        assert len(data["data"]["items"]) == 2

    def test_materials_support_keyword_search(self, client, teacher_token, db_session):
        """教师端资料支持关键词搜索。"""
        course = db_session.query(Course).filter(Course.created_by == "T001").first()
        m = Material(course_id=course.id, type="pdf", title="机器学习导论",
                    url="/test.pdf", size="1 MB", date="2026-06-04")
        db_session.add(m)
        db_session.commit()

        resp = client.get("/api/materials?keyword=机器学习", headers=auth_header(teacher_token))
        data = resp.json()
        assert data["code"] == 0
        titles = [item["title"] for item in data["data"]["items"]]
        assert "机器学习导论" in titles

    def test_course_contents_support_keyword(self, client, student_token, db_session):
        """学生端课程资料支持关键词搜索。"""
        course = db_session.query(Course).filter(Course.created_by == "T001").first()
        m = Material(course_id=course.id, type="video", title="深度学习基础",
                    url="/test.mp4", size="10 MB", date="2026-06-04")
        db_session.add(m)
        db_session.commit()

        resp = client.get(f"/api/courses/{course.id}/contents?keyword=深度学习",
                          headers=auth_header(student_token))
        data = resp.json()
        assert data["code"] == 0
        titles = [item["title"] for item in data["data"]]
        assert "深度学习基础" in titles

    def test_student_cannot_view_other_course_contents(self, client, student_token, db_session):
        """学生不能通过课程资料接口查看未加入课程的资料。"""
        other_course = db_session.query(Course).filter(Course.created_by == "T002").first()
        db_session.add(Material(
            course_id=other_course.id,
            type="pdf",
            title="其它课程资料",
            url="/other.pdf",
            size="1 MB",
            date="2026-06-04",
        ))
        db_session.commit()

        resp = client.get(
            f"/api/courses/{other_course.id}/contents",
            headers=auth_header(student_token),
        )
        data = resp.json()

        assert data["code"] == 404
        assert "课程不存在" in data["message"]


class TestCompletionReportPagination:
    """任务完成报告分页测试。"""

    def test_completion_report_has_paginated_students(self, client, teacher_token, db_session):
        """完成报告的学生列表使用分页结构。"""
        course = db_session.query(Course).filter(Course.created_by == "T001").first()
        cls = db_session.query(Class).filter(Class.course_id == course.id).first()

        ann = Announcement(
            title="分页测试任务", type="quiz", teacher_id="T001",
            course_id=course.id, question_ids=[1],
        )
        db_session.add(ann)
        db_session.flush()
        db_session.add(AnnouncementClass(announcement_id=ann.id, class_id=cls.id))
        db_session.commit()

        resp = client.get(
            f"/api/announcements/{ann.id}/completion-report?completed_page=1&completed_page_size=10",
            headers=auth_header(teacher_token),
        )
        data = resp.json()
        assert data["code"] == 0
        report = data["data"]
        # 新的分页结构
        assert "items" in report["completed_students"]
        assert "total" in report["completed_students"]
        assert "page" in report["completed_students"]
        assert "page_size" in report["completed_students"]
        assert "items" in report["incomplete_students"]
        assert "total" in report["incomplete_students"]
        # 汇总字段仍然存在
        assert "total_students" in report
        assert "completed_count" in report
        assert "per_class" in report

    def test_completion_report_class_filter_applies_before_pagination(self, client, teacher_token, db_session):
        """按班级查看完成报告时，筛选必须先于分页和总数统计。"""
        course = db_session.query(Course).filter(Course.created_by == "T001").first()
        first_class = db_session.query(Class).filter(Class.course_id == course.id).first()
        second_class = Class(name="分页筛选2班", course_id=course.id, created_by="T001")
        second_student = User(
            id="2025888",
            name="分页筛选学生",
            hashed_password=get_password_hash("abc123"),
            role="student",
            major="测试专业",
        )
        db_session.add_all([second_class, second_student])
        db_session.flush()
        db_session.add(StudentClassEnrollment(user_id=second_student.id, class_id=second_class.id))

        ann = Announcement(
            title="班级筛选任务",
            type="quiz",
            teacher_id="T001",
            course_id=course.id,
            question_ids=[1],
        )
        db_session.add(ann)
        db_session.flush()
        db_session.add_all([
            AnnouncementClass(announcement_id=ann.id, class_id=first_class.id),
            AnnouncementClass(announcement_id=ann.id, class_id=second_class.id),
            TaskCompletion(announcement_id=ann.id, user_id="2025001"),
        ])
        db_session.commit()

        resp = client.get(
            f"/api/announcements/{ann.id}/completion-report?class_id={second_class.id}&completed_page=1&completed_page_size=1&incomplete_page=1&incomplete_page_size=1",
            headers=auth_header(teacher_token),
        )
        data = resp.json()

        assert data["code"] == 0
        report = data["data"]
        assert report["total_students"] == 1
        assert report["completed_count"] == 0
        assert report["completed_students"]["total"] == 0
        assert report["incomplete_students"]["total"] == 1
        assert report["incomplete_students"]["items"][0]["id"] == second_student.id


class TestAdminPublicCourseSyncStatus:
    """管理员公共课程同步状态测试。"""

    def test_public_course_list_has_sync_fields(self, client, db_session):
        """公共课程列表包含同步状态字段。"""
        # 登录管理员
        login = client.post("/api/token", json={"id": "admin", "password": "admin123"})
        admin_token = login.json()["data"]["access_token"]

        # 创建公共课程
        course = Course(name="同步测试公共课程", created_by="admin", is_public=True)
        db_session.add(course)
        db_session.commit()

        resp = client.get("/api/admin/public-courses", headers=auth_header(admin_token))
        data = resp.json()
        assert data["code"] == 0
        # 找到刚创建的课程
        found = [c for c in data["data"] if c["name"] == "同步测试公共课程"]
        assert len(found) == 1
        course_data = found[0]
        assert "sync_copy_count" in course_data
        assert "synced_material_count" in course_data
        assert "synced_question_count" in course_data
        assert "sync_status" in course_data
        assert course_data["sync_status"] in ("not_synced", "partial", "synced")


class TestCourseQuizStatsPermission:
    """课程答题统计权限校验测试 - 修复问题5（权限泄露）"""

    def test_student_cannot_access_unenrolled_course_stats(self, client, db_session, student_token):
        """学生无法访问未加入课程的答题统计（防止信息泄露）"""
        # 创建一个学生未加入的课程
        other_course = db_session.query(Course).filter(Course.created_by == "T002").first()

        # 在该课程下创建题目
        question = Question(
            type="choice",
            course_id=other_course.id,
            stem="未加入课程的题目",
            options=["A", "B"],
            answer="A",
            explanation="解析",
        )
        db_session.add(question)
        db_session.commit()

        # 学生尝试访问该课程的答题统计
        resp = client.get(
            f"/api/quiz/stats/{other_course.id}",
            headers=auth_header(student_token),
        )
        data = resp.json()

        # 应该返回 404 而不是统计数据
        assert data["code"] == 404
        assert "课程不存在" in data["message"] or "无权限" in data["message"]

    def test_student_can_access_enrolled_course_stats(self, client, student_token):
        """学生可以访问已加入课程的答题统计"""
        # 学生已加入课程 ID=1（在 fixture 中设置）
        resp = client.get("/api/quiz/stats/1", headers=auth_header(student_token))
        data = resp.json()

        assert data["code"] == 0
        assert "course_id" in data["data"]
        assert data["data"]["course_id"] == 1
        assert "questions_done" in data["data"]
        assert "accuracy" in data["data"]

    def test_student_cannot_probe_nonexistent_course(self, client, student_token):
        """学生无法通过统计接口探测课程是否存在"""
        # 访问一个不存在的课程 ID
        resp = client.get("/api/quiz/stats/99999", headers=auth_header(student_token))
        data = resp.json()

        assert data["code"] == 404
        # 错误消息应该统一，不泄露课程是否存在
        assert "课程不存在" in data["message"] or "无权限" in data["message"]

    def test_permission_consistency_between_submit_and_stats(self, client, db_session, student_token):
        """确保答题提交和统计查询权限校验一致"""
        # 创建学生无权访问的课程和题目
        other_teacher = User(
            id="T888",
            name="另一教师",
            hashed_password=get_password_hash("teacher123"),
            role="teacher",
        )
        db_session.add(other_teacher)
        db_session.flush()

        restricted_course = Course(name="限制课程", created_by="T888", is_public=False)
        db_session.add(restricted_course)
        db_session.flush()

        restricted_question = Question(
            type="choice",
            course_id=restricted_course.id,
            stem="限制题目",
            options=["A", "B"],
            answer="A",
        )
        db_session.add(restricted_question)
        db_session.commit()

        # 尝试提交答案 - 应该被拒绝
        submit_resp = client.post(
            "/api/quiz/submit",
            json={"question_id": restricted_question.id, "user_answer": "A"},
            headers=auth_header(student_token),
        )
        assert submit_resp.json()["code"] == 404

        # 尝试查看统计 - 同样应该被拒绝
        stats_resp = client.get(
            f"/api/quiz/stats/{restricted_course.id}",
            headers=auth_header(student_token),
        )
        assert stats_resp.json()["code"] == 404

    def test_student_with_multiple_enrollments_can_access_all_stats(self, client, db_session):
        """学生加入多个班级后可以访问所有关联课程的统计"""
        # 创建第二个课程和班级
        teacher = db_session.query(User).filter(User.id == "T001").first()
        course2 = Course(name="多班级课程", created_by=teacher.id, is_public=False)
        db_session.add(course2)
        db_session.flush()

        class2 = Class(name="多班级测试班", course_id=course2.id, created_by=teacher.id)
        db_session.add(class2)
        db_session.flush()

        student = db_session.query(User).filter(User.id == "2025001").first()
        enrollment = StudentClassEnrollment(user_id=student.id, class_id=class2.id)
        db_session.add(enrollment)

        question2 = Question(
            type="choice",
            course_id=course2.id,
            stem="多班级课程题目",
            options=["A", "B"],
            answer="A",
        )
        db_session.add(question2)
        db_session.commit()

        student_token = client.post(
            "/api/token",
            json={"id": student.id, "password": "abc123"},
        ).json()["data"]["access_token"]

        # 应该能访问两个课程的统计
        resp1 = client.get("/api/quiz/stats/1", headers=auth_header(student_token))
        resp2 = client.get(f"/api/quiz/stats/{course2.id}", headers=auth_header(student_token))

        assert resp1.json()["code"] == 0
        assert resp2.json()["code"] == 0
