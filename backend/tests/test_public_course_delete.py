"""公共课程删除测试：验证有 QuizAttempt 引用的题目也能正常删除。"""
from app.models.entities import (
    Announcement, AnnouncementClass, Class, Course, Material,
    Question, QuizAttempt, StudentClassEnrollment, User,
)
from app.core.security import get_password_hash


class TestDeletePublicCourse:
    """公共课程删除回归测试。"""

    def _seed_public_course_with_quiz(self, db_session):
        """创建公共课程 + 班级 + 题目 + QuizAttempt，模拟真实场景。"""
        # 公共课程
        pub_course = Course(name="公共微积分", created_by="admin", is_public=True)
        db_session.add(pub_course)
        db_session.flush()

        # 公共课程下的题目
        pub_q = Question(
            type="choice", course_id=pub_course.id,
            stem="1+1=?",
            options=["A. 1", "B. 2", "C. 3", "D. 4"],
            answer="B",
            created_by="admin",
        )
        db_session.add(pub_q)
        db_session.flush()

        # 教师创建的班级（关联到公共课程的副本）
        teacher = User(id="T999", name="删除测试教师", hashed_password=get_password_hash("abc123"), role="teacher")
        student = User(id="S999", name="删除测试学生", hashed_password=get_password_hash("abc123"), role="student")
        db_session.add_all([teacher, student])
        db_session.flush()

        cls = Class(name="删除测试班", course_id=pub_course.id, created_by="T999")
        db_session.add(cls)
        db_session.flush()
        db_session.add(StudentClassEnrollment(user_id="S999", class_id=cls.id))

        # 教师发布的作业公告
        ann = Announcement(
            class_id=cls.id, course_id=pub_course.id,
            teacher_id="T999", type="quiz", title="测试作业",
            question_ids=[pub_q.id],
        )
        db_session.add(ann)
        db_session.flush()

        # 学生的答题记录（关键：引用了公共课程的题目）
        attempt = QuizAttempt(
            user_id="S999", question_id=pub_q.id,
            announcement_id=ann.id, user_answer="B", is_correct=True,
        )
        db_session.add(attempt)
        db_session.commit()

        return pub_course.id, pub_q.id

    def test_delete_public_course_with_quiz_attempts(self, db_session):
        """有 QuizAttempt 引用的公共课程应能正常删除，不报外键错误。"""
        from app.services.admin_public_course_service import delete_public_course

        course_id, question_id = self._seed_public_course_with_quiz(db_session)
        result = delete_public_course(db_session, course_id)
        assert result is True

        # 验证课程和关联数据已被清理
        assert db_session.query(Course).filter(Course.id == course_id).first() is None
        assert db_session.query(Question).filter(Question.course_id == course_id).count() == 0
        surviving_question = db_session.get(Question, question_id)
        assert surviving_question is not None
        assert surviving_question.deleted_at is None
        assert surviving_question.created_by == "admin"

    def test_delete_public_course_returns_false_for_nonexistent(self, db_session):
        """删除不存在的公共课程应返回 False。"""
        from app.services.admin_public_course_service import delete_public_course

        assert delete_public_course(db_session, 99999) is False

    def test_delete_public_course_clears_source_refs(self, db_session):
        """删除公共课程后，教师副本的 source_course_id 应被清空。"""
        from app.services.admin_public_course_service import delete_public_course

        # 公共课程
        pub = Course(name="同步测试课程", created_by="admin", is_public=True)
        db_session.add(pub)
        db_session.flush()

        # 教师副本（关联到公共课程）
        teacher = User(id="T888", name="同步教师", hashed_password=get_password_hash("abc123"), role="teacher")
        db_session.add(teacher)
        db_session.flush()

        copy = Course(name="同步测试课程", created_by="T888", source_course_id=pub.id)
        db_session.add(copy)
        db_session.commit()

        result = delete_public_course(db_session, pub.id)
        assert result is True

        # 副本应还在，但 source_course_id 已清空
        db_session.refresh(copy)
        assert copy.source_course_id is None
