# 题库增强 - 后端需求

## 数据模型

### courses 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK auto | 主键 |
| name | String(128) NOT NULL UNIQUE | 课程名称 |
| created_at | DateTime | 创建时间 |

### 修改 chapters 表
新增字段：
| 字段 | 类型 | 说明 |
|------|------|------|
| course_id | Integer FK(courses.id) nullable | 所属课程 |

## API 端点

### 课程管理
| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | /api/courses | auth | 列出所有课程 |
| POST | /api/courses | teacher | 创建课程 {name} |
| PUT | /api/courses/{id} | teacher | 修改课程 {name} |
| DELETE | /api/courses/{id} | teacher | 删除课程 |

### 题目批量导入
| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | /api/questions/import | teacher | Excel 批量导入题目 |

## Excel 导入格式

| type | chapter | stem | options | answer | explanation |
|------|---------|------|---------|--------|-------------|
| choice | 01 | 图灵测试由谁提出？ | A. 艾伦·图灵\|B. 约翰·麦卡锡\|C. 马文·明斯基\|D. 杰弗里·辛顿 | A | 图灵测试由英国数学家艾伦·图灵于1950年提出。 |
| fill | 03 | AI 的英文全称是 ______。 | | Artificial Intelligence | AI 即 Artificial Intelligence 的缩写。 |

字段说明：
- type: choice 或 fill
- chapter: 章节编号（如 01）或章节标题，用于匹配 chapters.num 或 chapters.title
- options: 选择题选项，用 | 分隔；填空题留空
- answer: 选择题填 A/B/C/D，填空题填标准答案

## 返回结构

```json
{
  "success_count": 8,
  "fail_count": 2,
  "errors": [
    {"row": 5, "reason": "未找到章节: 07"},
    {"row": 9, "reason": "题干为空"}
  ]
}
```

## 依赖

- 新增 Python 依赖：openpyxl（与班级管理共用）
