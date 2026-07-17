"""公共课程删除测试：验证软删除与关联事实保留。"""
from datetime import datetime, timezone

from app.models.entities import (
    Announcement, Class, Course, Material, MaterialPreview,
    Question, QuizAttempt, StoredFile, StudentClassEnrollment, User,
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

        return pub_course.id, pub_q.id, ann.id, attempt.id, cls.id

    def test_delete_public_course_with_quiz_attempts(self, db_session):
        """有 QuizAttempt 引用的公共课程应可软删除，题目与答题事实保留。"""
        from app.services.admin_public_course_service import delete_public_course

        course_id, question_id, ann_id, attempt_id, class_id = self._seed_public_course_with_quiz(db_session)
        result = delete_public_course(db_session, course_id)
        assert result is True

        course = db_session.get(Course, course_id)
        assert course is not None
        assert course.deleted_at is not None

        # 课程级联软删班级/作业，但不处理题目；活跃题库仍可见该题
        from app.services.question_bank_service import count_all_questions, list_all_questions

        assert db_session.get(Class, class_id).deleted_at is not None
        assert db_session.get(Announcement, ann_id).deleted_at is not None
        surviving_question = db_session.get(Question, question_id)
        assert surviving_question is not None
        assert surviving_question.deleted_at is None
        assert surviving_question.course_id == course_id
        assert surviving_question.created_by == "admin"
        assert question_id in {item.id for item in list_all_questions(db_session).all()}
        assert count_all_questions(db_session) >= 1
        assert db_session.get(QuizAttempt, attempt_id) is not None
        assert db_session.get(Announcement, ann_id).question_ids == [question_id]

    def test_delete_public_course_returns_false_for_nonexistent(self, db_session):
        """删除不存在的公共课程应返回 False。"""
        from app.services.admin_public_course_service import delete_public_course

        assert delete_public_course(db_session, 99999) is False

    def test_delete_public_course_keeps_source_refs(self, db_session):
        """软删除公共课程后，教师副本的同步引用保持不变。"""
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

        # 副本与同步引用均保留，便于恢复后继续关联
        db_session.refresh(copy)
        assert copy.source_course_id == pub.id
        assert db_session.get(Course, pub.id).deleted_at is not None

    def test_soft_deleted_question_bank_reference_does_not_block_delete(self, db_session):
        """已软删除课程的题库根引用不应阻止公共课程软删除。"""
        from app.services.admin_public_course_service import delete_public_course

        public_course = Course(name="待删除题库根", created_by="admin", is_public=True)
        db_session.add(public_course)
        db_session.flush()

        deleted_copy = Course(
            name="已软删除课程副本",
            created_by="T001",
            question_bank_root_course_id=public_course.id,
            deleted_at=datetime.now(timezone.utc),
            deleted_by="T001",
        )
        db_session.add(deleted_copy)
        db_session.commit()

        assert delete_public_course(db_session, public_course.id) is True

        db_session.refresh(deleted_copy)
        assert deleted_copy.question_bank_root_course_id == public_course.id
        assert db_session.get(Course, public_course.id).deleted_at is not None

    def test_active_question_bank_root_reference_does_not_block_delete(self, db_session):
        """活跃课程仍引用历史 root 时，公共课也必须可软删。"""
        from app.services.admin_public_course_service import delete_public_course

        public_course = Course(name="活跃根引用公共课", created_by="admin", is_public=True)
        db_session.add(public_course)
        db_session.flush()

        active_copy = Course(
            name="仍活跃并引用历史根",
            created_by="T001",
            question_bank_root_course_id=public_course.id,
        )
        db_session.add(active_copy)
        db_session.commit()

        assert delete_public_course(db_session, public_course.id) is True
        db_session.refresh(active_copy)
        assert active_copy.deleted_at is None
        assert active_copy.question_bank_root_course_id == public_course.id
        assert db_session.get(Course, public_course.id).deleted_at is not None

    def test_delete_public_material_soft_deletes_and_preserves_file_preview(self, db_session):
        """公共资料删除只软删主体，不删文件/预览，也不清理教师副本。"""
        from app.services.admin_public_course_service import delete_public_material

        public_course = Course(name="资料软删公共课", created_by="admin", is_public=True)
        db_session.add(public_course)
        db_session.flush()
        file = StoredFile(
            object_key="materials/public-soft.pdf",
            original_name="公共资料.pdf",
            stored_name="public-soft.pdf",
            created_by="admin",
        )
        db_session.add(file)
        db_session.flush()
        material = Material(
            course_id=public_course.id,
            type="pdf",
            title="公共资料",
            url="/materials/public-soft.pdf",
            file_id=file.id,
        )
        db_session.add(material)
        db_session.flush()
        preview = MaterialPreview(material_id=material.id, status="ready")
        copy = Course(name="资料软删副本", created_by="T001", source_course_id=public_course.id)
        db_session.add_all([preview, copy])
        db_session.flush()
        mirrored = Material(
            course_id=copy.id,
            type="pdf",
            title="公共资料",
            url="/materials/public-soft.pdf",
            file_id=file.id,
            source_material_id=material.id,
        )
        db_session.add(mirrored)
        db_session.commit()

        assert delete_public_material(db_session, material.id) is True
        assert db_session.get(Material, material.id).deleted_at is not None
        assert db_session.get(StoredFile, file.id) is not None
        assert db_session.get(MaterialPreview, preview.id) is not None
        assert db_session.get(Material, mirrored.id).deleted_at is None
        assert db_session.get(Material, mirrored.id).source_material_id == material.id

    def test_delete_public_question_soft_deletes_and_preserves_attempts(self, db_session):
        """公共题目删除只软删题目，保留答题记录与作业题目列表。"""
        from app.core.exceptions import BusinessException
        from app.services.admin_public_course_service import delete_public_question

        public_course = Course(name="题目软删公共课", created_by="admin", is_public=True)
        db_session.add(public_course)
        db_session.flush()
        question = Question(
            course_id=public_course.id,
            type="choice",
            stem="公共待删题",
            options=["A", "B"],
            answer="A",
            created_by="admin",
        )
        db_session.add(question)
        db_session.flush()
        assignment = Announcement(
            course_id=public_course.id,
            teacher_id="T001",
            type="quiz",
            title="引用公共题作业",
            question_ids=[question.id],
        )
        db_session.add(assignment)
        db_session.flush()
        attempt = QuizAttempt(
            user_id="S999",
            question_id=question.id,
            announcement_id=assignment.id,
            user_answer="A",
            is_correct=True,
        )
        db_session.add(attempt)
        db_session.commit()

        try:
            delete_public_question(db_session, question.id)
            raised = False
        except BusinessException as exc:
            raised = True
            assert exc.code == 400
            assert "作业" in exc.message
        assert raised is True
        assert db_session.get(Question, question.id).deleted_at is None

        assignment.deleted_at = datetime.now(timezone.utc)
        assignment.deleted_by = "T001"
        db_session.commit()

        assert delete_public_question(db_session, question.id) is True
        assert db_session.get(Question, question.id).deleted_at is not None
        assert db_session.get(QuizAttempt, attempt.id) is not None
        assert db_session.get(Announcement, assignment.id).question_ids == [question.id]
