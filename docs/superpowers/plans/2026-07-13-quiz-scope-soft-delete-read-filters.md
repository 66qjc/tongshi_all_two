# 2026-07-13 自由练习提交范围 + 软删除读路径过滤

## 目标

在不改造正式删除入口、不调整上传/连接池的前提下，先堵住两个高风险读路径问题：

1. 学生自由练习可对越权题目提交并拿回标准答案
2. 已软删课程/班级/资料/作业/公开课在正常业务读路径仍可能可见

## 范围

### 已做

- 收紧 `submit_answer` 学生自由练习可见范围
- 统一活跃选课鉴权：`Class.deleted_at IS NULL` + `Course.deleted_at IS NULL`
- 资料列表/资料鉴权、作业可访问性、公开学习列表与文件解析补齐软删过滤
- 课程题目列表与题目访问鉴权排除软删资源
- 学生拉题接口不再预下发 `answer/explanation`；提交后由 `/quiz/submit` 回填
- 学生端练习页改为使用提交结果中的正确答案/解析高亮
- 新增/扩展后端测试

### 明确不做

- 不把各服务 `db.delete()` 正式删除入口统一改为 `soft_delete()`（完整 H1 / 阶段 D Task1）
- 不改 1GB 上传上限、DB 连接池、多 worker、Redis

## 关键实现

### 自由练习提交范围

- 文件：`backend/app/services/quiz_service.py`
- 规则：
  - 题目与所属课程必须未软删
  - 私有课题目：学生须加入该题所属活跃课程
  - 公共课题目：学生只要有任一活跃选课即可（保留全站共享公共题库）
  - 作业路径继续校验任务可访问 + `question_ids`
- 失败统一：`404 题目不存在`，不返回标准答案

### 软删除读路径过滤

| 文件 | 改动 |
|---|---|
| `backend/app/services/access_control_service.py` | `student_can_access_course` 过滤软删班课；新增 `student_has_active_course_enrollment` |
| `backend/app/services/material_service.py` | `list_materials` / `can_view_course_materials` 过滤软删 |
| `backend/app/services/task_service.py` | 作业访问要求作业/班级/课程均活跃；作业题目排除软删题 |
| `backend/app/services/public_learning_service.py` | 公开课与公开资料排除软删 |
| `backend/app/services/question_service.py` | `get_course_questions` / `can_view_course_questions` 排除软删 |

## 验证

```bash
backend/.venv/Scripts/python.exe -m pytest \
  backend/tests/test_access_control_service.py \
  backend/tests/test_quiz_submit_scope.py \
  backend/tests/test_soft_delete_read_filters.py \
  backend/tests/test_assignment_scoring.py \
  backend/tests/test_public_learning.py \
  -q --basetemp=backend/tmp/pytest-basetemp
```

结果：`33 passed`；前端 `node ./tests/practice-quiz-flow-static.test.mjs` 通过

## 服务器部署影响

- 需要：拉取代码、**重启后端服务**、**重新构建并部署前端**（练习页依赖提交结果回填答案）
- 不需要：数据库迁移、改 Nginx、改环境变量
- 说明：过滤生效后，历史上已软删但此前仍被业务读到的数据会从正常列表/鉴权中消失，这是预期行为

## 后续建议

1. 完整阶段 D Task1：正式删除入口统一软删除并保留关联
2. 2G2 核门禁：降低上传上限、限制预览并发、固化 2 worker 生产启动
3. Redis 缓存正确性修复后再启用多 worker 缓存
