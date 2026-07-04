from app.models.entities import Class, StudentClassEnrollment, User
from tests.conftest import auth_header


def test_teacher_batch_delete_only_removes_student_from_own_classes(client, db_session, teacher_token):
    own_class = db_session.query(Class).filter(Class.created_by == "T001").first()
    other_class = db_session.query(Class).filter(Class.created_by == "T002").first()
    db_session.add(StudentClassEnrollment(user_id="2025001", class_id=other_class.id))
    db_session.commit()

    response = client.post(
        "/api/teacher/students/batch-delete",
        json=["2025001"],
        headers=auth_header(teacher_token),
    )
    data = response.json()

    assert response.status_code == 200
    assert data["code"] == 0
    assert data["data"]["deleted_count"] == 1
    assert db_session.query(User).filter(User.id == "2025001").first() is not None
    assert db_session.query(StudentClassEnrollment).filter(
        StudentClassEnrollment.user_id == "2025001",
        StudentClassEnrollment.class_id == other_class.id,
    ).first() is not None
    assert db_session.query(StudentClassEnrollment).filter(
        StudentClassEnrollment.user_id == "2025001",
        StudentClassEnrollment.class_id == own_class.id,
    ).first() is None
