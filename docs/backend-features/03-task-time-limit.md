# 任务时限与完成追踪 - 后端需求

## 数据模型

### task_completions 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK auto | 主键 |
| announcement_id | Integer FK(announcements.id) NOT NULL | 公告/任务ID |
| user_id | String(32) FK(users.id) NOT NULL | 学生ID |
| completed_at | DateTime | 完成时间 |

唯一约束：(announcement_id, user_id)

## API 端点（追加到 announcement_routes）

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | /api/announcements/{id}/complete | student | 标记任务完成（幂等） |
| GET | /api/announcements/{id}/completion-report | teacher | 获取完成报告 |

## 完成报告返回结构

```json
{
  "announcement_id": 1,
  "announcement_title": "第一章课后练习",
  "class_name": "2025级1班",
  "total_students": 30,
  "completed_students": 25,
  "incomplete_students": [
    {"id": "2025006", "name": "赵同学"},
    {"id": "2025007", "name": "钱同学"}
  ],
  "is_expired": true
}
```

## 业务逻辑

### 时限判断
- 若当前时间 > end_time，则 is_expired = true
- 过期后学生仍可标记完成，但前端会显示"已截止"标签

### 记录完成
- INSERT INTO task_completions，使用 INSERT IGNORE 或 try-catch 实现幂等
- 适用于 quiz 类型任务：学生完成所有题目的提交即自动标记完成
- 适用于 announcement 类型任务：学生手动点击"已知晓"标记完成
