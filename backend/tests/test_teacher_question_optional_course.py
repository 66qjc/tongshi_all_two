"""教师共享题库：新增题目可不挂课程。"""

from app.models.entities import QuestionContributionLog
from tests.conftest import auth_header
from tests.test_public_question_contribution import _create_teacher_course


def test_teacher_can_create_question_without_course(client, teacher_token, db_session):
    resp = client.post(
        "/api/questions",
        headers=auth_header(teacher_token),
        json={
            "type": "choice",
            "stem": "无挂载课程的共享题-测试用",
            "options": ["A. 一", "B. 二", "C. 三", "D. 四"],
            "answer": "A",
            "explanation": "",
            "tags": ["共享标签"],
            "star_rating": 3,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 0
    assert "id" in body["data"]

    listed = client.get(
        "/api/questions",
        headers=auth_header(teacher_token),
        params={"keyword": "无挂载课程的共享题-测试用", "page": 1, "page_size": 20},
    )
    assert listed.status_code == 200
    payload = listed.json()["data"]
    items = payload["items"] if isinstance(payload, dict) else payload
    assert len(items) >= 1
    hit = next(i for i in items if "无挂载课程的共享题-测试用" in i["stem"])
    assert hit.get("course_id") is None
    assert hit.get("star_rating") == 3
    assert "共享标签" in (hit.get("tags") or [])
    log = db_session.query(QuestionContributionLog).one()
    assert log.public_course_id is None
    assert log.public_course_name == "独立题库"
    assert log.operator_id == "T001"
    assert log.operator_role == "teacher"
    assert log.action == "create"
    assert log.question_count == 1


def test_teacher_create_still_accepts_optional_course(client, teacher_token, db_session):
    course_id = _create_teacher_course(client, teacher_token, "可选挂载课程-测试")
    resp = client.post(
        "/api/questions",
        headers=auth_header(teacher_token),
        json={
            "type": "fill",
            "course_id": course_id,
            "stem": "可选挂载仍可用-测试用",
            "options": [],
            "answer": "北京",
            "tags": [],
            "star_rating": 4,
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["code"] == 0

    listed = client.get(
        "/api/questions",
        headers=auth_header(teacher_token),
        params={"keyword": "可选挂载仍可用-测试用", "page": 1, "page_size": 20},
    )
    assert listed.status_code == 200
    payload = listed.json()["data"]
    items = payload["items"] if isinstance(payload, dict) else payload
    hit = next(i for i in items if "可选挂载仍可用-测试用" in i["stem"])
    assert hit.get("course_id") == course_id
    assert hit.get("star_rating") == 4
    log = db_session.query(QuestionContributionLog).one()
    assert log.public_course_id is None
    assert log.public_course_name == "独立题库"
