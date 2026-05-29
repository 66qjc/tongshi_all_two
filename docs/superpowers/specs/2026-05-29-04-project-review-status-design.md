# 作品审核现状确认（04 · C 组域）

- 日期：2026-05-29
- 上级文档：[`00-教师端重构总览`](2026-05-29-00-teacher-refactor-overview-design.md)
- 归属：C 组（作品/文件存储）
- 拍板：D 组

---

## 1. 结论

作品审核（导航第 6 项）本轮**无功能改动**，现状已满足 C 组验收标准。本文档仅做核对清单，确保其它模块改动不波及作品审核链路。

## 2. 现状（梳理结论）

- 后端 `teacher_routes.py`：
  - `GET /teacher/projects?status=&page=&page_size=` 列表（分页）。
  - `POST /teacher/projects/{id}/approve`、`/reject`（带 `reason`）。
  - `GET /teacher/projects/batch-download` 批量下载 ZIP（`StreamingResponse` + 临时文件分块，内存可控）。
- 前端 `TeacherReviews.vue`：列表、状态筛选、详情抽屉、通过/驳回、PDF/图片预览、批量下载。
- 存储：`StoredFile` + `file_id`，`GET /api/files/{id}` 统一访问 + Range；上传魔数校验；历史 `/uploads/` 兼容。

## 3. 受其它模块改动牵连的核对项

| 牵连点 | 说明 | 处置 |
|--------|------|------|
| 教师归属 | 作品归属是学生 `author_id`，教师仅审核权；本轮"按课程隔离"**是否要求教师只审自己课程学生的作品**？| **需 D 组确认**：默认维持现状（教师可审全部待审作品）。若要隔离，需经"学生→班级→课程→教师"链路过滤，改动 `list_all_projects`。见开放问题。 |
| `entities.py` 共享改动 | 删 `Chapter`、改 `Material/Question` 等会改同一文件 | C 组只需保证 `Project/ProjectImage/StoredFile` 不被误删 |
| `teacher_routes.py` 共享改动 | 学生统计/导出与作品审核同文件 | 删 `published_chapters` 等统计时不动作品审核函数 |
| 学生成绩页 | 与作品审核无耦合 | 无需改 |

## 4. 验收（保持）

- 作品列表/审核/驳回/批量下载功能不回归。
- 新上传走对象存储（s3 模式）；旧 `/uploads/` 可访问。
- 批量下载流式输出不爆内存；上传有魔数校验。

## 5. 开放问题

1. **是否要求作品审核也按教师课程隔离**（教师只审自己课程下班级学生的作品）？
   - 维持现状（推荐，改动最小）：所有教师审全部待审作品。
   - 若隔离：需 `list_all_projects` 增加 `author_id ∈ (当前教师课程下班级的学生)` 过滤，并补测试。肯定需要去做隔离数据
   - 该问题与本轮"严格隔离"基调相关，请 D 组拍板。
