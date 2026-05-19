# 课程时间安排 - 后端需求

## 数据模型修改

### 修改 chapters 表
新增字段：
| 字段 | 类型 | 说明 |
|------|------|------|
| day_of_week | String(16) default "" | 星期几，如"周一"、"周三" |
| class_periods | String(32) default "" | 节次，如"1-3"表示第1到3节 |
| schedule_note | String(128) default "" | 备注，如"双周" |

## Schema 修改

ChapterOut 新增：
```python
day_of_week: str = ""
class_periods: str = ""
schedule_note: str = ""
```

新增 Schema：
```python
class ChapterScheduleUpdate(BaseModel):
    day_of_week: Optional[str] = None
    class_periods: Optional[str] = None
    schedule_note: Optional[str] = None
```

## API 端点

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| PUT | /api/chapters/{id}/schedule | teacher | 更新课程时间 |

## 业务逻辑

- 时间绑定在课程（章节）层级，不按班级区分
- 若后续需要按班级区分（专业课 vs 选修课），可扩展 class_chapter_schedule 表
- day_of_week 可选值：周一、周二、周三、周四、周五、周六、周日
- class_periods 格式：起始节-结束节（如 "1-3"）或单节（如 "5"）

## 前端展示

- 学生端 LearnView 章节卡片显示：`上课时间: 周三 第1-3节`
- 教师端 TeacherMaterials 可编辑每个章节的时间安排
