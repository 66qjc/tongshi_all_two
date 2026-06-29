"""公共课程共享题库贡献记录测试。"""
import io

from openpyxl import Workbook

from app.models.entities import Course, Question, QuestionContributionLog
from tests.conftest import auth_header


def _build_question_import_file(headers: list[str], rows: list[list[str]]) -> io.BytesIO:
    """构造题库导入接口使用的 Excel 文件。"""
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def _admin_token(client) -> str:
    resp = client.post("/api/token", json={"id": "admin", "password": "Admin#2026"})
    return resp.json()["data"]["access_token"]


def _create_public_course(client, admin_token: str, name: str) -> int:
    resp = client.post(
        "/api/admin/public-courses",
        json={"name": name},
        headers=auth_header(admin_token),
    )
    assert resp.json()["code"] == 0
    return resp.json()["data"]["id"]


def _create_teacher_course(client, teacher_token: str, name: str) -> int:
    resp = client.post(
        "/api/questions/courses",
        json={"name": name},
        headers=auth_header(teacher_token),
    )
    assert resp.json()["code"] == 0
    return resp.json()["data"]["id"]


def test_question_bank_is_shared_across_teacher_courses(client, teacher_token):
    """同一题库下的不同课程应直接看到同一套题目。"""
    course_a = _create_teacher_course(client, teacher_token, "共享课程 A")
    course_b = _create_teacher_course(client, teacher_token, "共享课程 B")

    create_resp = client.post(
        "/api/questions",
        json={
            "course_id": course_a,
            "type": "choice",
            "stem": "共享题目",
            "options": ["A. 对", "B. 错"],
            "answer": "A",
            "explanation": "",
            "tags": [],
        },
        headers=auth_header(teacher_token),
    )
    assert create_resp.json()["code"] == 0

    list_resp = client.get(
        f"/api/questions?course_id={course_b}",
        headers=auth_header(teacher_token),
    )
    data = list_resp.json()
    assert data["code"] == 0
    # 全站共享题库：从 B 课程入口也能看到 A 课程下新增的题，且题目 course_id 仍是 A
    shared = [item for item in data["data"]["items"] if item["stem"] == "共享题目"]
    assert len(shared) == 1
    assert shared[0]["course_id"] == course_a


def test_duplicate_question_is_rejected_across_shared_courses(client, teacher_token):
    """不同课程下提交相同题目时，应被共享题库统一拦截。"""
    course_a = _create_teacher_course(client, teacher_token, "重复校验 A")
    course_b = _create_teacher_course(client, teacher_token, "重复校验 B")

    first_resp = client.post(
        "/api/questions",
        json={
            "course_id": course_a,
            "type": "choice",
            "stem": "重复题目",
            "options": ["A. 对", "B. 错"],
            "answer": "A",
            "explanation": "",
            "tags": [],
        },
        headers=auth_header(teacher_token),
    )
    assert first_resp.json()["code"] == 0

    second_resp = client.post(
        "/api/questions",
        json={
            "course_id": course_b,
            "type": "choice",
            "stem": "重复题目",
            "options": ["A. 对", "B. 错"],
            "answer": "A",
            "explanation": "",
            "tags": [],
        },
        headers=auth_header(teacher_token),
    )
    data = second_resp.json()
    assert data["code"] == 400
    assert "相同题目" in data["message"]


def test_admin_creating_public_question_writes_log_and_shares_globally(
    client,
    db_session,
    teacher_token,
):
    """管理员在公共课程新增题目时记一条贡献日志，且题目全站可见。"""
    admin_token = _admin_token(client)
    public_course_id = _create_public_course(client, admin_token, "共享题库公共课")
    teacher_copy_id = client.post(
        f"/api/questions/courses/{public_course_id}/add",
        headers=auth_header(teacher_token),
    ).json()["data"]["id"]

    resp = client.post(
        f"/api/admin/public-courses/{public_course_id}/questions",
        json={
            "type": "choice",
            "stem": "管理员新增公共题",
            "options": ["A. 对", "B. 错"],
            "answer": "A",
            "explanation": "写入共享题库",
            "tags": ["共建"],
        },
        headers=auth_header(admin_token),
    )

    data = resp.json()
    assert data["code"] == 0
    # 题目原地保存在公共课程，不再复制副本
    source = db_session.query(Question).filter(
        Question.course_id == public_course_id,
        Question.stem == "管理员新增公共题",
    ).one()
    assert data["data"]["id"] == source.id
    assert db_session.query(Question).filter(
        Question.source_question_id.isnot(None),
    ).count() == 0

    # 教师在自己的课程下也能看到这道全站共享题
    list_resp = client.get(
        f"/api/questions?course_id={teacher_copy_id}",
        headers=auth_header(teacher_token),
    )
    stems = [item["stem"] for item in list_resp.json()["data"]["items"]]
    assert "管理员新增公共题" in stems

    log = db_session.query(QuestionContributionLog).one()
    assert log.public_course_id == public_course_id
    assert log.public_course_name == "共享题库公共课"
    assert log.operator_id == "admin"
    assert log.action == "create"
    assert log.question_count == 1


def test_admin_importing_public_questions_writes_batch_log(
    client,
    db_session,
):
    """管理员向公共课程批量导入时，只按成功写入数量记一条批次日志。"""
    admin_token = _admin_token(client)
    public_course_id = _create_public_course(client, admin_token, "共享导入公共课")

    excel = _build_question_import_file(
        ["题型", "标签", "题干", "选项（选择题用 | 分隔）", "答案", "解析"],
        [
            ["choice", "共建", "导入公共题一", "A. 对|B. 错", "A", ""],
            ["fill", "共建", "导入公共题二", "", "答案", ""],
        ],
    )
    resp = client.post(
        f"/api/admin/public-courses/{public_course_id}/questions/import",
        files={"file": ("questions.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_header(admin_token),
    )

    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["success_count"] == 2
    assert data["data"]["fail_count"] == 0
    # 题目原地写入公共课程，不产生副本
    assert db_session.query(Question).filter(Question.course_id == public_course_id).count() == 2
    assert db_session.query(Question).filter(Question.source_question_id.isnot(None)).count() == 0

    log = db_session.query(QuestionContributionLog).one()
    assert log.public_course_id == public_course_id
    assert log.operator_id == "admin"
    assert log.action == "import"
    assert log.question_count == 2


def test_admin_can_page_question_contribution_logs(client):
    """管理员可按公共课程分页查看题库贡献记录。"""
    admin_token = _admin_token(client)
    public_course_id = _create_public_course(client, admin_token, "贡献记录公共课")
    client.post(
        f"/api/admin/public-courses/{public_course_id}/questions",
        json={
            "type": "choice",
            "stem": "分页贡献题一",
            "options": ["A", "B"],
            "answer": "A",
            "explanation": "",
            "tags": [],
        },
        headers=auth_header(admin_token),
    )

    resp = client.get(
        f"/api/admin/public-courses/{public_course_id}/question-contributions?page=1&page_size=10",
        headers=auth_header(admin_token),
    )

    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["total"] == 1
    assert data["data"]["page"] == 1
    assert data["data"]["page_size"] == 10
    assert data["data"]["items"][0]["public_course_id"] == public_course_id
    assert data["data"]["items"][0]["operator_name"] == "管理员"
    assert data["data"]["items"][0]["action"] == "create"
    assert data["data"]["items"][0]["question_count"] == 1


def test_private_course_create_and_import_do_not_write_contribution_logs(
    client,
    db_session,
    teacher_token,
):
    """私有课程题目新增和导入保持原行为，不写贡献记录。"""
    create_course_resp = client.post(
        "/api/questions/courses",
        json={"name": "私有题库课程"},
        headers=auth_header(teacher_token),
    )
    private_course_id = create_course_resp.json()["data"]["id"]
    client.post(
        "/api/questions",
        json={
            "course_id": private_course_id,
            "type": "choice",
            "stem": "私有新增题",
            "options": ["A", "B"],
            "answer": "A",
            "explanation": "",
            "tags": [],
        },
        headers=auth_header(teacher_token),
    )
    excel = _build_question_import_file(
        ["题型", "课程名称", "标签", "题干", "选项（选择题用 | 分隔）", "答案", "解析"],
        [["choice", "私有题库课程", "", "私有导入题", "A|B", "A", ""]],
    )
    client.post(
        "/api/questions/import",
        files={"file": ("questions.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_header(teacher_token),
    )

    assert db_session.query(QuestionContributionLog).count() == 0


def test_contribution_log_snapshot_survives_public_course_delete(
    client,
    db_session,
):
    """公共课程删除后，已写入的贡献记录保留课程快照。"""
    admin_token = _admin_token(client)
    public_course_id = _create_public_course(client, admin_token, "待删除公共课")
    client.post(
        f"/api/admin/public-courses/{public_course_id}/questions",
        json={
            "type": "choice",
            "stem": "删除后保留日志",
            "options": ["A", "B"],
            "answer": "A",
            "explanation": "",
            "tags": [],
        },
        headers=auth_header(admin_token),
    )

    delete_resp = client.delete(
        f"/api/admin/public-courses/{public_course_id}",
        headers=auth_header(admin_token),
    )

    assert delete_resp.json()["code"] == 0
    log = db_session.query(QuestionContributionLog).one()
    assert log.public_course_id == public_course_id
    assert log.public_course_name == "待删除公共课"
    assert log.operator_name == "管理员"
