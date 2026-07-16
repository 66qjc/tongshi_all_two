"""课时与课时进度接口退役回归测试。"""

import pytest


RETIRED_ENDPOINTS = [
    ("GET", "/api/courses/1/lessons", "/api/courses/{course_id}/lessons"),
    ("POST", "/api/courses/1/lessons", "/api/courses/{course_id}/lessons"),
    ("GET", "/api/lessons/1", "/api/lessons/{lesson_id}"),
    ("PUT", "/api/lessons/1", "/api/lessons/{lesson_id}"),
    ("DELETE", "/api/lessons/1", "/api/lessons/{lesson_id}"),
    ("POST", "/api/courses/1/lessons/reorder", "/api/courses/{course_id}/lessons/reorder"),
    ("GET", "/api/courses/1/progress", "/api/courses/{course_id}/progress"),
    ("POST", "/api/courses/1/progress", "/api/courses/{course_id}/progress"),
    (
        "POST",
        "/api/courses/1/lessons/1/progress",
        "/api/courses/{course_id}/lessons/{lesson_id}/progress",
    ),
    (
        "GET",
        "/api/classes/1/students/2025001/progress",
        "/api/classes/{class_id}/students/{student_id}/progress",
    ),
    ("GET", "/api/courses/1/analytics", "/api/courses/{course_id}/analytics"),
    (
        "GET",
        "/api/public/learning/courses/1/lessons",
        "/api/public/learning/courses/{course_id}/lessons",
    ),
]


@pytest.mark.parametrize(
    ("method", "path", "template"),
    RETIRED_ENDPOINTS,
    # 使用短 id，避免 Windows 下 nodeid 路径过长导致 conftest 创建目录失败
    ids=[
        "course-lessons-get",
        "course-lessons-post",
        "lesson-get",
        "lesson-put",
        "lesson-delete",
        "lessons-reorder",
        "course-progress-get",
        "course-progress-post",
        "lesson-progress-post",
        "class-student-progress",
        "course-analytics",
        "public-lessons",
    ],
)
def test_retired_lesson_endpoint_returns_http_404(
    client,
    method: str,
    path: str,
    template: str,
):
    response = client.request(method, path)
    assert response.status_code == 404


def test_retired_lesson_paths_are_absent_from_openapi(client):
    paths = client.get("/openapi.json").json()["paths"]
    retired_templates = {template for _, _, template in RETIRED_ENDPOINTS}
    assert retired_templates.isdisjoint(paths)
