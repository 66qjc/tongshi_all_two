# 班级管理 - 后端需求

## 数据模型

### classes 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK auto | 主键 |
| name | String(64) NOT NULL | 班级名称，如"2025级1班" |
| major | String(64) NOT NULL | 专业名称，如"自动化专业" |
| created_at | DateTime | 创建时间 |

### student_class_enrollment 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK auto | 主键 |
| user_id | String(32) FK(users.id) NOT NULL | 学生ID |
| class_id | Integer FK(classes.id) NOT NULL | 班级ID |
| enrolled_at | DateTime | 加入时间 |

关系：User 1:N StudentClassEnrollment, Class 1:N StudentClassEnrollment，均 cascade delete。

## API 端点

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | /api/classes | teacher | 列出所有班级（含 student_count） |
| POST | /api/classes | teacher | 创建班级 {name, major} |
| DELETE | /api/classes/{id} | teacher | 删除班级（级联删除注册关系） |
| GET | /api/classes/{id}/students | teacher | 列出班级学生 |
| POST | /api/classes/{id}/enroll | teacher | 手动添加学生 {student_id} |
| DELETE | /api/classes/{id}/enroll/{student_id} | teacher | 移除学生 |
| POST | /api/classes/import | teacher | Excel 批量导入学生 |

## Excel 导入格式

文件格式：.xlsx，第一行为表头。

| student_id | name | major | class_name |
|------------|------|-------|------------|
| 2025006 | 赵同学 | 自动化专业 | 2025级1班 |

处理逻辑：
1. 遍历每一行
2. 若 user 不存在，创建 User（role=student，默认密码 123456，pbkdf2_sha256 加密）
3. 若 class 不存在，创建 Class
4. 创建 StudentClassEnrollment（若不存在）
5. 返回统计：成功导入数、跳过数（已存在）、失败数及原因

## 依赖

- 新增 Python 依赖：openpyxl（requirements.txt）
- 修改 User 模型添加 enrollments 关系
