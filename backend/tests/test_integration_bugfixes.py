"""教师端重构回归测试。"""
import io
from pathlib import Path

from app.core.security import get_password_hash
from app.models.entities import Announcement, AnnouncementClass, Class, Course, Material, Project, Question, StoredFile, StudentClassEnrollment, TaskCompletion, User
from tests.conftest import auth_header



def make_stored_file(db_session, content_type="application/pdf", extension=".pdf", owner="admin"):
    """为公共课程资料测试快速构造一条 stored_files 记录。"""
    sf = StoredFile(
        biz_type="public_course_material",
        storage_provider="local",
        object_key=f"test/file{extension}",
        original_name=f"file{extension}",
        stored_name=f"file{extension}",
        extension=extension,
        content_type=content_type,
        size_bytes=100,
        sha256="0" * 64,
        status="active",
        created_by=owner,
    )
    db_session.add(sf)
    db_session.commit()
    db_session.refresh(sf)
    return sf.id
def _build_student_import_file(rows: list[list[str]]) -> io.BytesIO:
    """构造学生导入接口使用的 Excel 文件。"""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["学号", "姓名", "专业"])
    for row in rows:
        ws.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def _build_question_import_file(headers: list[str], rows: list[list[str]]) -> io.BytesIO:
    """构造题库导入接口使用的 Excel 文件。"""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


class TestTeacherRefactor:
    """覆盖课程锚定、教师隔离、班级和发布题目核心行为。"""

    def test_teacher_only_sees_own_courses(self, client, teacher_token, other_teacher_token):
        t1 = client.get("/api/courses", headers=auth_header(teacher_token)).json()
        t2 = client.get("/api/courses", headers=auth_header(other_teacher_token)).json()

        assert t1["code"] == 0
        assert [item["name"] for item in t1["data"]] == ["测试课程"]
        assert t2["code"] == 0
        assert [item["name"] for item in t2["data"]] == ["其它课程"]

    def test_course_detail_returns_course_counts_without_old_section_count(self, client, teacher_token):
        resp = client.get("/api/courses/1", headers=auth_header(teacher_token))
        data = resp.json()

        assert data["code"] == 0
        assert data["data"]["id"] == 1
        assert "material_count" in data["data"]
        assert data["data"]["question_count"] == 1
        assert data["data"]["class_count"] == 1

    def test_create_material_uses_course_id(self, client, teacher_token):
        payload = {
            "course_id": 1,
            "type": "pdf",
            "title": "测试讲义",
            "url": "/uploads/test-material.pdf",
            "size": "2 MB",
        }

        create_data = client.post("/api/materials", json=payload, headers=auth_header(teacher_token)).json()
        assert create_data["code"] == 0

        list_data = client.get("/api/materials?course_id=1", headers=auth_header(teacher_token)).json()
        created = next(item for item in list_data["data"]["items"] if item["id"] == create_data["data"]["id"])
        assert created["course_id"] == 1
        assert created["course_name"] == "测试课程"
        assert created["url"] == "/uploads/test-material.pdf"
        assert created["size"] == "2 MB"
        assert created["source_material_id"] is None
        assert created["is_synced"] is False

        delete_data = client.delete(f"/api/materials/{created['id']}", headers=auth_header(teacher_token)).json()
        assert delete_data["code"] == 0

    def test_teacher_cannot_create_material_for_other_teacher_course(self, client, other_teacher_token):
        resp = client.post(
            "/api/materials",
            json={"course_id": 1, "type": "pdf", "title": "越权资料"},
            headers=auth_header(other_teacher_token),
        )
        data = resp.json()

        assert data["code"] == 404
        assert "课程不存在" in data["message"]

    def test_delete_course_with_child_data_cleans_up_related_data(self, client, db_session, teacher_token):
        resp = client.delete("/api/courses/1", headers=auth_header(teacher_token))
        data = resp.json()

        assert data["code"] == 0
        assert db_session.query(Course).filter(Course.id == 1).first() is None
        assert db_session.query(Class).filter(Class.course_id == 1).count() == 0
        assert db_session.query(Question).filter(Question.course_id == 1).count() == 0

    def test_delete_empty_course_succeeds(self, client, teacher_token):
        create_data = client.post(
            "/api/courses",
            json={"name": "可删除空课程"},
            headers=auth_header(teacher_token),
        ).json()
        course_id = create_data["data"]["id"]

        resp = client.delete(f"/api/courses/{course_id}", headers=auth_header(teacher_token))
        assert resp.json()["code"] == 0

    def test_teacher_created_course_is_always_private(self, client, teacher_token):
        create_data = client.post(
            "/api/courses",
            json={"name": "教师私有课程测试", "is_public": True},
            headers=auth_header(teacher_token),
        ).json()
        assert create_data["code"] == 0

        courses = client.get("/api/courses", headers=auth_header(teacher_token)).json()["data"]
        created = next(item for item in courses if item["id"] == create_data["data"]["id"])
        assert created["is_public"] is False
        assert created["is_owner"] is True

    def test_teacher_edit_course_cannot_change_public_flag(self, client, db_session, teacher_token):
        course = Course(name="已有公共课程", created_by="T001", is_public=True)
        db_session.add(course)
        db_session.commit()

        resp = client.put(
            f"/api/courses/{course.id}",
            json={"name": "已有公共课程改名", "is_public": False},
            headers=auth_header(teacher_token),
        )
        assert resp.json()["code"] == 0

        db_session.refresh(course)
        assert course.name == "已有公共课程改名"
        assert course.is_public is True

    def test_add_public_course_creates_owned_copy_with_content(self, client, db_session, other_teacher_token):
        public_course = Course(name="共享公共课程", created_by="T001", is_public=True)
        db_session.add(public_course)
        db_session.flush()
        db_session.add(Material(course_id=public_course.id, type="pdf", title="共享资料", url="/uploads/shared.pdf", size="1 MB"))
        db_session.add(Question(type="choice", course_id=public_course.id, stem="共享题目", options=["A", "B"], answer="A"))
        db_session.commit()

        resp = client.post(f"/api/courses/{public_course.id}/add", headers=auth_header(other_teacher_token))
        data = resp.json()

        assert data["code"] == 0
        added_id = data["data"]["id"]
        added = db_session.query(Course).filter(Course.id == added_id).first()
        assert added is not None
        assert added.name == "共享公共课程"
        assert added.created_by == "T002"
        assert added.is_public is False
        # 资料仍复制到教师副本
        assert db_session.query(Material).filter(Material.course_id == added_id).count() == 1
        # 全站共享题库：题目不再复制副本，副本课程名下没有题目
        assert db_session.query(Question).filter(Question.course_id == added_id).count() == 0

        courses = client.get("/api/courses", headers=auth_header(other_teacher_token)).json()["data"]
        copied = next(item for item in courses if item["id"] == added_id)
        assert copied["is_owner"] is True
        assert copied["is_public"] is False
        assert copied["material_count"] == 1
        # 全站共享题库：题目数为全站题目总数（seed 1 题 + 公共课 1 题）
        assert copied["question_count"] == db_session.query(Question).count()

    def test_add_public_course_records_source_ids(self, client, db_session, other_teacher_token):
        public_course = Course(name="公共来源课程", created_by="T001", is_public=True)
        db_session.add(public_course)
        db_session.flush()
        public_material = Material(
            course_id=public_course.id,
            type="pdf",
            title="公共资料",
            url="/uploads/public.pdf",
            size="1 MB",
        )
        public_question = Question(
            type="choice",
            course_id=public_course.id,
            stem="公共题目",
            options=["A", "B"],
            answer="A",
        )
        db_session.add_all([public_material, public_question])
        db_session.commit()

        resp = client.post(
            f"/api/courses/{public_course.id}/add",
            headers=auth_header(other_teacher_token),
        )
        assert resp.json()["code"] == 0
        copy_id = resp.json()["data"]["id"]

        copied_course = db_session.query(Course).filter(Course.id == copy_id).first()
        assert copied_course.source_course_id == public_course.id

        copied_material = db_session.query(Material).filter(Material.course_id == copy_id).one()
        assert copied_material.source_material_id == public_material.id

        # 全站共享题库：题目不再复制到教师副本，副本课程名下没有题目
        assert db_session.query(Question).filter(Question.course_id == copy_id).count() == 0

    def test_admin_create_public_course_and_sync_material_to_teacher_copy(
        self,
        client,
        db_session,
        teacher_token,
        other_teacher_token,
    ):
        admin_token = client.post(
            "/api/token", json={"id": "admin", "password": "Admin#2026"}).json()["data"]["access_token"]

        create_resp = client.post(
            "/api/admin/public-courses",
            json={"name": "管理员公共课程"},
            headers=auth_header(admin_token),
        )
        assert create_resp.json()["code"] == 0
        public_course_id = create_resp.json()["data"]["id"]

        client.post(f"/api/courses/{public_course_id}/add", headers=auth_header(teacher_token))
        client.post(f"/api/courses/{public_course_id}/add", headers=auth_header(other_teacher_token))
        pdf_file_id = make_stored_file(db_session)

        material_resp = client.post(
            f"/api/admin/public-courses/{public_course_id}/materials",
            json={"type": "pdf", "title": "同步资料", "url": "/uploads/sync.pdf", "size": "1 MB", "file_id": pdf_file_id},
            headers=auth_header(admin_token),
        )
        assert material_resp.json()["code"] == 0
        source_material_id = material_resp.json()["data"]["id"]

        copies = db_session.query(Course).filter(Course.source_course_id == public_course_id).all()
        assert len(copies) == 2
        for copy in copies:
            mirrored = db_session.query(Material).filter(
                Material.course_id == copy.id,
                Material.source_material_id == source_material_id,
            ).first()
            assert mirrored is not None
            assert mirrored.title == "同步资料"

    def test_admin_question_changes_are_globally_visible_and_teacher_cannot_delete(
        self,
        client,
        db_session,
        teacher_token,
    ):
        admin_token = client.post(
            "/api/token", json={"id": "admin", "password": "Admin#2026"}).json()["data"]["access_token"]
        course_resp = client.post(
            "/api/admin/public-courses",
            json={"name": "公共题库课程"},
            headers=auth_header(admin_token),
        )
        public_course_id = course_resp.json()["data"]["id"]
        add_resp = client.post(f"/api/courses/{public_course_id}/add", headers=auth_header(teacher_token))
        copy_id = add_resp.json()["data"]["id"]

        question_resp = client.post(
            f"/api/admin/public-courses/{public_course_id}/questions",
            json={"type": "choice", "stem": "原题干", "options": ["A", "B"], "answer": "A", "explanation": "原解析"},
            headers=auth_header(admin_token),
        )
        source_question_id = question_resp.json()["data"]["id"]
        # 全站共享题库：题目原地保存在公共课程，不再复制副本
        source_q = db_session.query(Question).filter(Question.id == source_question_id).one()
        assert source_q.course_id == public_course_id
        assert source_q.source_question_id is None

        # 教师在自己副本课程入口也能看到这道全站共享题
        list_resp = client.get(f"/api/questions?course_id={copy_id}", headers=auth_header(teacher_token))
        listed = next(item for item in list_resp.json()["data"]["items"] if item["id"] == source_question_id)
        assert listed["stem"] == "原题干"
        assert listed["is_synced"] is False

        # 管理员改题 → 全站可见最新内容（无需同步副本）
        update_resp = client.put(
            f"/api/admin/public-courses/{public_course_id}/questions/{source_question_id}",
            json={"type": "choice", "stem": "新题干", "options": ["A", "B"], "answer": "B", "explanation": "新解析"},
            headers=auth_header(admin_token),
        )
        assert update_resp.json()["code"] == 0
        db_session.refresh(source_q)
        assert source_q.stem == "新题干"
        assert source_q.answer == "B"

        # 维持现状：教师不能编辑非自己创建的题（题归属公共课程/管理员）
        teacher_edit = client.put(
            f"/api/questions/{source_question_id}",
            json={"course_id": copy_id, "type": "choice", "stem": "教师改", "options": ["A"], "answer": "A", "explanation": ""},
            headers=auth_header(teacher_token),
        )
        assert teacher_edit.json()["code"] == 404
        db_session.refresh(source_q)
        assert source_q.stem == "新题干"

        # 维持现状：教师不能删除题目
        teacher_delete = client.delete(f"/api/questions/{source_question_id}", headers=auth_header(teacher_token))
        assert teacher_delete.json()["code"] == 403
        assert "教师不能删除题目" in teacher_delete.json()["message"]

        # 管理员删除 → 题目全站消失
        admin_delete = client.delete(
            f"/api/admin/public-courses/{public_course_id}/questions/{source_question_id}",
            headers=auth_header(admin_token),
        )
        assert admin_delete.json()["code"] == 0
        assert db_session.query(Question).filter(Question.id == source_question_id).first() is None

    def test_admin_public_question_tags_are_normalized(
        self,
        client,
        db_session,
        teacher_token,
    ):
        admin_token = client.post(
            "/api/token", json={"id": "admin", "password": "Admin#2026"}).json()["data"]["access_token"]
        course_resp = client.post(
            "/api/admin/public-courses",
            json={"name": "公共题目标签课程"},
            headers=auth_header(admin_token),
        )
        public_course_id = course_resp.json()["data"]["id"]
        # 教师添加该公共课，资料和阶段会复制副本；题目仍走全站共享
        client.post(f"/api/courses/{public_course_id}/add", headers=auth_header(teacher_token))

        create_resp = client.post(
            f"/api/admin/public-courses/{public_course_id}/questions",
            json={
                "type": "choice",
                "stem": "标签同步题",
                "options": ["A", "B"],
                "answer": "A",
                "explanation": "",
                "tags": [" AI ", "基础", "AI"],
            },
            headers=auth_header(admin_token),
        )

        assert create_resp.json()["code"] == 0
        # 标签去重、去空白
        assert create_resp.json()["data"]["tags"] == ["AI", "基础"]
        source_question_id = create_resp.json()["data"]["id"]
        # 全站共享题库：题目原地保存在公共课程，无副本
        source_q = db_session.query(Question).filter(Question.id == source_question_id).one()
        assert source_q.course_id == public_course_id
        assert source_q.tags == ["AI", "基础"]

        update_resp = client.put(
            f"/api/admin/public-courses/{public_course_id}/questions/{source_question_id}",
            json={
                "type": "choice",
                "stem": "标签同步题",
                "options": ["A", "B"],
                "answer": "B",
                "explanation": "",
                "tags": ["进阶", "基础", "进阶"],
            },
            headers=auth_header(admin_token),
        )

        assert update_resp.json()["code"] == 0
        assert update_resp.json()["data"]["tags"] == ["进阶", "基础"]
        db_session.refresh(source_q)
        assert source_q.tags == ["进阶", "基础"]

    def test_admin_import_public_questions_uses_selected_course_and_splits_tags(
        self,
        client,
        db_session,
        teacher_token,
    ):
        admin_token = client.post(
            "/api/token", json={"id": "admin", "password": "Admin#2026"}).json()["data"]["access_token"]
        course_resp = client.post(
            "/api/admin/public-courses",
            json={"name": "公共导入标签课程"},
            headers=auth_header(admin_token),
        )
        public_course_id = course_resp.json()["data"]["id"]
        client.post(f"/api/courses/{public_course_id}/add", headers=auth_header(teacher_token))
        excel = _build_question_import_file(
            ["题型", "标签", "题干", "选项（选择题用 | 分隔）", "答案", "解析"],
            [["choice", "人工智能,基础|多选", "公共导入标签题", "A. 对|B. 错", "A", "解析"]],
        )

        resp = client.post(
            f"/api/admin/public-courses/{public_course_id}/questions/import",
            files={"file": ("questions.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_header(admin_token),
        )

        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["success_count"] == 1
        assert data["data"]["fail_count"] == 0
        # 全站共享题库：题目原地写入公共课程，不再产生副本
        source = db_session.query(Question).filter(
            Question.course_id == public_course_id,
            Question.stem == "公共导入标签题",
        ).one()
        assert source.tags == ["人工智能", "基础", "多选"]
        assert source.source_question_id is None
        assert db_session.query(Question).filter(Question.source_question_id == source.id).count() == 0

    def test_admin_public_question_template_omits_course_name_column(self, client):
        admin_token = client.post(
            "/api/token", json={"id": "admin", "password": "Admin#2026"}).json()["data"]["access_token"]

        resp = client.get(
            "/api/admin/public-courses/questions/import/template",
            headers=auth_header(admin_token),
        )

        assert resp.status_code == 200
        workbook = __import__("openpyxl").load_workbook(io.BytesIO(resp.content))
        headers = [cell.value for cell in next(workbook.active.iter_rows(min_row=1, max_row=1))]
        assert headers == ["题型", "标签", "题干", "选项（选择题用 | 分隔）", "答案", "解析"]
        assert "课程名称" not in headers

    def test_teacher_can_delete_synced_material_without_deleting_public_source(self, client, db_session, teacher_token):
        admin_token = client.post(
            "/api/token", json={"id": "admin", "password": "Admin#2026"}).json()["data"]["access_token"]
        course_resp = client.post(
            "/api/admin/public-courses",
            json={"name": "公共资料课程"},
            headers=auth_header(admin_token),
        )
        public_course_id = course_resp.json()["data"]["id"]
        copy_resp = client.post(f"/api/courses/{public_course_id}/add", headers=auth_header(teacher_token))
        copy_id = copy_resp.json()["data"]["id"]
        pdf_file_id = make_stored_file(db_session)
        material_resp = client.post(
            f"/api/admin/public-courses/{public_course_id}/materials",
            json={"type": "pdf", "title": "只读资料", "url": "/uploads/readonly.pdf", "size": "1 MB", "file_id": pdf_file_id},
            headers=auth_header(admin_token),
        )
        source_material_id = material_resp.json()["data"]["id"]
        mirrored = db_session.query(Material).filter(
            Material.course_id == copy_id,
            Material.source_material_id == source_material_id,
        ).one()

        list_resp = client.get(f"/api/materials?course_id={copy_id}", headers=auth_header(teacher_token))
        listed = next(item for item in list_resp.json()["data"]["items"] if item["id"] == mirrored.id)
        assert listed["source_material_id"] == source_material_id
        assert listed["is_synced"] is True

        delete_resp = client.delete(f"/api/materials/{mirrored.id}", headers=auth_header(teacher_token))
        assert delete_resp.json()["code"] == 0
        assert db_session.query(Material).filter(Material.id == mirrored.id).first() is None
        assert db_session.query(Material).filter(Material.id == source_material_id).first() is not None

    def test_teacher_materials_list_excludes_public_source_materials(self, client, db_session, teacher_token):
        public_course = Course(name="Public Materials List Scope", created_by="admin", is_public=True)
        db_session.add(public_course)
        db_session.flush()
        public_material = Material(
            course_id=public_course.id,
            type="pdf",
            title="Public Source Material",
            url="/uploads/public-source.pdf",
            size="1 MB",
            date="2026-06-17",
        )
        db_session.add(public_material)
        db_session.commit()

        add_resp = client.post(
            f"/api/courses/{public_course.id}/add",
            headers=auth_header(teacher_token),
        )
        assert add_resp.json()["code"] == 0
        copied_course_id = add_resp.json()["data"]["id"]

        list_resp = client.get("/api/materials", headers=auth_header(teacher_token))
        assert list_resp.json()["code"] == 0
        items = list_resp.json()["data"]["items"]

        matched = [item for item in items if item["title"] == "Public Source Material"]
        assert len(matched) == 1
        assert matched[0]["course_id"] == copied_course_id
        assert matched[0]["source_material_id"] == public_material.id
        assert matched[0]["is_synced"] is True

    def test_delete_public_course_unlinks_teacher_copy_and_preserves_shared_questions(self, client, db_session, teacher_token):
        admin_token = client.post(
            "/api/token", json={"id": "admin", "password": "Admin#2026"}).json()["data"]["access_token"]
        course_resp = client.post(
            "/api/admin/public-courses",
            json={"name": "可删除公共课程"},
            headers=auth_header(admin_token),
        )
        public_course_id = course_resp.json()["data"]["id"]
        pdf_file_id = make_stored_file(db_session)
        material_resp = client.post(
            f"/api/admin/public-courses/{public_course_id}/materials",
            json={"type": "pdf", "title": "公共资料", "url": "/uploads/delete-source.pdf", "size": "1 MB", "file_id": pdf_file_id},
            headers=auth_header(admin_token),
        )
        question_resp = client.post(
            f"/api/admin/public-courses/{public_course_id}/questions",
            json={"type": "choice", "stem": "公共题目", "options": ["A", "B"], "answer": "A", "explanation": ""},
            headers=auth_header(admin_token),
        )
        question_id = question_resp.json()["data"]["id"]
        copy_resp = client.post(f"/api/courses/{public_course_id}/add", headers=auth_header(teacher_token))
        copy_id = copy_resp.json()["data"]["id"]

        delete_resp = client.delete(
            f"/api/admin/public-courses/{public_course_id}",
            headers=auth_header(admin_token),
        )
        assert delete_resp.json()["code"] == 0

        copied_course = db_session.query(Course).filter(Course.id == copy_id).one()
        assert copied_course.source_course_id is None

        copied_material = db_session.query(Material).filter(Material.course_id == copy_id).one()
        assert copied_material.source_material_id is None

        # 资料源仍按现状删除（mirror 资料分发未变）
        assert db_session.query(Material).filter(Material.id == material_resp.json()["data"]["id"]).first() is None
        # 全站共享题库：公共课名下的题不会被级联删除，而是转挂到其他课程保留在全站
        surviving = db_session.query(Question).filter(Question.id == question_id).first()
        assert surviving is not None
        assert surviving.course_id != public_course_id

    def test_teacher_can_delete_owned_course_copy_without_affecting_public_source(self, client, db_session, teacher_token):
        admin_token = client.post(
            "/api/token", json={"id": "admin", "password": "Admin#2026"}).json()["data"]["access_token"]
        course_resp = client.post(
            "/api/admin/public-courses",
            json={"name": "课程副本删除测试"},
            headers=auth_header(admin_token),
        )
        public_course_id = course_resp.json()["data"]["id"]
        pdf_file_id = make_stored_file(db_session)
        material_resp = client.post(
            f"/api/admin/public-courses/{public_course_id}/materials",
            json={"type": "pdf", "title": "副本资料", "url": "/uploads/delete-copy.pdf", "size": "1 MB", "file_id": pdf_file_id},
            headers=auth_header(admin_token),
        )
        question_resp = client.post(
            f"/api/admin/public-courses/{public_course_id}/questions",
            json={"type": "choice", "stem": "副本题目", "options": ["A", "B"], "answer": "A", "explanation": ""},
            headers=auth_header(admin_token),
        )
        copy_resp = client.post(f"/api/courses/{public_course_id}/add", headers=auth_header(teacher_token))
        copy_id = copy_resp.json()["data"]["id"]

        delete_resp = client.delete(f"/api/courses/{copy_id}", headers=auth_header(teacher_token))
        assert delete_resp.json()["code"] == 0
        assert db_session.query(Course).filter(Course.id == copy_id).first() is None
        assert db_session.query(Material).filter(Material.id == material_resp.json()["data"]["id"]).first() is not None
        assert db_session.query(Question).filter(Question.id == question_resp.json()["data"]["id"]).first() is not None
        assert db_session.query(Course).filter(Course.id == public_course_id).first() is not None

    def test_student_without_class_gets_empty_course_hint(self, client, db_session):
        student = User(
            id="2025888",
            name="未入班学生",
            hashed_password=get_password_hash("abc123"),
            role="student",
            major="测试",
        )
        db_session.add(student)
        db_session.commit()
        token = client.post("/api/token", json={"id": "2025888", "password": "abc123"}).json()["data"]["access_token"]

        resp = client.get("/api/courses", headers=auth_header(token))
        data = resp.json()

        assert data["code"] == 0
        assert data["data"]["courses"] == []

    def test_download_multi_choice_question_template(self, client, teacher_token):
        resp = client.get("/api/questions/import/template/multi_choice", headers=auth_header(teacher_token))

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert "multi-choice-question-template.xlsx" in resp.headers["content-disposition"]

    def test_classes_are_filtered_by_teacher_and_course(self, client, teacher_token, other_teacher_token):
        t1 = client.get("/api/classes", headers=auth_header(teacher_token)).json()
        t2 = client.get("/api/classes", headers=auth_header(other_teacher_token)).json()

        assert [item["name"] for item in t1["data"]] == ["2025级1班"]
        assert [item["name"] for item in t2["data"]] == ["2025级2班"]

        filtered = client.get("/api/classes?course_id=1&keyword=1班", headers=auth_header(teacher_token)).json()
        assert [item["name"] for item in filtered["data"]] == ["2025级1班"]

    def test_class_with_students_cannot_be_deleted(self, client, teacher_token):
        resp = client.delete("/api/classes/1", headers=auth_header(teacher_token))
        data = resp.json()

        assert data["code"] == 400
        assert "仍有学生" in data["message"]

    def test_create_class_without_legacy_major_column(self, client, teacher_token):
        """新增班级不应因旧库 classes.major NOT NULL 约束而 500。"""
        resp = client.post(
            "/api/classes",
            json={"name": "新测试班", "course_id": 1},
            headers=auth_header(teacher_token),
        )
        data = resp.json()

        assert data["code"] == 0
        assert isinstance(data["data"]["id"], int)

    def test_class_without_students_can_be_deleted(self, client, db_session, teacher_token):
        course = db_session.query(Course).filter(Course.created_by == "T001").first()
        cls = Class(name="空班级", course_id=course.id, created_by="T001")
        db_session.add(cls)
        db_session.commit()

        resp = client.delete(f"/api/classes/{cls.id}", headers=auth_header(teacher_token))
        assert resp.json()["code"] == 0

    def test_delete_empty_class_unlinks_shared_task_without_deleting_task(self, client, db_session, teacher_token):
        course = db_session.query(Course).filter(Course.created_by == "T001").first()
        owned_class = db_session.query(Class).filter(
            Class.course_id == course.id,
            Class.created_by == "T001",
        ).first()
        empty_class = Class(name="待删除空班", course_id=course.id, created_by="T001")
        task = Announcement(course_id=course.id, teacher_id="T001", type="quiz", title="多班共享任务", question_ids=[1])
        db_session.add_all([empty_class, task])
        db_session.flush()
        db_session.add_all([
            AnnouncementClass(announcement_id=task.id, class_id=owned_class.id),
            AnnouncementClass(announcement_id=task.id, class_id=empty_class.id),
            TaskCompletion(announcement_id=task.id, user_id="2025001"),
        ])
        task_id = task.id
        owned_class_id = owned_class.id
        empty_class_id = empty_class.id
        db_session.commit()

        resp = client.delete(f"/api/classes/{empty_class_id}", headers=auth_header(teacher_token))
        assert resp.json()["code"] == 0

        assert db_session.query(Announcement).filter(Announcement.id == task_id).first() is not None
        assert db_session.query(AnnouncementClass).filter(
            AnnouncementClass.announcement_id == task_id,
            AnnouncementClass.class_id == owned_class_id,
        ).first() is not None
        assert db_session.query(AnnouncementClass).filter(
            AnnouncementClass.announcement_id == task_id,
            AnnouncementClass.class_id == empty_class_id,
        ).first() is None
        assert db_session.query(TaskCompletion).filter(
            TaskCompletion.announcement_id == task_id,
            TaskCompletion.user_id == "2025001",
        ).first() is not None

    def test_import_students_rejects_existing_non_student_account(self, client, db_session, teacher_token):
        teacher = db_session.query(User).filter(User.id == "T002").one()
        original_name = teacher.name
        original_major = teacher.major
        file_obj = _build_student_import_file([
            ["T002", "被误导入的教师", "错误专业"],
            ["2025777", "新学生", "人工智能"],
        ])

        resp = client.post(
            "/api/classes/import",
            data={"class_id": "1"},
            files={
                "file": (
                    "students.xlsx",
                    file_obj,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            headers=auth_header(teacher_token),
        )
        data = resp.json()

        assert data["code"] == 0
        assert data["data"]["success_count"] == 1
        assert data["data"]["fail_count"] == 1
        assert data["data"]["errors"][0]["row"] == 2
        db_session.refresh(teacher)
        assert teacher.role == "teacher"
        assert teacher.name == original_name
        assert teacher.major == original_major
        assert db_session.query(StudentClassEnrollment).filter(
            StudentClassEnrollment.user_id == "T002",
            StudentClassEnrollment.class_id == 1,
        ).first() is None
        assert db_session.query(StudentClassEnrollment).filter(
            StudentClassEnrollment.user_id == "2025777",
            StudentClassEnrollment.class_id == 1,
        ).first() is not None

    def test_teacher_students_only_include_owned_classes(self, client, teacher_token):
        resp = client.get("/api/teacher/students", headers=auth_header(teacher_token))
        data = resp.json()

        assert data["code"] == 0
        assert [item["id"] for item in data["data"]["items"]] == ["2025001"]

    def test_teacher_students_include_task_completion_stats(self, client, db_session, teacher_token):
        course = db_session.query(Course).filter(Course.created_by == "T001").first()
        cls = db_session.query(Class).filter(Class.course_id == course.id).first()
        first = Announcement(course_id=course.id, teacher_id="T001", type="quiz", title="任务一", question_ids=[1])
        second = Announcement(course_id=course.id, teacher_id="T001", type="quiz", title="任务二", question_ids=[1])
        db_session.add_all([first, second])
        db_session.flush()
        db_session.add_all([
            AnnouncementClass(announcement_id=first.id, class_id=cls.id),
            AnnouncementClass(announcement_id=second.id, class_id=cls.id),
            TaskCompletion(announcement_id=first.id, user_id="2025001"),
        ])
        db_session.commit()

        resp = client.get("/api/teacher/students", headers=auth_header(teacher_token))
        data = resp.json()

        assert data["code"] == 0
        student = data["data"]["items"][0]
        assert student["completed_tasks"] == 1
        assert student["incomplete_tasks"] == 1
        assert student["task_completion_rate"] == 50

    def test_publish_questions_supports_multiple_classes_and_completion_report(self, client, db_session, teacher_token, student_token):
        course = db_session.query(Course).filter(Course.created_by == "T001").first()
        second_class = Class(name="同课2班", course_id=course.id, created_by="T001")
        second_student = User(id="2025999", name="同课学生", hashed_password=get_password_hash("abc123"), role="student")
        db_session.add_all([second_class, second_student])
        db_session.flush()
        db_session.add(StudentClassEnrollment(user_id=second_student.id, class_id=second_class.id))
        db_session.commit()

        create_data = client.post(
            "/api/announcements",
            json={
                "course_id": course.id,
                "class_ids": [1, second_class.id],
                "title": "课程练习",
                "question_ids": [1],
            },
            headers=auth_header(teacher_token),
        ).json()
        assert create_data["code"] == 0
        announcement_id = create_data["data"]["id"]

        answer = client.post(
            "/api/quiz/submit",
            json={"question_id": 1, "user_answer": "B", "announcement_id": announcement_id},
            headers=auth_header(student_token),
        ).json()
        assert answer["code"] == 0

        client.post(f"/api/announcements/{announcement_id}/complete", headers=auth_header(student_token))
        report = client.get(f"/api/announcements/{announcement_id}/completion-report", headers=auth_header(teacher_token)).json()

        assert report["code"] == 0
        assert report["data"]["total_students"] == 2
        assert report["data"]["completed_count"] == 1
        assert len(report["data"]["per_class"]) == 2

    def test_create_material_persists_file_id(self, client, db_session, teacher_token):
        stored = StoredFile(
            biz_type="upload",
            storage_provider="local",
            object_key="test-file-id-material.pdf",
            original_name="讲义.pdf",
            stored_name="test-file-id-material.pdf",
            content_type="application/pdf",
            extension=".pdf",
            size_bytes=100,
            created_by="T001",
        )
        db_session.add(stored)
        db_session.commit()

        create_resp = client.post(
            "/api/materials",
            json={
                "course_id": 1,
                "type": "pdf",
                "title": "file_id 测试资料",
                "url": f"/api/files/{stored.id}",
                "size": "0.1 MB",
                "file_id": stored.id,
            },
            headers=auth_header(teacher_token),
        )
        assert create_resp.json()["code"] == 0

        materials = client.get("/api/materials", headers=auth_header(teacher_token)).json()["data"]
        created = next(item for item in materials["items"] if item["id"] == create_resp.json()["data"]["id"])
        assert created["file_id"] == stored.id
        assert created["url"].startswith("/api/files/")

    def test_get_file_by_file_id_returns_streamed_content(self, client, db_session, teacher_token):
        from app.services.file_service import _local_adapter

        upload_dir = _local_adapter.root_dir
        upload_dir.mkdir(parents=True, exist_ok=True)
        test_file = upload_dir / "file-by-id-test.pdf"
        test_file.write_bytes(b"%PDF-1.4 test content")

        try:
            stored = StoredFile(
                biz_type="material",
                storage_provider="local",
                object_key="file-by-id-test.pdf",
                original_name="test.pdf",
                stored_name="file-by-id-test.pdf",
                content_type="application/pdf",
                extension=".pdf",
                size_bytes=21,
                created_by="T001",
            )
            db_session.add(stored)
            db_session.commit()

            resp = client.get(f"/api/files/{stored.id}", headers=auth_header(teacher_token))
            assert resp.status_code == 200
            assert resp.content.startswith(b"%PDF")
        finally:
            if test_file.exists():
                try:
                    test_file.unlink()
                except PermissionError:
                    pass

    def test_upload_rejects_wrong_magic_number_even_if_extension_matches(self, client, teacher_token):
        fake_content = b"This is not a real PDF file"
        resp = client.post(
            "/api/upload",
            files={"file": ("fake.pdf", io.BytesIO(fake_content), "application/pdf")},
            headers=auth_header(teacher_token),
        )
        assert resp.json()["code"] == 400

    def test_uploaded_pdf_can_be_opened_by_browser_without_auth_header(self, client, teacher_token):
        """上传返回的文件 URL 应能被浏览器直接打开，不能依赖 Authorization 头。"""
        pdf_content = b"%PDF-1.4 browser preview pdf"
        upload = client.post(
            "/api/upload",
            files={"file": ("preview.pdf", io.BytesIO(pdf_content), "application/pdf")},
            headers=auth_header(teacher_token),
        ).json()
        assert upload["code"] == 0

        resp = client.get(upload["data"]["url"])

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/pdf")
        assert "inline" in resp.headers["content-disposition"]
        assert resp.headers["content-length"] == str(len(pdf_content))
        assert resp.content.startswith(b"%PDF")

    def test_uploaded_mp4_supports_browser_range_without_auth_header(self, client, teacher_token):
        """视频标签发起 Range 请求时也无法带 Bearer Token，应可直接分段读取。"""
        mp4_content = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"0" * 64
        upload = client.post(
            "/api/upload",
            files={"file": ("lesson.mp4", io.BytesIO(mp4_content), "video/mp4")},
            headers=auth_header(teacher_token),
        ).json()
        assert upload["code"] == 0

        resp = client.get(upload["data"]["url"], headers={"Range": "bytes=0-15"})

        assert resp.status_code == 206
        assert resp.headers["content-type"].startswith("video/mp4")
        assert resp.headers["content-range"] == f"bytes 0-15/{len(mp4_content)}"
        assert resp.content == mp4_content[:16]

    def test_batch_download_only_uses_teacher_students(self, client, db_session, teacher_token, other_teacher_token):
        from app.services.file_service import _local_adapter

        upload_dir = _local_adapter.root_dir
        upload_dir.mkdir(parents=True, exist_ok=True)
        own_report = upload_dir / "own-report.pdf"
        other_report = upload_dir / "other-report.pdf"
        own_report.write_bytes(b"%PDF-1.4 own")
        other_report.write_bytes(b"%PDF-1.4 other")

        try:
            db_session.add(Project(
                title="本教师学生作品",
                author_id="2025001",
                major="自动化专业",
                description="测试",
                tags=[],
                report_url="/uploads/own-report.pdf",
                status="approved",
                date="2026-05-25",
            ))
            db_session.add(Project(
                title="其它教师学生作品",
                author_id="2025002",
                major="人工智能",
                description="测试",
                tags=[],
                report_url="/uploads/other-report.pdf",
                status="approved",
                date="2026-05-25",
            ))
            db_session.commit()

            resp = client.get("/api/teacher/projects/batch-download", headers=auth_header(teacher_token))
            assert resp.status_code == 200
            assert resp.content.startswith(b"PK")

            other_resp = client.get("/api/teacher/projects/batch-download", headers=auth_header(other_teacher_token))
            assert other_resp.status_code == 200
            assert other_resp.content.startswith(b"PK")
        finally:
            for path in (own_report, other_report):
                if path.exists():
                    path.unlink()


class TestProjectReview:
    """作品审核接口集成测试。"""

    def _create_project(self, client, student_token, title="测试作品", report_url=""):
        """辅助：学生创建作品，返回 project id。"""
        resp = client.post(
            "/api/projects",
            json={
                "course_id": 1,
                "title": title,
                "description": "测试描述",
                "tags": ["AI"],
                "report_url": report_url,
            },
            headers=auth_header(student_token),
        )
        assert resp.json()["code"] == 0
        return resp.json()["data"]["id"]

    def test_teacher_approve_project(self, client, student_token, teacher_token):
        """教师通过作品审核 → 状态变更为 approved。"""
        pid = self._create_project(client, student_token, "待审核作品")

        resp = client.post(
            f"/api/teacher/projects/{pid}/approve",
            headers=auth_header(teacher_token),
        )
        assert resp.json()["code"] == 0

        detail = client.get(f"/api/projects/{pid}", headers=auth_header(student_token)).json()
        assert detail["data"]["status"] == "approved"

    def test_teacher_reject_project_with_reason(self, client, student_token, teacher_token):
        """教师驳回作品 → 状态变更为 rejected，驳回理由不为空。"""
        pid = self._create_project(client, student_token, "要驳回的作品")

        resp = client.post(
            f"/api/teacher/projects/{pid}/reject",
            json={"reason": "报告格式不规范"},
            headers=auth_header(teacher_token),
        )
        assert resp.json()["code"] == 0

        detail = client.get(f"/api/projects/{pid}", headers=auth_header(student_token)).json()
        assert detail["data"]["status"] == "rejected"
        assert detail["data"]["reject_reason"] == "报告格式不规范"

    def test_non_teacher_cannot_approve(self, client, student_token):
        """非教师角色审核作品被拒绝。"""
        pid = self._create_project(client, student_token, "学生想审核")

        resp = client.post(
            f"/api/teacher/projects/{pid}/approve",
            headers=auth_header(student_token),
        )
        assert resp.json()["code"] == 403

    def test_approve_nonexistent_project_returns_error(self, client, teacher_token):
        """审核不存在的作品返回错误。"""
        resp = client.post(
            "/api/teacher/projects/99999/approve",
            headers=auth_header(teacher_token),
        )
        assert resp.json()["code"] == 404


class TestProjectLike:
    """作品点赞接口集成测试。"""

    def _create_project(self, client, student_token, title="点赞测试作品"):
        resp = client.post(
            "/api/projects",
            json={"course_id": 1, "title": title, "description": "测试描述", "tags": ["AI"]},
            headers=auth_header(student_token),
        )
        assert resp.json()["code"] == 0
        return resp.json()["data"]["id"]

    def _like(self, client, token, project_id):
        return client.post(
            f"/api/projects/{project_id}/like",
            headers=auth_header(token),
        )

    def test_like_project(self, client, student_token):
        """点赞作品 → liked=true, likes 计数增加。"""
        pid = self._create_project(client, student_token)

        result = self._like(client, student_token, pid).json()
        assert result["code"] == 0
        assert result["data"]["liked"] is True
        assert result["data"]["likes"] == 1

    def test_unlike_project(self, client, student_token):
        """取消点赞 → liked=false, likes 计数减少。"""
        pid = self._create_project(client, student_token)

        # 先点赞
        self._like(client, student_token, pid)
        # 再取消
        result = self._like(client, student_token, pid).json()
        assert result["code"] == 0
        assert result["data"]["liked"] is False
        assert result["data"]["likes"] == 0

    def test_double_like_is_idempotent(self, client, student_token):
        """重复点赞不累积，连续两次点赞 = 赞后取消，回到未赞状态。"""
        pid = self._create_project(client, student_token)

        self._like(client, student_token, pid)
        result = self._like(client, student_token, pid).json()

        # 赞后再次调用 = 取消点赞
        assert result["data"]["liked"] is False
        assert result["data"]["likes"] == 0

    def test_like_nonexistent_project_returns_error(self, client, student_token):
        """点赞不存在的作品返回 404。"""
        resp = self._like(client, student_token, 99999)
        assert resp.json()["code"] == 404


class TestProjectFullFlow:
    """作品完整流程 E2E 测试。"""

    def test_create_then_approve_then_visible_in_square(self, client, db_session, student_token, teacher_token):
        """学生创建 → 待审不可见 → 教师通过 → 广场可见。"""
        # 创建
        create = client.post(
            "/api/projects",
            json={"course_id": 1, "title": "完整流程测试", "description": "E2E", "tags": ["AI"]},
            headers=auth_header(student_token),
        ).json()
        assert create["code"] == 0
        pid = create["data"]["id"]

        # 待审状态下广场不可见
        square = client.get("/api/projects", headers=auth_header(student_token)).json()
        square_ids = [item["id"] for item in square["data"]["items"]]
        assert pid not in square_ids

        # 审核通过
        approve = client.post(
            f"/api/teacher/projects/{pid}/approve",
            headers=auth_header(teacher_token),
        ).json()
        assert approve["code"] == 0

        # 广场可见
        square_after = client.get("/api/projects", headers=auth_header(student_token)).json()
        square_ids_after = [item["id"] for item in square_after["data"]["items"]]
        assert pid in square_ids_after

    def test_rejected_project_can_be_resubmitted(self, client, db_session, student_token, teacher_token):
        """驳回后学生重新提交 → 状态变回 pending。"""
        # 创建 → 驳回
        create = client.post(
            "/api/projects",
            json={"course_id": 1, "title": "驳回重提交测试", "description": "描述", "tags": []},
            headers=auth_header(student_token),
        ).json()
        pid = create["data"]["id"]

        client.post(
            f"/api/teacher/projects/{pid}/reject",
            json={"reason": "格式不对"},
            headers=auth_header(teacher_token),
        )

        # 重新提交
        update = client.put(
            f"/api/projects/{pid}",
            json={"course_id": 1, "title": "驳回重提交测试（已修改）", "description": "改好了", "tags": ["AI"], "report_url": ""},
            headers=auth_header(student_token),
        ).json()
        assert update["code"] == 0

        detail = client.get(f"/api/projects/{pid}", headers=auth_header(student_token)).json()
        assert detail["data"]["status"] == "pending"


class TestBatchDownload:
    """批量下载测试。"""

    def test_empty_projects_returns_error(self, client, teacher_token):
        """没有可下载的作品时返回 404。"""
        resp = client.get("/api/teacher/projects/batch-download", headers=auth_header(teacher_token))
        assert resp.json()["code"] == 404

    def test_local_storage_batch_download(self, client, db_session, student_token, teacher_token):
        """本地存储模式下批量下载返回 ZIP。"""
        from app.services.file_service import _local_adapter

        upload_dir = _local_adapter.root_dir
        upload_dir.mkdir(parents=True, exist_ok=True)
        report_path = upload_dir / "batch-dl-test.pdf"
        report_path.write_bytes(b"%PDF-1.4 batch download test content")

        try:
            project = Project(
                title="下载测试作品",
                author_id="2025001",
                major="自动化专业",
                description="测试",
                tags=[],
                report_url="/uploads/batch-dl-test.pdf",
                status="approved",
                date="2026-05-25",
            )
            db_session.add(project)
            db_session.commit()

            resp = client.get(
                "/api/teacher/projects/batch-download",
                headers=auth_header(teacher_token),
            )
            assert resp.status_code == 200
            # ZIP 文件以 PK 开头
            assert resp.content[:2] == b"PK"
        finally:
            if report_path.exists():
                report_path.unlink()

    def test_batch_download_with_report_file_id(self, client, db_session, student_token, teacher_token):
        """通过 report_file_id（新方式）批量下载。"""
        from app.services.file_service import _local_adapter

        upload_dir = _local_adapter.root_dir
        upload_dir.mkdir(parents=True, exist_ok=True)
        local_file = upload_dir / "file-id-dl-test.pdf"
        local_file.write_bytes(b"%PDF-1.4 via stored_file")

        try:
            stored = StoredFile(
                biz_type="project_report",
                storage_provider="local",
                object_key="file-id-dl-test.pdf",
                original_name="report.pdf",
                stored_name="file-id-dl-test.pdf",
                content_type="application/pdf",
                extension=".pdf",
                size_bytes=24,
                created_by="2025001",
            )
            db_session.add(stored)
            db_session.flush()

            project = Project(
                title="file_id 下载测试",
                author_id="2025001",
                major="自动化专业",
                description="测试",
                tags=[],
                status="approved",
                date="2026-05-25",
                report_file_id=stored.id,
            )
            db_session.add(project)
            db_session.commit()

            resp = client.get(
                "/api/teacher/projects/batch-download",
                headers=auth_header(teacher_token),
            )
            assert resp.status_code == 200
            assert resp.content[:2] == b"PK"
        finally:
            if local_file.exists():
                local_file.unlink()
