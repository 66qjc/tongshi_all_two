"""学生全局自由练习题池测试。"""
from app.models.entities import Course, Question, StudentClassEnrollment
from tests.conftest import auth_header


def test_global_practice_pool_hides_answers(client, student_token, db_session):
    public = Course(name="全局练习公共课", created_by="admin", is_public=True)
    db_session.add(public)
    db_session.flush()
    q = Question(
        course_id=public.id,
        type="choice",
        stem="全局题池隐藏答案",
        options=["A", "B"],
        answer="A",
        explanation="不该下发",
        created_by="admin",
    )
    db_session.add(q)
    db_session.commit()

    resp = client.get("/api/quiz/questions", headers=auth_header(student_token))
    body = resp.json()
    assert body["code"] == 0
    item = next(x for x in body["data"] if x["id"] == q.id)
    assert item["answer"] == ""
    assert item["explanation"] == ""
    assert "全局题池隐藏答案" in item["stem"]


def test_global_practice_pool_empty_without_enrollment(client, db_session):
    # 清空 2025002 的选课
    db_session.query(StudentClassEnrollment).filter(
        StudentClassEnrollment.user_id == "2025002"
    ).delete()
    q = Question(
        course_id=None,
        type="fill",
        stem="无选课不可见空挂载题",
        options=[],
        answer="X",
        created_by="admin",
    )
    db_session.add(q)
    db_session.commit()

    token = client.post("/api/token", json={"id": "2025002", "password": "abc123"}).json()["data"]["access_token"]
    resp = client.get("/api/quiz/questions", headers=auth_header(token)).json()
    assert resp["code"] == 0
    assert resp["data"] == []

    stats = client.get("/api/quiz/stats", headers=auth_header(token)).json()
    assert stats["code"] == 0
    assert stats["data"]["total_questions"] == 0
