# 公告/任务发布 - 后端需求

## 数据模型

### announcements 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK auto | 主键 |
| class_id | Integer FK(classes.id) NOT NULL | 发布目标班级 |
| teacher_id | String(32) FK(users.id) NOT NULL | 发布教师 |
| type | String(16) NOT NULL | "announcement" 或 "quiz" |
| title | String(128) NOT NULL | 标题 |
| content | Text | 公告正文（announcement 类型） |
| question_ids | JSON | 题目ID列表 [1,2,3]（quiz 类型） |
| start_time | DateTime nullable | 任务开始时间 |
| end_time | DateTime nullable | 任务截止时间 |
| created_at | DateTime | 创建时间 |

### announcement_reads 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK auto | 主键 |
| user_id | String(32) FK(users.id) NOT NULL | 学生ID |
| announcement_id | Integer FK(announcements.id) NOT NULL | 公告ID |
| read_at | DateTime | 阅读时间 |

## API 端点

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | /api/announcements | auth | 教师：自己发布的公告；学生：所在班级的公告 |
| POST | /api/announcements | teacher | 发布公告/任务 {class_id, type, title, content, question_ids, start_time, end_time} |
| DELETE | /api/announcements/{id} | teacher | 删除公告 |
| GET | /api/announcements/unread-count | student | 获取未读公告数量 |
| POST | /api/announcements/{id}/read | student | 标记公告为已读 |
| GET | /api/announcements/{id} | auth | 获取公告详情（含班级名、教师名） |

## 业务逻辑

### 学生获取公告列表
1. 查询学生所在所有班级的 ID
2. 查询这些班级的所有公告
3. LEFT JOIN announcement_reads 判断已读/未读
4. 关联 classes 表获取 class_name，关联 users 表获取 teacher_name
5. 按 created_at 降序排列

### 未读计数
```sql
SELECT COUNT(*) FROM announcements a
WHERE a.class_id IN (SELECT class_id FROM student_class_enrollment WHERE user_id = :uid)
AND a.id NOT IN (SELECT announcement_id FROM announcement_reads WHERE user_id = :uid)
```

### 前端展示字段
AnnouncementOut 需包含：id, class_id, class_name, teacher_id, teacher_name, type, title, content, question_ids, start_time, end_time, created_at, is_read
