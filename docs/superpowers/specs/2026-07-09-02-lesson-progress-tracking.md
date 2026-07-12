# 课程进度追踪系统设计

## 一、背景与目标

### 当前问题
- course_progress 只记录最后一个lesson_id
- 无法统计每个课时的完成情况
- 无法追踪学习时长
- 无法识别"刷课"行为
- 视频播放进度丢失

### 目标
1. 课时级进度追踪
2. 记录实际学习时长
3. 支持视频断点续播
4. 识别刷课行为
5. 教师端学习数据分析

## 二、数据库设计

### 2.1 新增 lesson_progress 表

```sql
CREATE TABLE lesson_progress (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(32) NOT NULL,
    course_id INT NOT NULL,
    lesson_id INT NOT NULL,
    status VARCHAR(16) DEFAULT 'not_started',
    progress_percent INT DEFAULT 0,
    last_position INT DEFAULT 0,
    duration_seconds INT DEFAULT 0,
    first_viewed_at DATETIME,
    last_viewed_at DATETIME,
    completed_at DATETIME,
    view_count INT DEFAULT 0,
    
    UNIQUE KEY uq_user_lesson (user_id, lesson_id),
    INDEX ix_lesson_progress_user_course (user_id, course_id),
    INDEX ix_lesson_progress_status (status),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
);
```

字段说明：
- status: not_started / in_progress / completed
- progress_percent: 0-100
- last_position: 视频秒数或PDF页码
- duration_seconds: 实际学习时长（累加）
- view_count: 访问次数

### 2.2 ORM 模型

```python
class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id"),
        Index("ix_lesson_progress_user_course", "user_id", "course_id"),
    )
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"))
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"))
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"))
    
    status = Column(String(16), default="not_started")
    progress_percent = Column(Integer, default=0)
    last_position = Column(Integer, default=0)
    duration_seconds = Column(Integer, default=0)
    
    first_viewed_at = Column(DateTime, nullable=True)
    last_viewed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    view_count = Column(Integer, default=0)
    
    user = relationship("User")
    course = relationship("Course")
    lesson = relationship("Lesson")
```

## 三、API 接口设计

### 3.1 上报学习进度
POST /api/courses/{course_id}/lessons/{lesson_id}/progress

请求体：
```json
{
  "progress_percent": 45,
  "last_position": 270,
  "duration_seconds": 30
}
```

业务逻辑：
- 首次访问创建记录，设置first_viewed_at
- 累加duration_seconds
- 更新last_viewed_at和view_count
- progress_percent >= 90时自动标记completed

### 3.2 查询课程进度
GET /api/courses/{course_id}/progress

响应：
```json
{
  "total_lessons": 20,
  "completed_lessons": 8,
  "total_duration": 3600,
  "completion_rate": 40.0,
  "lessons": [
    {
      "lesson_id": 1,
      "title": "第一课",
      "status": "completed",
      "progress_percent": 100,
      "duration_seconds": 180
    }
  ]
}
```

### 3.3 教师查看学生进度
GET /api/classes/{class_id}/students/{user_id}/progress

响应：学生在该班级关联课程的详细进度

### 3.4 课程学习统计
GET /api/courses/{course_id}/analytics

响应：
```json
{
  "avg_completion_rate": 65.5,
  "avg_duration": 4200,
  "most_viewed_lessons": [...],
  "low_completion_lessons": [...]
}
```

## 四、前端改动

### 4.1 学生学习页面
组件: LearnView.vue / CourseDetailView.vue

功能：
- 每30秒心跳上报进度
- 视频播放器记录currentTime
- 页面卸载时最后一次上报
- 进入课时时恢复last_position

代码示例：
```typescript
let progressTimer: NodeJS.Timeout

onMounted(() => {
  // 恢复播放进度
  if (lessonProgress.value?.last_position) {
    videoPlayer.currentTime = lessonProgress.value.last_position
  }
  
  // 启动心跳上报
  progressTimer = setInterval(() => {
    updateProgress({
      progress_percent: calculateProgress(),
      last_position: videoPlayer.currentTime,
      duration_seconds: 30
    })
  }, 30000)
})

onUnmounted(() => {
  clearInterval(progressTimer)
  // 最后一次上报
  updateProgress(...)
})
```

### 4.2 教师端进度统计
组件: TeacherCourseAnalytics.vue

显示：
- 班级整体完成率
- 每个学生的课时完成情况
- 平均学习时长
- 识别刷课学生（duration < 30%且已完成）

## 五、数据迁移

```python
def upgrade():
    op.create_table(
        'lesson_progress',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.String(32), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('lesson_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(16), default='not_started'),
        sa.Column('progress_percent', sa.Integer(), default=0),
        sa.Column('last_position', sa.Integer(), default=0),
        sa.Column('duration_seconds', sa.Integer(), default=0),
        sa.Column('first_viewed_at', sa.DateTime(), nullable=True),
        sa.Column('last_viewed_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('view_count', sa.Integer(), default=0),
        
        sa.UniqueConstraint('user_id', 'lesson_id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lesson_id'], ['lessons.id'], ondelete='CASCADE')
    )
    
    op.create_index('ix_lesson_progress_user_course', 'lesson_progress', ['user_id', 'course_id'])
    op.create_index('ix_lesson_progress_status', 'lesson_progress', ['status'])

def downgrade():
    op.drop_table('lesson_progress')
```

## 六、测试计划

单元测试：
- 首次访问课时创建进度
- 心跳上报累加时长
- 进度达90%自动完成
- 断点续播恢复位置

集成测试：
- 学生完整学习流程
- 教师查看班级进度
- 刷课行为识别

性能测试：
- 100学生并发上报进度
- 查询1000条进度记录耗时

## 七、实施风险

高风险：
- 并发写入：大量学生同时学习
  - 缓解：INSERT ... ON DUPLICATE KEY UPDATE
  - 缓解：考虑Redis缓存批量写入

中风险：
- 存储成本：1000学生 × 50课时 = 5万条记录
  - 缓解：按学期归档旧数据
- 前端心跳耗电：移动端电池消耗
  - 缓解：移动端降低频率到60秒

低风险：
- 新表不影响现有功能

## 八、服务器部署

部署步骤：
1. 备份数据库
2. 拉取代码
3. 执行迁移：alembic upgrade head
4. 重启后端
5. 构建前端

验证清单：
- 学生观看视频，检查进度上报
- 刷新页面，检查断点续播
- 教师端查看班级进度统计
- 检查数据库lesson_progress表数据

性能监控：
- 监控INSERT耗时
- 监控表大小增长

## 九、后续优化

1. 资料进度追踪（PDF、视频资料）
2. 学习路径推荐（根据进度推荐下一课时）
3. 学习报告（周报、月报）
4. 学习排行榜
5. 学习提醒（长时间未学习推送通知）


## 十、实施记录（2026-07-09）

本轮已完成规格中 02/03/04 的第一版落地，范围限定为课程进度追踪系统本身，不包含软删除、通知扩展等其他独立规格。

### 已落地内容
- 后端新增 `LessonProgress` ORM 模型与 `lesson_progress` 兼容建表逻辑，记录用户、课程、课时、完成状态、完成百分比、断点位置、累计学习时长、首次/最后学习时间、完成时间和访问次数。
- 新增课时进度上报接口：`POST /api/courses/{course_id}/lessons/{lesson_id}/progress`。
- 扩展课程进度查询：`GET /api/courses/{course_id}/progress` 保留 `last_lesson_id`，并返回课时明细、完成课时数、总学习时长和完成率。
- 新增教师端数据接口：`GET /api/classes/{class_id}/students/{student_id}/progress` 与 `GET /api/courses/{course_id}/analytics`。
- 学生课程详情页接入 30 秒心跳上报、页面隐藏/卸载前最后一次上报、视频 `currentTime` 断点采集与恢复；学习馆进度展示改为优先使用后端完成率。
- `last_position` 保存最近一次上报位置，允许学生回退复习后从实际离开位置继续；完成百分比仍保留历史最大值。浏览器 `pagehide` 场景使用带 JWT 的 `fetch keepalive` 补报，降低刷新或关闭标签页时丢失进度的概率。
- 教师课程详情新增“学习分析”标签页，展示班级学生数、课时数、整体完成率、平均学习时长、每个学生课时完成情况、热门/低完成课时和疑似刷课次数。
- 课程分析接口补充 `student_progress` 明细，前端 `progress.ts` 增加完整分析类型和 `getCourseAnalytics` 封装。
- 删除课时时会同步清理 `lesson_progress` 记录，并继续清空旧 `course_progress.last_lesson_id`，避免悬空引用。

### 验证记录
- `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_lessons_progress.py backend/tests/test_030405_management_systems.py -q`：22 passed, 1 warning。
- `node ./tests/teacher-course-analytics-static.test.mjs`：教师课程学习分析静态检查通过。
- `frontend` 下 `npm run build`：type-check 与 Vite build 均通过，仅保留既有大 chunk 体积警告。
- 真实浏览器验收：教师登录后访问 `/teacher/courses/1` 的“学习分析”标签，`GET /api/courses/1/analytics` 返回 200；页面正确渲染班级学生数、课时数、完成率、平均学习时长、学生明细、热门课时和低完成课时，1440px 视口无横向溢出，控制台 0 error / 0 warning。

### 服务器部署影响
- 需要备份数据库。
- 需要服务器拉取代码并重启后端，启动兼容层会创建 `lesson_progress` 表；如服务器改用 Alembic，应补正式迁移并执行 `alembic upgrade head`。
- 需要重新构建并部署前端静态资源。
- 不需要修改环境变量或 Nginx 配置。

### 补充验证记录（2026-07-09）
- 02/03/04/05 后端组合验证：`backend\.venv\Scripts\python.exe -m pytest backend/tests/test_lessons_progress.py backend/tests/test_030405_management_systems.py -q`，结果 `22 passed, 1 warning`。
- 通知中心前端静态验证：`node ./tests/notification-center-static.test.mjs`，结果通过。
- 教师课程学习分析静态验证：`node ./tests/teacher-course-analytics-static.test.mjs`，结果通过。
- 前端完整构建验证：`frontend` 下执行 `npm run build`，结果 type-check 与 Vite build 均通过；仅保留既有大 chunk 体积警告。
- 服务器部署影响更新：本次最终实现需要服务器拉取代码、重启后端、重新构建并部署前端静态资源；需要数据库兼容层创建/补齐 `lesson_progress`、软删除字段、通知偏好/模板等表字段；不需要修改环境变量或 Nginx 配置。

## 十一、并发、访问次数与分析分页修正（2026-07-11）

### 最终语义

- `LessonProgressIn` 增加 `visit_started: bool = False`。真实进入课时传 `true`，30 秒心跳、视频结束上报和最终补报均传 `false`；`view_count` 只在真实进入时增加。
- `LessonProgress` 与 `CourseProgress` 按数据库方言执行原子 upsert；时长与访问次数直接由 SQL 表达式累加，完成百分比和完成状态只前进不回退。
- `App.vue` 使用路由 `path` 作为组件 key，只改变 `lesson_id` 不会重建课程页。隐藏、`pagehide` 与卸载统一调用带门闩的 keepalive 补报，页面重新可见后再开启下一周期。
- 无视频课时显示“完成本课”，学生主动提交 100%；视频课时继续按播放位置计算完成百分比。
- `GET /api/courses/{course_id}/analytics?page=&page_size=` 的学生明细返回 `{items,total,page,page_size}`。有效学生、学生汇总和课时汇总在数据库完成，教师端使用服务端分页。
- 疑似刷课仍只统计已完成记录；正播放位置使用整数等价式计算 30% 阈值，避免 SQLite/MySQL 浮点差异。

### 验证记录

- 阶段 B 进度与分析回归：`16 passed, 1 skipped, 1 warning`；跳过项为未配置 `TEST_MYSQL_URL` 的 MySQL 并发用例。
- 100 名学生 × 20 个课时规模用例确认不加载任何 `LessonProgress` ORM，分析查询数保持常数。
- 非视频完成、进度上报和教师分析静态测试通过；前端全部静态测试与生产构建通过。
- 本地未执行 MySQL 实库和真实浏览器角色流程。

### 服务器部署影响

- 需要服务器拉取代码、重启后端、重新构建并部署前端静态资源。
- 本次修正不新增表或字段，不需要数据库迁移，不需要修改环境变量或 Nginx 配置。
