# 项目地图

## 当前架构

- 前端：`frontend/`，Vue 3 + TypeScript + Vite + Element Plus。
- 后端：`backend/`，FastAPI + SQLAlchemy。
- 部署：`deploy/nginx.conf` 提供生产 Nginx 示例，托管前端 `dist` 并反代 `/api/`、`/uploads/` 到后端 `8050`。
- 存储：第一阶段上线默认 `STORAGE_BACKEND=local`，`LOCAL_UPLOAD_DIR` 指向服务器持久化上传目录；S3/SeaweedFS/MinIO 作为第二阶段对象存储接入任务。
- 测试：`backend/tests/`，SQLite 内存库。

## 核心业务结构

教师端已改为以课程为归属根：

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
- 课程与题库服务：`backend/app/services/question_service.py`
- 发布题目服务：`backend/app/services/announcement_service.py`
- 任务完成服务：`backend/app/services/task_service.py`
- 教师统计/学生成绩/作品审核服务：`backend/app/services/teacher_service.py`

## 教师端页面

- `/teacher`：概述
- `/teacher/courses`：课程管理
- `/teacher/classes`：班级管理
- `/teacher/publish`：发布题目
- `/teacher/grades`：学生成绩
- `/teacher/task-report`：任务完成报告
- `/teacher/reviews`：作品审核
- `/teacher/materials`：资料管理
- `/teacher/student-admin`：学生管理
- `/teacher/questions`：题库管理

## 学生端页面

- `/learn`：课程列表
- `/learn/course/:courseId`：课程资料
- `/practice`：按课程练习入口
- `/practice/quiz/:courseId`：课程练习
- `/practice/announcement/:announcementId`：题目任务练习
- `/inbox`：题目任务通知

## 长期约定

- 不再使用独立章节表、章节 API 或章节页面。
- 资料、题目和作品全部直接挂在课程下；答题统计以 `QuizAttempt` 为事实来源。
- 新上传文件统一通过 `file_id` 访问 `/api/files/{id}`；旧 `/uploads/xxx` 仅作兼容。
- 生产环境预览 PDF/视频优先新窗口查看，Nginx 必须代理 `/api/` 和 `/uploads/`，并透传 `Range`/`If-Range` 以支持视频分段读取。
- 第一阶段部署不要求 S3 端点存在；部署前通过 `backend/scripts/check_deploy_env.py` 校验本地上传目录可写、MySQL 可连接和安全配置未使用默认值。
- 班级必须归属一门课程。
- 发布题目可一次选择同一课程下的多个班级。
- 题目任务练习必须通过任务维度记录 `QuizAttempt.announcement_id`；任务完成和教师完成报告按该任务下每题最新一次答题结果统计。
- 学生提交作品必须选择自己已加入班级对应的课程；教师只能审核自己课程范围内的作品。
- 教师只能访问自己创建的课程及其下属班级、资料、题目、学生成绩和作品审核范围。
