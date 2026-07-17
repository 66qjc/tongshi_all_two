"""公共课程共享题库贡献记录测试。"""
import io

from openpyxl import Workbook

from app.models.entities import Course, Question, QuestionContributionLog
from app.services.question_bank_service import compute_stem_hash
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
        "/api/courses",
        json={"name": name},
        headers=auth_header(teacher_token),
    )
    assert resp.json()["code"] == 0
    return resp.json()["data"]["id"]


def test_admin_can_edit_teacher_question_from_public_course_entry(client, teacher_token):
    """管理员应能从任意有效公共课程入口编辑教师贡献到共享题库的题目。"""
    admin_token = _admin_token(client)
    public_course_id = _create_public_course(client, admin_token, "跨入口编辑公共课")
    teacher_course_id = _create_teacher_course(client, teacher_token, "教师贡献挂课")
    created = client.post(
        "/api/questions",
        json={
            "course_id": teacher_course_id,
            "type": "fill",
            "stem": "教师贡献待编辑题",
            "options": [],
            "answer": "原答案",
            "explanation": "",
            "tags": [],
        },
        headers=auth_header(teacher_token),
    ).json()
    assert created["code"] == 0

    response = client.put(
        f"/api/admin/public-courses/{public_course_id}/questions/{created['data']['id']}",
        json={
            "type": "fill",
            "stem": "管理员已编辑教师贡献题",
            "options": [],
            "answer": "新答案",
            "explanation": "管理员修订",
            "tags": ["共享题库"],
        },
        headers=auth_header(admin_token),
    )

    data = response.json()
    assert data["code"] == 0
    assert data["data"]["stem"] == "管理员已编辑教师贡献题"
    assert data["data"]["course_id"] == teacher_course_id


def test_admin_can_create_edit_and_list_question_star_rating(client):
    """管理员应能维护共享题目的 1-5 星级，并在列表中读取同一值。"""
    admin_token = _admin_token(client)
    public_course_id = _create_public_course(client, admin_token, "管理员星级维护公共课")
    created = client.post(
        f"/api/admin/public-courses/{public_course_id}/questions",
        json={
            "type": "fill",
            "stem": "管理员星级创建题",
            "options": [],
            "answer": "答案",
            "explanation": "",
            "tags": [],
            "star_rating": 5,
        },
        headers=auth_header(admin_token),
    ).json()
    assert created["code"] == 0
    assert created["data"]["star_rating"] == 5
    question_id = created["data"]["id"]

    updated = client.put(
        f"/api/admin/public-courses/{public_course_id}/questions/{question_id}",
        json={
            "type": "fill",
            "stem": "管理员星级创建题",
            "options": [],
            "answer": "答案",
            "explanation": "",
            "tags": [],
            "star_rating": 1,
        },
        headers=auth_header(admin_token),
    ).json()
    assert updated["code"] == 0
    assert updated["data"]["star_rating"] == 1

    listed = client.get(
        f"/api/admin/public-courses/{public_course_id}/questions",
        headers=auth_header(admin_token),
    ).json()
    assert listed["code"] == 0
    assert next(item for item in listed["data"] if item["id"] == question_id)["star_rating"] == 1

    invalid = client.post(
        f"/api/admin/public-courses/{public_course_id}/questions",
        json={
            "type": "fill",
            "stem": "管理员无效星级题",
            "options": [],
            "answer": "答案",
            "explanation": "",
            "tags": [],
            "star_rating": 6,
        },
        headers=auth_header(admin_token),
    )
    assert invalid.status_code == 422


def test_admin_create_rejects_same_stem_and_writes_hash(client, db_session):
    """管理员新增题目应写入统一题干哈希，并拦截同题干不同答案。"""
    admin_token = _admin_token(client)
    public_course_id = _create_public_course(client, admin_token, "管理员新增哈希课")
    first = client.post(
        f"/api/admin/public-courses/{public_course_id}/questions",
        json={
            "type": "choice",
            "stem": "管理员新增唯一题干",
            "options": ["A. 是", "B. 否"],
            "answer": "A",
            "explanation": "",
            "tags": [],
        },
        headers=auth_header(admin_token),
    ).json()
    assert first["code"] == 0
    stored = db_session.query(Question).filter(Question.id == first["data"]["id"]).one()
    assert stored.stem_hash == compute_stem_hash("管理员新增唯一题干")

    duplicate = client.post(
        f"/api/admin/public-courses/{public_course_id}/questions",
        json={
            "type": "choice",
            "stem": "管理员新增唯一题干",
            "options": ["A. 是", "B. 否"],
            "answer": "B",
            "explanation": "答案不同也应拦截",
            "tags": [],
        },
        headers=auth_header(admin_token),
    ).json()
    assert duplicate["code"] == 400


def test_admin_update_rejects_same_stem_and_rewrites_hash(client, db_session):
    """管理员编辑应排除自身查重，同时拦截其他题目的相同题干并更新哈希。"""
    admin_token = _admin_token(client)
    public_course_id = _create_public_course(client, admin_token, "管理员编辑哈希课")

    def create_question(stem: str, answer: str) -> int:
        result = client.post(
            f"/api/admin/public-courses/{public_course_id}/questions",
            json={
                "type": "fill",
                "stem": stem,
                "options": [],
                "answer": answer,
                "explanation": "",
                "tags": [],
            },
            headers=auth_header(admin_token),
        ).json()
        assert result["code"] == 0
        return result["data"]["id"]

    create_question("管理员编辑基准题干", "甲")
    target_id = create_question("管理员编辑待改题干", "乙")
    conflict = client.put(
        f"/api/admin/public-courses/{public_course_id}/questions/{target_id}",
        json={
            "type": "fill",
            "stem": "管理员编辑基准题干",
            "options": [],
            "answer": "不同答案",
            "explanation": "",
            "tags": [],
        },
        headers=auth_header(admin_token),
    ).json()
    assert conflict["code"] == 400

    updated = client.put(
        f"/api/admin/public-courses/{public_course_id}/questions/{target_id}",
        json={
            "type": "fill",
            "stem": "管理员编辑后的全新题干",
            "options": [],
            "answer": "乙",
            "explanation": "",
            "tags": [],
        },
        headers=auth_header(admin_token),
    ).json()
    assert updated["code"] == 0
    stored = db_session.query(Question).filter(Question.id == target_id).one()
    assert stored.stem_hash == compute_stem_hash("管理员编辑后的全新题干")


def test_admin_import_skips_same_stem_and_writes_hash(client, db_session):
    """管理员导入应跳过同题干记录，并为成功导入的题目写入统一哈希。"""
    admin_token = _admin_token(client)
    public_course_id = _create_public_course(client, admin_token, "管理员导入哈希课")
    created = client.post(
        f"/api/admin/public-courses/{public_course_id}/questions",
        json={
            "type": "fill",
            "stem": "管理员导入已有题干",
            "options": [],
            "answer": "已有答案",
            "explanation": "",
            "tags": [],
        },
        headers=auth_header(admin_token),
    ).json()
    assert created["code"] == 0

    workbook = _build_question_import_file(
        ["题型", "题干", "选项", "答案", "解析", "标签"],
        [
            ["fill", "管理员导入已有题干", "", "不同答案", "", ""],
            ["fill", "管理员导入全新题干", "", "新答案", "", "导入"],
        ],
    )
    response = client.post(
        f"/api/admin/public-courses/{public_course_id}/questions/import",
        files={"file": ("questions.xlsx", workbook.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_header(admin_token),
    ).json()

    assert response["code"] == 0
    data = response["data"]
    assert data["success_count"] == 1
    assert data["skip_count"] == 1
    assert data["fail_count"] == 0
    assert data["errors"] == []
    assert any("已存在相同题目" in skip["reason"] for skip in data["skips"])
    imported = db_session.query(Question).filter(Question.stem == "管理员导入全新题干").one()
    assert imported.stem_hash == compute_stem_hash("管理员导入全新题干")


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


def test_shared_question_list_exposes_creator_star_and_owner(
    client,
    teacher_token,
    other_teacher_token,
):
    """共享列表应返回添加人、星级，并以 created_by 判定 is_owner。"""
    course_a = _create_teacher_course(client, teacher_token, "归属课程 A")
    course_b = _create_teacher_course(client, other_teacher_token, "归属课程 B")

    create_resp = client.post(
        "/api/questions",
        json={
            "course_id": course_a,
            "type": "choice",
            "stem": "带星级共享题",
            "options": ["A. 对", "B. 错"],
            "answer": "A",
            "explanation": "",
            "tags": [],
            "star_rating": 5,
        },
        headers=auth_header(teacher_token),
    )
    assert create_resp.json()["code"] == 0

    owner_list = client.get(
        f"/api/questions?course_id={course_a}",
        headers=auth_header(teacher_token),
    ).json()
    owner_item = next(item for item in owner_list["data"]["items"] if item["stem"] == "带星级共享题")
    assert owner_item["created_by"] == "T001"
    assert owner_item["creator_name"]
    assert owner_item["star_rating"] == 5
    assert owner_item["is_owner"] is True

    peer_list = client.get(
        f"/api/questions?course_id={course_b}",
        headers=auth_header(other_teacher_token),
    ).json()
    peer_item = next(item for item in peer_list["data"]["items"] if item["stem"] == "带星级共享题")
    assert peer_item["created_by"] == "T001"
    assert peer_item["creator_name"] == owner_item["creator_name"]
    assert peer_item["star_rating"] == 5
    assert peer_item["is_owner"] is False


def test_update_question_enforces_stem_hash_and_rewrites_hash(client, teacher_token, db_session):
    """编辑题干时沿用同题干 hash 拦截，并在成功后回写 stem_hash。"""
    from app.services.question_service import _compute_stem_hash

    course_id = _create_teacher_course(client, teacher_token, "编辑哈希课程")
    first = client.post(
        "/api/questions",
        json={
            "course_id": course_id,
            "type": "fill",
            "stem": "原始题干甲",
            "options": [],
            "answer": "甲",
            "explanation": "",
            "tags": [],
        },
        headers=auth_header(teacher_token),
    )
    second = client.post(
        "/api/questions",
        json={
            "course_id": course_id,
            "type": "fill",
            "stem": "原始题干乙",
            "options": [],
            "answer": "乙",
            "explanation": "",
            "tags": [],
        },
        headers=auth_header(teacher_token),
    )
    assert first.json()["code"] == 0
    assert second.json()["code"] == 0
    second_id = second.json()["data"]["id"]

    conflict = client.put(
        f"/api/questions/{second_id}",
        json={
            "course_id": course_id,
            "type": "fill",
            "stem": "原始题干甲",
            "options": [],
            "answer": "乙",
            "explanation": "",
            "tags": [],
        },
        headers=auth_header(teacher_token),
    )
    assert conflict.json()["code"] == 400

    ok = client.put(
        f"/api/questions/{second_id}",
        json={
            "course_id": course_id,
            "type": "fill",
            "stem": "更新后的题干乙",
            "options": [],
            "answer": "乙",
            "explanation": "",
            "tags": [],
        },
        headers=auth_header(teacher_token),
    )
    assert ok.json()["code"] == 0
    updated = db_session.query(Question).filter(Question.id == second_id).one()
    assert updated.stem_hash == _compute_stem_hash("更新后的题干乙")


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
        f"/api/courses/{public_course_id}/add",
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
    assert source.created_by == "admin"
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
    assert db_session.query(Question).filter(
        Question.course_id == public_course_id,
        Question.created_by == "admin",
    ).count() == 2
    assert db_session.query(Question).filter(Question.source_question_id.isnot(None)).count() == 0

    log = db_session.query(QuestionContributionLog).one()
    assert log.public_course_id == public_course_id
    assert log.operator_id == "admin"
    assert log.action == "import"
    assert log.question_count == 2


def test_admin_import_reports_duplicate_rows_as_skipped(client):
    """管理员导入共享题库时，重复题干应单独计入跳过而不是显示为成功 0、失败 0。"""
    admin_token = _admin_token(client)
    public_course_id = _create_public_course(client, admin_token, "共享导入跳过统计课")
    excel = _build_question_import_file(
        ["题型", "标签", "题干", "选项（选择题用 | 分隔）", "答案", "解析"],
        [["choice", "重复", "1+1=?", "A. 1|B. 2|C. 3|D. 4", "B", ""]],
    )

    response = client.post(
        f"/api/admin/public-courses/{public_course_id}/questions/import",
        files={
            "file": (
                "questions.xlsx",
                excel,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers=auth_header(admin_token),
    )

    data = response.json()["data"]
    assert data["success_count"] == 0
    assert data["skip_count"] == 1
    assert data["fail_count"] == 0
    assert len(data["skips"]) == 1
    assert data["errors"] == []


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
        "/api/courses",
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
    assert db_session.query(Question).filter(
        Question.course_id == private_course_id,
        Question.created_by == "T001",
    ).count() == 2


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


def test_admin_can_delete_shared_question_from_any_public_course_entry(
    client,
    db_session,
    teacher_token,
):
    """共享题库删除不再要求题目 course_id 等于当前公共课入口。"""
    admin_token = _admin_token(client)
    public_course_id = _create_public_course(client, admin_token, "删除入口公共课")
    teacher_course_id = _create_teacher_course(client, teacher_token, "教师私有挂课题")

    create_resp = client.post(
        "/api/questions",
        json={
            "course_id": teacher_course_id,
            "type": "fill",
            "stem": "跨课入口可删题",
            "options": [],
            "answer": "答案",
            "explanation": "",
            "tags": [],
        },
        headers=auth_header(teacher_token),
    )
    assert create_resp.json()["code"] == 0
    question_id = create_resp.json()["data"]["id"]

    delete_resp = client.delete(
        f"/api/admin/public-courses/{public_course_id}/questions/{question_id}",
        headers=auth_header(admin_token),
    )
    assert delete_resp.json()["code"] == 0
    deleted = db_session.query(Question).filter(Question.id == question_id).one()
    assert deleted.deleted_at is not None


def test_admin_batch_delete_shared_questions(client, db_session, teacher_token):
    """管理员可批量删除共享题库题目。"""
    admin_token = _admin_token(client)
    public_course_id = _create_public_course(client, admin_token, "批量删除公共课")
    teacher_course_id = _create_teacher_course(client, teacher_token, "批量删除挂课")

    ids = []
    for stem in ("批量删除题 A", "批量删除题 B"):
        resp = client.post(
            "/api/questions",
            json={
                "course_id": teacher_course_id,
                "type": "fill",
                "stem": stem,
                "options": [],
                "answer": "A",
                "explanation": "",
                "tags": [],
            },
            headers=auth_header(teacher_token),
        )
        assert resp.json()["code"] == 0
        ids.append(resp.json()["data"]["id"])

    batch_resp = client.post(
        f"/api/admin/public-courses/{public_course_id}/questions/batch-delete",
        json={"question_ids": ids + [999999]},
        headers=auth_header(admin_token),
    )
    data = batch_resp.json()
    assert data["code"] == 0
    assert data["data"]["deleted_count"] == 2
    assert sorted(data["data"]["deleted_ids"]) == sorted(ids)
    assert data["data"]["missing_ids"] == [999999]
    rows = db_session.query(Question).filter(Question.id.in_(ids)).all()
    assert len(rows) == 2
    assert all(row.deleted_at is not None for row in rows)


def test_teacher_can_edit_own_question_when_mount_course_soft_deleted(
    client,
    db_session,
    teacher_token,
):
    """教师可编辑自己创建、挂载课已软删且题目未删的共享题，不必改挂。"""
    from datetime import datetime, timezone

    course_id = _create_teacher_course(client, teacher_token, "待软删挂载课")
    created = client.post(
        "/api/questions",
        json={
            "course_id": course_id,
            "type": "fill",
            "stem": "挂载课软删后仍可编辑",
            "options": [],
            "answer": "原答案",
            "explanation": "",
            "tags": [],
            "star_rating": 3,
        },
        headers=auth_header(teacher_token),
    ).json()
    assert created["code"] == 0
    question_id = created["data"]["id"]

    course = db_session.get(Course, course_id)
    course.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    # 接口要求 course_id；不改挂时继续提交原挂载课 ID（即使该课已软删）
    response = client.put(
        f"/api/questions/{question_id}",
        json={
            "course_id": course_id,
            "type": "fill",
            "stem": "挂载课软删后已更新题干",
            "options": [],
            "answer": "新答案",
            "explanation": "仅改内容",
            "tags": ["软删挂载"],
            "star_rating": 5,
        },
        headers=auth_header(teacher_token),
    )
    data = response.json()
    assert response.status_code == 200, data
    assert data["code"] == 0
    # 教师编辑接口成功时可能只返回 ok，以库内状态为准
    db_session.expire_all()
    stored = db_session.get(Question, question_id)
    assert stored.stem == "挂载课软删后已更新题干"
    assert stored.answer == "新答案"
    assert stored.star_rating == 5
    assert stored.course_id == course_id
    assert stored.deleted_at is None


def test_create_rejects_same_stem_on_soft_deleted_mount_course(client, teacher_token, db_session):
    """新增撞上挂载课已软删但仍活跃的同题干时，必须判重拒绝。"""
    from datetime import datetime, timezone

    course_a = _create_teacher_course(client, teacher_token, "同干挂载课A")
    course_b = _create_teacher_course(client, teacher_token, "同干挂载课B")
    first = client.post(
        "/api/questions",
        json={
            "course_id": course_a,
            "type": "fill",
            "stem": "挂载课软删后仍占题干",
            "options": [],
            "answer": "答案",
            "explanation": "",
            "tags": [],
        },
        headers=auth_header(teacher_token),
    ).json()
    assert first["code"] == 0

    course = db_session.get(Course, course_a)
    course.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    second = client.post(
        "/api/questions",
        json={
            "course_id": course_b,
            "type": "fill",
            "stem": "挂载课软删后仍占题干",
            "options": [],
            "answer": "答案",
            "explanation": "",
            "tags": [],
        },
        headers=auth_header(teacher_token),
    ).json()
    assert second["code"] == 400
    assert "相同题目" in second["message"]


def test_admin_create_rejects_same_stem_on_soft_deleted_mount_course(client, teacher_token, db_session):
    """管理员新增撞上已软删挂载课上的活跃同题干时，必须判重拒绝。"""
    from datetime import datetime, timezone

    admin_token = _admin_token(client)
    public_course_id = _create_public_course(client, admin_token, "管理新增判重公共课")
    teacher_course_id = _create_teacher_course(client, teacher_token, "管理新增判重挂课")
    first = client.post(
        "/api/questions",
        json={
            "course_id": teacher_course_id,
            "type": "choice",
            "stem": "管理端撞软删挂载同干",
            "options": ["A", "B"],
            "answer": "A",
            "explanation": "",
            "tags": [],
        },
        headers=auth_header(teacher_token),
    ).json()
    assert first["code"] == 0

    course = db_session.get(Course, teacher_course_id)
    course.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    second = client.post(
        f"/api/admin/public-courses/{public_course_id}/questions",
        json={
            "type": "choice",
            "stem": "管理端撞软删挂载同干",
            "options": ["A", "B"],
            "answer": "A",
            "explanation": "",
            "tags": [],
        },
        headers=auth_header(admin_token),
    ).json()
    assert second["code"] == 400
    assert "相同题目" in second["message"]


def test_admin_question_delete_audit_uses_real_operator(client, db_session, teacher_token):
    """管理员删题审计必须记录真实操作者，不得写死 admin 字符串身份。"""
    from app.models.entities import AuditLog

    admin_token = _admin_token(client)
    public_course_id = _create_public_course(client, admin_token, "审计身份公共课")
    teacher_course_id = _create_teacher_course(client, teacher_token, "审计身份挂课")
    created = client.post(
        "/api/questions",
        json={
            "course_id": teacher_course_id,
            "type": "fill",
            "stem": "审计身份待删题",
            "options": [],
            "answer": "A",
            "explanation": "",
            "tags": [],
        },
        headers=auth_header(teacher_token),
    ).json()
    assert created["code"] == 0
    question_id = created["data"]["id"]

    delete_resp = client.delete(
        f"/api/admin/public-courses/{public_course_id}/questions/{question_id}",
        headers=auth_header(admin_token),
    )
    assert delete_resp.json()["code"] == 0

    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "question.delete", AuditLog.resource_id == str(question_id))
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit is not None
    assert audit.user_id == "admin"
    assert audit.user_role == "admin"
