"""题库导入重复检测测试。"""
import io

import openpyxl
from app.models.entities import Question
from app.services.question_service import import_questions_from_excel


def _make_excel_rows(rows: list[dict]) -> list[dict]:
    """将列表形式转为 import_questions_from_excel 需要的 dict 列表。"""
    return rows


def _build_import_excel(headers: list[str], data_rows: list[list[str]]) -> bytes:
    """构建一个 Excel 文件，返回 bytes。"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in data_rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class TestImportDuplicateDetection:
    """验证题库导入时重复题干被跳过而非报错。"""

    def test_duplicate_stem_is_skipped(self, db_session):
        """相同课程、相同题干的题目再次导入时应跳过，而非重复插入。"""
        # 种子数据已有：course_id=1, stem="1+1=?"
        rows = [
            {"题型": "choice", "课程名称": "测试课程", "题干": "1+1=?",
             "选项": "A. 1|B. 2|C. 3|D. 4", "答案": "B", "解析": "基础加法"},
        ]
        result = import_questions_from_excel(db_session, rows, "T001")
        assert result["success_count"] == 0
        assert result["skip_count"] == 1
        assert result["fail_count"] == 0
        assert len(result["skips"]) == 1
        assert "已存在相同题目" in result["skips"][0]["reason"]

    def test_new_stem_is_imported(self, db_session):
        """不同题干的题目应正常导入。"""
        rows = [
            {"题型": "fill", "课程名称": "测试课程", "题干": "太阳从哪边升起？",
             "选项": "", "答案": "东方", "解析": "地理常识"},
        ]
        result = import_questions_from_excel(db_session, rows, "T001")
        assert result["success_count"] == 1
        assert result["skip_count"] == 0
        assert result["fail_count"] == 0
        assert len(result["skips"]) == 0

    def test_import_splits_multiple_tags(self, db_session):
        """标签列支持用多种分隔符填写多个标签，并去重保存。"""
        rows = [
            {"题型": "fill", "课程名称": "测试课程", "标签": "人工智能,基础|人工智能、通识",
             "题干": "什么是机器学习？", "选项": "", "答案": "算法", "解析": "测试解析"},
        ]
        result = import_questions_from_excel(db_session, rows, "T001")

        assert result["success_count"] == 1
        created = db_session.query(Question).filter(Question.stem == "什么是机器学习？").one()
        assert created.tags == ["人工智能", "基础", "通识"]

    def test_mixed_new_and_duplicate(self, db_session):
        """混合导入：新题目成功，重复题目跳过。"""
        rows = [
            {"题型": "choice", "课程名称": "测试课程", "题干": "1+1=?",
             "选项": "A. 1|B. 2|C. 3|D. 4", "答案": "B", "解析": ""},
            {"题型": "fill", "课程名称": "测试课程", "题干": "水的化学式？",
             "选项": "", "答案": "H2O", "解析": ""},
            {"题型": "fill", "课程名称": "测试课程", "题干": "光速约多少？",
             "选项": "", "答案": "3×10^8 m/s", "解析": ""},
        ]
        result = import_questions_from_excel(db_session, rows, "T001")
        assert result["success_count"] == 2
        assert result["skip_count"] == 1
        assert result["fail_count"] == 0
        assert len(result["skips"]) == 1
        assert "1+1=?" in result["skips"][0]["reason"]

    def test_same_stem_different_course_is_skipped_in_shared_bank(self, db_session):
        """全站共享题库：不同课程下导入相同题目也会被全站查重拦截并跳过。"""
        rows = [
            {"题型": "choice", "课程名称": "其它课程", "题干": "1+1=?",
             "选项": "A. 1|B. 2|C. 3|D. 4", "答案": "B", "解析": ""},
        ]
        result = import_questions_from_excel(db_session, rows, "T002")
        assert result["success_count"] == 0
        assert result["skip_count"] == 1
        assert "已存在相同题目" in result["skips"][0]["reason"]

    def test_import_skips_same_stem_on_soft_deleted_mount_course(self, db_session):
        """导入目标课活跃，但同题干挂在已软删课程上时仍应 skip，不得重复入库。"""
        from datetime import datetime, timezone

        from app.models.entities import Course

        existing = db_session.query(Question).filter(Question.stem == "1+1=?").one()
        mount = db_session.get(Course, existing.course_id)
        mount.deleted_at = datetime.now(timezone.utc)
        db_session.commit()

        # 导入到另一门仍活跃的教师课
        other = db_session.query(Course).filter(Course.name == "其它课程").one()
        assert other.deleted_at is None
        rows = [
            {"题型": "choice", "课程名称": "其它课程", "题干": "1+1=?",
             "选项": "A. 1|B. 2|C. 3|D. 4", "答案": "B", "解析": "撞软删挂载"},
        ]
        before = db_session.query(Question).count()
        result = import_questions_from_excel(db_session, rows, "T002")
        assert result["success_count"] == 0
        assert result["skip_count"] == 1
        assert "已存在相同题目" in result["skips"][0]["reason"]
        assert db_session.query(Question).count() == before

    def test_import_skips_same_stem_hash_even_if_options_differ(self, db_session):
        """已有 stem_hash 时，导入同题干但不同选项/答案也应跳过。"""
        from app.services.question_service import _compute_stem_hash

        existing = db_session.query(Question).filter(Question.stem == "1+1=?").one()
        existing.stem_hash = _compute_stem_hash(existing.stem)
        db_session.commit()

        rows = [
            {"题型": "choice", "课程名称": "测试课程", "题干": "1+1=?",
             "选项": "A. 一|B. 二|C. 三|D. 四", "答案": "A", "解析": "不同选项也应跳过"},
        ]
        before = db_session.query(Question).count()
        result = import_questions_from_excel(db_session, rows, "T001")
        assert result["success_count"] == 0
        assert result["skip_count"] == 1
        assert result["fail_count"] == 0
        assert "已存在相同题目" in result["skips"][0]["reason"]
        assert db_session.query(Question).count() == before

    def test_import_via_api_skips_duplicates(self, client, teacher_token):
        """通过 API 上传 Excel，重复题目应返回 skip_count。"""
        from tests.conftest import auth_header

        excel_bytes = _build_import_excel(
            ["题型", "课程名称", "题干", "选项", "答案", "解析"],
            [
                ["choice", "测试课程", "1+1=?", "A. 1|B. 2|C. 3|D. 4", "B", "基础加法"],
                ["fill", "测试课程", "地球的自转周期？", "", "约24小时", ""],
            ],
        )
        resp = client.post(
            "/api/questions/import",
            headers=auth_header(teacher_token),
            files={"file": ("test.xlsx", excel_bytes,
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["success_count"] == 1
        assert data["data"]["skip_count"] == 1
        assert data["data"]["fail_count"] == 0
        assert len(data["data"]["skips"]) == 1
