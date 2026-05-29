# 项目地图

## 当前架构

- 前端：`frontend/`，Vue 3 + TypeScript + Vite + Element Plus。
- 后端：`backend/`，FastAPI + SQLAlchemy。
- 测试：`backend/tests/`，SQLite 内存库。

## 核心业务结构

教师端已改为以课程为归属根：

```text
User(teacher) -> Course -> Class -> StudentClassEnrollment -> User(student)
User(teacher) -> Course -> Material
User(teacher) -> Course -> Question -> QuizAttempt
User(teacher) -> Course -> StudentProgress
Announcement -> AnnouncementClass -> Class
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
- `/teacher/reviews`：作品审核
- `/teacher/materials`：资料管理
- `/teacher/student-admin`：学生管理
- `/teacher/questions`：题库管理

## 学生端页面

- `/learn`：课程列表
- `/learn/course/:courseId`：课程资料
- `/practice`：按课程练习入口
- `/practice/quiz/:courseId`：课程练习
- `/inbox`：题目任务通知

## 长期约定

- 不再使用独立章节表、章节 API 或章节页面。
- 资料、题目、学习进度全部直接挂在课程下。
- 班级必须归属一门课程。
- 发布题目可一次选择同一课程下的多个班级。
- 教师只能访问自己创建的课程及其下属班级、资料、题目、学生成绩和作品审核范围。
