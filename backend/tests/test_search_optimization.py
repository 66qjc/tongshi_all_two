"""搜索语义优化测试。"""
from app.models.entities import Course, Material, Question
from tests.conftest import auth_header


def test_course_search_is_case_insensitive_for_ascii(client, db_session, teacher_token):
    """ASCII 课程名搜索应大小写不敏感。"""
    db_session.add(Course(name="AI Foundations", created_by="T001", is_public=False))
    db_session.commit()

    resp = client.get("/api/courses?keyword=ai", headers=auth_header(teacher_token))
    data = resp.json()

    assert data["code"] == 0
    assert any(item["name"] == "AI Foundations" for item in data["data"])


def test_course_search_matches_chinese_substring(client, db_session, teacher_token):
    """中文课程名搜索应支持子串匹配。"""
    db_session.add(Course(name="人工智能基础", created_by="T001", is_public=False))
    db_session.commit()

    resp = client.get("/api/courses?keyword=智能", headers=auth_header(teacher_token))
    data = resp.json()

    assert data["code"] == 0
    assert any(item["name"] == "人工智能基础" for item in data["data"])


def test_material_search_matches_title_case_insensitive(client, db_session, teacher_token):
    """资料标题搜索应大小写不敏感。"""
    course = Course(name="资料课", created_by="T001", is_public=False)
    db_session.add(course)
    db_session.flush()
    db_session.add(Material(course_id=course.id, type="pdf", title="AI Reading", url="/uploads/a.pdf"))
    db_session.commit()

    resp = client.get("/api/materials?keyword=ai", headers=auth_header(teacher_token))
    data = resp.json()

    assert data["code"] == 0
    assert any(item["title"] == "AI Reading" for item in data["data"]["items"])


def test_question_search_matches_stem_case_insensitive(client, db_session, teacher_token):
    """题目题干搜索应大小写不敏感。"""
    course = Course(name="题目课", created_by="T001", is_public=False)
    db_session.add(course)
    db_session.flush()
    db_session.add(Question(course_id=course.id, type="choice", stem="What is AI?", options=["A"], answer="A"))
    db_session.commit()

    resp = client.get("/api/questions?keyword=ai", headers=auth_header(teacher_token))
    data = resp.json()

    assert data["code"] == 0
    assert any(item["stem"] == "What is AI?" for item in data["data"]["items"])
