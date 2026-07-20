# 共享题库标签：手输 + 选用已有标签

- 状态：已实现（本地完成，未提交 git）
- 日期：2026-07-19
- 范围：教师端 `/teacher/questions`、管理员端 `/admin/question-bank`
- 方案：后端聚合标签接口 + 前端 `el-select` 选项（方案 A）

## 1. 背景与问题

共享题库「新增/编辑题目」弹窗中，标签控件为：

```vue
el-select multiple filterable allow-create default-first-option
```

但未提供 `el-option`，教师/管理员只能手输后回车，无法从题库已有标签中点选。列表顶部标签筛选也是普通输入框，不能直接选用已有标签。

标签目前存放在题目 JSON 字段 `tags: string[]` 中，无独立标签表，也无标签聚合接口。

## 2. 目标

1. 新增/编辑题目时，标签支持：
   - 手动输入新标签（回车创建）
   - 从题库已有标签下拉点选
2. 列表顶部标签筛选支持：
   - 从已有标签选择
   - 继续手输关键词做模糊筛选（兼容现状）
3. 教师端与管理员端行为一致

## 3. 范围

### 3.1 范围内

| 端 | 页面/模块 | 改动点 |
|---|---|---|
| 教师 | `/teacher/questions` | 新增/编辑弹窗标签、列表标签筛选 |
| 管理员 | `/admin/question-bank` | 新增/编辑弹窗标签、列表标签筛选 |
| 后端 | 教师题库 + 管理员题库 | 各增加一个只读标签聚合接口 |

### 3.2 范围外

- 不建独立标签表，不改题目存储结构（仍为 `tags: string[]`）
- 不改 Excel 导入的标签规则
- 不改学生端、作业选题、公告选题中的标签展示或筛选
- 不做标签重命名、合并、全局删除管理
- 不改创建/更新题目接口语义
- 不引入标签缓存（题量上万后再议）
- 不把列表 `tag` 筛选从模糊匹配改为精确数组包含（若需要，单独立项）

## 4. 方案取舍

| 方案 | 做法 | 结论 |
|---|---|---|
| A（采用） | 后端聚合活跃题标签；前端弹窗与筛选绑定选项，保留 `allow-create` | 标签跨页完整，边界清晰 |
| B | 前端从当前列表拼装 | 翻页不全，已排除 |
| C | 打开弹窗时拉大 `page_size` 再提取 | 请求重且仍可能不全，已排除 |

## 5. 后端设计

### 5.1 新增接口

| 角色 | 方法 | 路径 | 权限 |
|---|---|---|---|
| 教师 | `GET` | `/api/questions/tags` | `teacher` |
| 管理员 | `GET` | `/api/admin/question-bank/tags` | `admin` |

两端各一条路由，避免跨角色调用权限耦合。服务层共用同一聚合逻辑（或管理员侧薄封装复用 helper）。

### 5.2 响应格式

沿用统一包装：

```json
{
  "code": 0,
  "data": ["机器学习", "深度学习", "人工智能"],
  "message": "ok"
}
```

`data` 为 `string[]`，不分页。

### 5.3 聚合规则

1. 数据源：活跃共享题，`Question.deleted_at IS NULL`
2. 字段：只读 `Question.tags`
3. 规范化：
   - `trim` 空白
   - 丢弃空字符串
   - 大小写敏感去重（与现有 `_normalize_tags` 一致，不合并 `AI` 与 `ai`）
4. 排序：稳定字符串升序（可用 `casefold()` 作为排序键，去重仍大小写敏感）
5. 不按课程、创建人、题型过滤（共享题库全站视角）
6. 软删题目的标签不出现

### 5.4 实现落点

- 服务层：在 `question_service` 或 `question_bank_service` 增加
  `list_question_tags(db) -> list[str]`
- 教师路由：`question_routes.py` 增加 `GET /tags`
- 管理员路由：`admin_question_bank_routes.py` 增加 `GET /tags`
- **路由注册顺序**：`/tags` 必须写在 `/{question_id}` 之前，避免被路径参数吞掉
- Schema：可直接返回 `list[str]`，不必新增复杂模型

### 5.5 列表筛选语义（不变）

现有列表查询参数 `tag` 继续为关键词模糊匹配（`ilike %tag%`）。
前端筛选改为下拉后，传给后端的仍是同一字符串：

- 选中已有标签 → 传精确词（通常等价于命中该标签）
- 手输关键词 → 仍模糊匹配

本轮**不修改**后端列表筛选实现。

### 5.6 性能约定

- 题量百～千级：查询活跃题 `tags` 后在 Python 侧去重即可
- 本轮不做 Redis/短缓存
- 本轮不做跨 SQLite/MySQL 的 JSON 展开复杂 SQL

## 6. 前端设计

### 6.1 文件

| 端 | 页面 | API 封装 |
|---|---|---|
| 教师 | `frontend/src/views/teacher/TeacherQuestions.vue` | `frontend/src/api/question.ts` → `getQuestionTags()` |
| 管理员 | `frontend/src/views/admin/AdminQuestionBank.vue` | `frontend/src/api/adminQuestionBank.ts` → `getQuestionBankTags()` |

两端各自改页面，不强制抽公共业务组件（避免无关重构）。

### 6.2 新增/编辑弹窗标签

保留：

- `multiple`
- `filterable`
- `allow-create`
- `default-first-option`

补齐 `el-option`，选项来自 `tagOptions`。

占位文案：`选择已有标签，或输入后回车创建`

保存逻辑不变：

```ts
tags: form.tags.map(item => item.trim()).filter(Boolean)
```

### 6.3 列表标签筛选

将 `el-input` 改为可清空的 `el-select`：

- `clearable`
- `filterable`
- `allow-create`
- `default-first-option`
- 选项绑定同一 `tagOptions`

占位文案：`选择或输入标签`

交互统一：

- 选中 / 清空即 `page = 1` 并刷新列表
- 管理员端可保留「查询」按钮，但 change/clear 也应刷新，避免两端手感不一致
- 请求参数仍为 `tag`

### 6.4 标签选项加载

```ts
const tagOptions = ref<string[]>([])

async function loadTagOptions() {
  try {
    tagOptions.value = await getQuestionTags() // 管理员侧用 getQuestionBankTags()
  } catch {
    tagOptions.value = []
  }
}
```

| 时机 | 动作 |
|---|---|
| 页面 `onMounted` | 与题目列表并行加载 |
| 新增/编辑保存成功后 | 重新拉取标签 |
| 导入成功后 | 重新拉取标签 |
| 打开弹窗时 | 不必每次强刷 |

标签接口失败时：

- 不阻断主列表
- 弹窗/筛选退化为「仅手输」，与现状底线一致
- 不弹致命错误

## 7. 错误处理与权限

| 场景 | 行为 |
|---|---|
| 标签接口失败 | `tagOptions = []`，主流程可用 |
| 空题库无标签 | 下拉为空，仅手输创建 |
| 保存失败 | 沿用现有提示 |
| 学生/游客访问标签接口 | 401/403，与题库接口一致 |

## 8. 验收标准

### 8.1 功能

1. 教师端新增：下拉可见已有标签，可点选
2. 教师端新增：可手输新标签并回车
3. 教师端编辑：已有标签回显，可增删，下拉可选
4. 教师端列表筛选：可选已有标签；可手输模糊词；可清空
5. 管理员端上述 1–4 同样通过
6. 保存成功后，新标签出现在后续下拉中
7. 软删题目上的标签不出现在聚合结果中

### 8.2 回归

8. 创建/编辑/导入接口与校验不变
9. 列表 `tag` 模糊筛选语义不变
10. 无数据库迁移、无环境变量变更

### 8.3 自动化

11. 后端：聚合去重/排序/软删过滤/权限
12. 前端：静态测试覆盖 API 封装与关键关键位
13. 教师/管理员相关已有测试不回归

## 9. 服务器部署影响

| 项 | 是否需要 |
|---|---|
| 拉代码 | 是 |
| 重启后端 | 是（新路由） |
| 重新构建前端 | 是 |
| 数据库迁移 | 否 |
| 环境变量/配置 | 否 |
| Nginx 调整 | 否 |

建议顺序：先后端标签接口，再发前端。若前端先发，标签下拉为空但仍可手输，不致命。

## 10. 风险与后续

| 风险 | 处理 |
|---|---|
| 题量增大后 Python 聚合变慢 | 本轮接受；后续可加缓存或 SQL 侧展开 |
| 大小写重复标签 | 与现有规范化一致，本轮不合并 |
| 模糊筛选命中子串 | 与现状一致；精确匹配另立项 |
| 作业选题页标签筛选未改 | 明确范围外；若需要另开需求 |

## 11. 预估涉及文件

### 后端

- `backend/app/services/question_service.py` 或 `question_bank_service.py`
- `backend/app/api/v1/routes/question_routes.py`
- `backend/app/api/v1/routes/admin_question_bank_routes.py`
- `backend/app/services/admin_question_bank_service.py`（如需薄封装）
- 对应测试文件

### 前端

- `frontend/src/api/question.ts`
- `frontend/src/api/adminQuestionBank.ts`
- `frontend/src/views/teacher/TeacherQuestions.vue`
- `frontend/src/views/admin/AdminQuestionBank.vue`
- 相关静态测试

### 文档

- 本设计文档
- 后续实施计划：`docs/superpowers/plans/2026-07-19-shared-question-tag-options.md`
- 实现完成后更新修改记录与部署说明
