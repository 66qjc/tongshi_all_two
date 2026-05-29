# 项目地图

本文件记录项目中长期有效的目录、页面、路由和服务清单，供代理和接手开发者快速定位。更新页面、核心路由或核心服务时，应同步维护本文件。

## 核心目录

- 前端源码：`frontend/src/`
- 教师端页面：`frontend/src/views/teacher/`
- 学生端页面：`frontend/src/views/`
- 后端路由：`backend/app/api/v1/routes/`
- 后端服务：`backend/app/services/`
- 后端模型：`backend/app/models/entities.py`
- 后端 Schema：`backend/app/schemas/common.py`
- 后端测试：`backend/tests/`
- 设计和计划文档：`docs/superpowers/specs/`、`docs/superpowers/plans/`

## 教师端页面

- `TeacherDashboard.vue`
- `TeacherMaterials.vue`
- `TeacherQuestions.vue`
- `TeacherStudents.vue`
- `TeacherClasses.vue`
- `TeacherAnnouncements.vue`
- `TeacherReviews.vue`
- `TeacherCourses.vue`
- `TeacherLayout.vue`

## 核心后端路由

- `auth_routes.py`
- `chapter_routes.py`
- `class_routes.py`
- `material_routes.py`
- `question_routes.py`
- `teacher_routes.py`：包含学生数据 Excel 导出接口 `GET /teacher/students/export`
- `announcement_routes.py`
- `quiz_routes.py`
- `project_routes.py`
- `portfolio_routes.py`
- `upload_routes.py`
- `file_routes.py`：统一文件访问 `GET /api/files/{file_id}`
- `admin_routes.py`：管理员教师账号 CRUD、批量导入、密码重置
- `profile_routes.py`：个人中心错题本、收藏作品
- `showcase_routes.py`：悟页面图文内容，管理员 CRUD，公开只读

## 核心后端服务

- `auth_service.py`
- `chapter_service.py`
- `class_service.py`
- `material_service.py`
- `question_service.py`
- `teacher_service.py`
- `announcement_service.py`
- `quiz_service.py`
- `project_service.py`
- `portfolio_service.py`
- `task_service.py`
- `file_service.py`

## 存储服务

- `storage_service.py`：存储抽象协议和 `StoredObject`
- `storage_local.py`：本地文件适配器
- `storage_s3.py`：SeaweedFS S3 适配器
- `file_service.py`：文件元数据写入、URL 构建、记录解析

## 优先测试文件

后端改动优先检查这些测试是否受影响：

- `backend/tests/test_auth.py`
- `backend/tests/test_integration_bugfixes.py`
- `backend/tests/test_schema_compat.py`
