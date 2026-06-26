# 课程资料阶段化与三端联动展示改造计划

> 日期：2026-06-25
> 状态：待实施
> 范围：学生端课程详情页、教师端课程详情管理、管理员端公共课程管理

## 一、要解决的问题

当前课程详情页以平铺的资料卡片列表呈现学习内容，存在以下问题：

1. **缺少学习结构感**：资料没有按主题/阶段分组，学生难以形成清晰的学习路径。
2. **目录定位困难**：没有侧边目录或阶段锚点，长课程滚动查找费时。
3. **同一主题资料分散**：一个阶段下可能需要多份资料补充，但现有结构无法挂在一起。
4. **目录名称无法维护**：学生端顶部时间线或目录的命名依赖前端硬编码，教师/管理员不能统一修改。
5. **学生端信息冗余**：课程详情 Hero 区展示“练习数”“班级数”，对学生学习没有直接帮助。
6. **教师和管理员管理不便**：教师端课程与资料管理分离，管理员端公共课程也以表格形式管理资料，不直观。

本次改造希望让课程资料支持**阶段/目录**组织，实现学生端“目录定位 + 时间线 + 每阶段下资料并排展示”，教师端和管理员端可统一维护阶段结构与阶段下资料。

## 二、现状（已核实代码）

### 后端

- `backend/app/models/entities.py`：
  - `Course` 模型仅有 `name`、`created_by`、`is_public`、`source_course_id`、`created_at`。
  - `Material` 模型仅有 `course_id`，没有阶段/目录归属字段。
  - 项目此前约定“不再使用独立章节表、章节 API 或章节页面”。
- `backend/app/schemas/common.py`：
  - `CourseUpdateRequest` / `CourseCreateRequest` 只包含 `name`、`is_public`。
  - `MaterialCreate` 不包含阶段字段。
- `backend/app/services/course_response_service.py`：
  - `build_course_detail` 返回课程信息 + 平铺资料列表。
- `backend/app/services/question_service.py` / `mirror_public_course_content`：
  - 公共课程被教师添加时，只复制 `materials` 和 `questions`，没有阶段概念。
- `backend/app/services/admin_public_course_service.py`：
  - 公共资料 CRUD 直接使用 `Material`，没有阶段分组。

### 前端

- `frontend/src/views/CourseDetailView.vue`：
  - Hero 区展示课程名、资料数、题目数、班级数。
  - 下方是资料网格（2 列）。
  - 没有目录、没有时间线、没有阶段概念。
- `frontend/src/views/teacher/TeacherCourses.vue`：
  - 只管理课程名称，不提供课程下阶段与资料的组织入口。
- `frontend/src/views/teacher/TeacherMaterials.vue`：
  - 按全部课程筛选管理资料，不以某一课程为根组织。
- `frontend/src/views/admin/AdminPublicCourses.vue`：
  - 左侧公共课程列表，右侧资料/题目表格。

## 三、方案选型

| 方案 | 说明 | 优点 | 缺点 |
| --- | --- | --- | --- |
| A. 新增阶段表（推荐） | 新增 `course_stages` 表，`materials` 增加 `stage_id` | 数据结构清晰；目录名称可维护；支持多资料挂同一阶段；学生教师管理员三端一致 | 需要数据库表变更；需要调整公共课程复制/同步逻辑 |
| B. 资料标题前缀分组 | 通过资料标题前缀（如“01-”）做视觉分组 | 不改数据库 | 名称无法统一维护；依赖教师命名规范；容易乱 |
| C. 只加字段不分组 | 在 Material 上加 `chapter_name` 字段 | 实现简单 | 每份资料重复写阶段名；改名成本高；无法排序阶段 |

### 推荐：方案 A

新增独立的 `course_stages` 阶段目录表，让阶段成为课程资料的组织单元。教师和管理员维护阶段名称与排序后，学生端目录、时间线、阶段区块自动同步。

> 该方案会调整项目此前“不再使用独立章节表”的约定，需在 `AGENTS.md` 与项目文档中同步更新。

## 四、数据结构设计

### 新增表：course_stages

```python
class CourseStage(Base):
    __tablename__ = "course_stages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    name = Column(String(64), nullable=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    course = relationship("Course", back_populates="stages")
    materials = relationship("Material", back_populates="stage")
```

### Course 模型补充 relationship

```python
class Course(Base):
    ...
    stages = relationship(
        "CourseStage",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="CourseStage.sort_order"
    )
```

### Material 模型补充字段

```python
class Material(Base):
    ...
    stage_id = Column(Integer, ForeignKey("course_stages.id"), nullable=True, index=True)
    stage = relationship("CourseStage", back_populates="materials")
```

### 设计约束

- 阶段为**单层结构**，不支持嵌套子阶段。
- 一个课程下阶段数量**不限制**。
- 阶段排序使用 `sort_order` 数字字段，越小越靠前。
- 一份资料最多归属一个阶段；暂时未归属阶段的资料 `stage_id` 为 NULL，学生端归入“未分类”或最后展示。
- 删除阶段时，若该阶段下仍有资料，系统**拒绝删除**并提示用户先移出或删除资料。

## 五、后端接口与 Schema 变更

### 新增 Schema

```python
class CourseStageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    sort_order: int = 0

class CourseStageUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None

class CourseStageOut(BaseModel):
    id: int
    course_id: int
    name: str
    sort_order: int
    created_at: Optional[str] = None

class CourseStageWithMaterials(CourseStageOut):
    materials: List[MaterialOut] = []
```

### Material Schema 调整

```python
class MaterialCreate(BaseModel):
    ...
    stage_id: Optional[int] = None

class MaterialOut(BaseModel):
    ...
    stage_id: Optional[int] = None
```

### 新增路由

- `GET /courses/{course_id}/stages` — 获取课程阶段列表（含每个阶段下的资料）。
- `POST /courses/{course_id}/stages` — 创建阶段。
- `PUT /stages/{stage_id}` — 更新阶段名称/排序。
- `DELETE /stages/{stage_id}` — 删除阶段（仅限空阶段）。

### 资料路由调整

- `POST /materials` 增加 `stage_id` 字段。
- `PUT /materials/{material_id}` 增加 `stage_id` 字段。
- 管理员端公共资料对应接口同步增加 `stage_id`。

### 课程详情返回结构

`GET /courses/{course_id}` 返回结构由：

```json
{ "code": 0, "data": { "course": {...}, "materials": [...] } }
```

改为：

```json
{
  "code": 0,
  "data": {
    "course": {...},
    "stages": [
      {
        "id": 1,
        "name": "导学：认识 AI",
        "sort_order": 1,
        "materials": [...]
      }
    ],
    "uncategorized_materials": [...]
  }
}
```

## 六、后端服务变更

1. **course_response_service.py**
   - `build_course_detail` 从“平铺资料”改为“按 stages 分组 + 未分类资料”。
   - 学生端只返回其已加入课程的资料，权限过滤逻辑保持不变。

2. **material_service.py**
   - 创建/更新资料时保存 `stage_id`。
   - 删除阶段前先校验阶段下是否还有资料。

3. **question_service.py**
   - `create_course`、`add_public_course` 复制公共课程时，同步复制 `CourseStage` 结构及其下资料。
   - 保持 `source_course_id` / `source_material_id` 等同步字段。

4. **admin_public_course_service.py**
   - 公共资料创建/更新支持 `stage_id`。
   - `sync_material_to_course_copies` 需将公共资料同步到教师副本的对应阶段中。

## 七、前端改造

### 学生端 `frontend/src/views/CourseDetailView.vue`

新布局：

```
┌────────────────────────────────────────────────────────┐
│  ← 返回课程列表                                          │
│  人工智能通识 A                                          │
│  课程简介...                                             │
│  📄 10 份资料 · 进度 3/6 阶段                             │
│  [继续学习 →] [查看练习]                                  │
├────────────────────────────────────────────────────────┤
│  1---2---3---4---5---6  （横向时间线，节点=阶段）          │
├────────────┬───────────────────────────────────────────┤
│ 课程目录    │  阶段 1 标题                                │
│ ○ 认识 AI   │  阶段描述...                                │
│ ○ 计算机基础│  [资料卡片] [资料卡片]                      │
│ ● AI 理论  │  [资料卡片]                                 │
│ ○ AI 工具  │                                           │
│ ○ 前沿应用 │  阶段 2 标题                                │
│ ○ AI 伦理  │  [资料卡片] [资料卡片]                      │
└────────────┴───────────────────────────────────────────┘
```

具体改动：

- Hero 区保留课程名、课程简介、资料数、学习进度，**去掉练习数和班级数**。
- 左侧固定目录：阶段列表，点击平滑滚动到对应阶段；当前所在阶段高亮。
- 顶部横向时间线：节点 = 阶段，点击可滚动定位。
- 右侧主内容区分阶段展示，每个阶段一个区块，阶段下资料用 2 列网格并排展示。
- 同一阶段下可挂多份资料。
- 资料状态（已完成/进行中/未开始）保留，已完成资料带勾选标识。

### 教师端

- `frontend/src/views/teacher/TeacherCourses.vue`
  - 课程列表表格增加“管理课程”操作入口。
- 新增 `frontend/src/views/teacher/TeacherCourseDetail.vue`
  - 顶部：课程名 + 课程简介 + 编辑课程信息按钮。
  - 阶段管理区：阶段名称输入框 + 排序数字 + 删除按钮；支持新增阶段。
  - 资料管理区：按阶段分组展示资料卡片网格；每张卡片有编辑/删除。
  - 上传资料弹窗：增加“所属阶段”下拉选择。
- 路由新增 `/teacher/courses/:courseId`。

### 管理员端 `frontend/src/views/admin/AdminPublicCourses.vue`

- 左侧公共课程列表保留。
- 右侧选中课程的内容区分成两个维度：
  - 阶段目录管理（同教师端）。
  - 按阶段分组的资料卡片（同教师端）。
- 题目管理保留原有逻辑，题目暂不归属阶段。

### 前端 API 调整

- `frontend/src/api/course.ts`
  - 课程详情返回类型改为 `CourseDetail = Course & { stages: StageWithMaterials[]; uncategorized_materials: Material[] }`。
  - 新增阶段相关接口。
- `frontend/src/api/material.ts`
  - `MaterialCreatePayload` / 更新类型增加 `stage_id`。
- `frontend/src/api/adminPublicCourse.ts`
  - 公共资料接口增加 `stage_id`。

## 八、数据库迁移脚本

如果使用手动迁移：

```sql
CREATE TABLE course_stages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    course_id INT NOT NULL,
    name VARCHAR(64) NOT NULL,
    sort_order INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX (course_id),
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);

ALTER TABLE materials ADD COLUMN stage_id INT NULL;
CREATE INDEX idx_materials_stage_id ON materials(stage_id);
ALTER TABLE materials ADD FOREIGN KEY (stage_id) REFERENCES course_stages(id) ON DELETE SET NULL;
```

如果使用项目现有 `schema_compat.py` 自动补列机制，则同步更新 `backend/app/db/schema_compat.py` 中的补列逻辑。

## 九、验收方式

### 后端

- 阶段 CRUD 接口可用，排序生效。
- 课程详情接口返回按阶段分组的资料。
- 创建/更新资料时可指定/修改阶段。
- 删除非空阶段被拒绝并给出中文提示。
- 公共课程被教师添加后，阶段结构和资料同步复制。
- 既有后端测试通过。

### 前端

- `frontend` 下执行 `npm run build` 通过。
- 学生端：目录点击可滚动定位到对应阶段；时间线节点可点击；阶段下资料并排展示。
- 教师端：可新增/编辑/删除阶段；上传资料可选择阶段；阶段资料网格展示正常。
- 管理员端：公共课程阶段与资料管理正常。
- 所有页面文案为正常中文，无乱码；空状态合理。

### 数据权限

- 学生只能看到自己已加入课程及其阶段资料。
- 教师只能管理自己创建的课程阶段与资料。
- 管理员管理公共课程阶段与资料，不影响教师私有课程。

## 十、范围边界

**在范围内：**
- 新增 `course_stages` 阶段目录表。
- `materials` 表增加 `stage_id`。
- 学生端课程详情页左侧目录 + 顶部时间线 + 阶段资料网格。
- 教师端课程详情管理（阶段 + 资料）。
- 管理员端公共课程阶段与资料管理。
- 公共课程复制时同步复制阶段结构。

**不在范围内：**
- 题目/练习暂不分阶段，仍直接归属课程。
- 阶段内拖拽排序（首版用 sort_order 数字排序，拖拽作为后续优化）。
- 首页课程大纲展示（本次不讨论）。
- `/learn` 课程列表页（只做必要的数据结构适配，不做视觉升级）。
- 资料学习进度记录（已完成/未开始状态若需真实数据支持，单独评估实现成本）。

## 十一、风险点

1. **与既有约定冲突**：项目 `AGENTS.md` 约定“不再使用独立章节表”，需同步更新文档说明引入 `course_stages` 的新约定。
2. **历史数据迁移**：现有资料 `stage_id` 为空，学生端需合理展示（如归入“未分类”或不展示）。
3. **公共课程同步逻辑变复杂**：`sync_material_to_course_copies` 需要处理阶段对齐，避免副本资料错位。
4. **移动端适配**：左侧固定目录在窄屏下需要隐藏或变为顶部横向目录，需单独处理响应式。

## 十二、服务器部署影响

实施完成后，服务器需要：

1. **拉取最新代码**。
2. **执行数据库变更**：
   - 新增 `course_stages` 表；
   - 为 `materials` 表增加 `stage_id` 字段及索引；
   - 或通过 `schema_compat.py` 自动补列（如项目已接入该机制）。
3. **重新构建前端**：在 `frontend` 目录执行 `npm run build`。
4. **重启后端服务**。

> 不需要修改 `.env` 或环境变量；不需要回填历史数据（未分类资料可继续展示）；不需要调整 Nginx 配置。

