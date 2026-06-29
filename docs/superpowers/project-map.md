# 项目地图

## 当前架构

- 前端：`frontend/`，Vue 3 + TypeScript + Vite + Element Plus
- 后端：`backend/`，FastAPI + SQLAlchemy
- 部署：`deploy/nginx.conf` 负责生产 Nginx 示例，代理 `/api/` 和 `/uploads/` 到后端
- 存储：第一阶段默认本地上传目录，后续再接入 S3 / SeaweedFS / MinIO
- 测试：`backend/tests/`，以 SQLite 内存库为主

## 核心业务结构

```text
User(teacher) -> Course -> Class -> StudentClassEnrollment -> User(student)
User(teacher) -> Course -> Material
User(teacher) -> Course -> Question -> QuizAttempt
User(teacher) -> Course -> Project
Announcement -> AnnouncementClass -> Class
Announcement -> QuizAttempt(announcement_id) -> TaskCompletion
```

## 后端主要文件

- ORM：`backend/app/models/entities.py`
- Schema：`backend/app/schemas/common.py`
- 兼容层：`backend/app/db/schema_compat.py`
- 班级服务：`backend/app/services/class_service.py`
- 资料服务：`backend/app/services/material_service.py`
- 资料预览服务：`backend/app/services/material_preview_service.py`
- 题库服务：`backend/app/services/question_service.py`
- 公共课程题库贡献记录：`backend/app/services/question_contribution_service.py`
- 公告服务：`backend/app/services/announcement_service.py`
- 任务服务：`backend/app/services/task_service.py`
- 教师统计/成绩/作品审核：`backend/app/services/teacher_service.py`

## 教师端页面

- `/teacher`
- `/teacher/courses`
- `/teacher/classes`
- `/teacher/publish`
- `/teacher/grades`
- `/teacher/task-report`
- `/teacher/reviews`
- `/teacher/materials`
- `/teacher/student-admin`
- `/teacher/questions`

## 学生端页面

- `/learn`
- `/learn/course/:courseId`
- `/practice`
- `/practice/quiz/:courseId`
- `/practice/announcement/:announcementId`
- `/inbox`

## 长期约定

- 不再使用独立章节表、章节 API 或章节页面
- 资料、题目和作品都直接挂在课程下
- 答题统计以 `QuizAttempt` 为事实来源
- 新上传文件统一通过 `file_id` 访问 `/api/files/{id}`
- 生产环境预览 PDF / 视频优先走 Nginx 代理
- 第一阶段部署不要求 S3 端点存在
- 班级必须归属一门课程
- 发布题目可以一次选择同一课程下的多个班级
- 题目任务练习必须通过 `QuizAttempt.announcement_id` 记录任务维度
- 学生提交作品必须选择自己已加入班级对应的课程
- 教师只能访问自己创建的课程及其下属班级、资料、题目、学生成绩和作品审核范围
- 教师可以删除自己课程下的资料，包括公共课程同步到教师副本里的资料，但不会影响公共课程源
- 教师可以新增和编辑自己课程中的题目，但不能删除题目；题目删除仅由管理员执行
- 公共课程是所有教师共享的题库源。教师在公共课程副本里新增或导入题目时，会回写到源公共课程，再同步到所有教师副本
- 公共课程题库的新增与导入会记录到 `question_contribution_logs`，保存课程快照、操作人、动作类型、题目数量和时间
- 课程资料预览使用 `material_previews` 保存封面、摘要、页数、时长和处理状态
- 课程资料大文件打开优先走 `/api/materials/{material_id}/file`，后端鉴权后由 Nginx 内部目录传输
- 学生端和教师端资料展示统一使用图文资料卡片和站内预览；旧 `/api/files/{id}` 保留给图片、作品报告等通用文件访问
