# 通知系统扩展设计

## 一、背景与目标

### 当前问题
- student_notifications 只支持项目审核通知
- 缺少作业截止提醒
- 缺少成绩发布通知
- 缺少课程更新通知
- 无法批量发送通知

### 目标
1. 扩展通知类型（作业、成绩、课程）
2. 支持批量通知
3. 支持通知模板
4. 支持通知偏好设置
5. 优化通知查询性能

## 二、数据库设计

### 2.1 扩展 student_notifications 表

新增字段：
- category VARCHAR(32) 通知分类
- priority VARCHAR(16) 优先级
- action_url VARCHAR(512) 跳转链接
- extra_data JSON 扩展数据
- expires_at DATETIME 过期时间
- sent_at DATETIME 发送时间

### 2.2 新增 notification_preferences 表

学生通知偏好设置

字段：
- user_id
- enable_assignment_due
- enable_grade_published
- enable_course_update
- enable_project_review

### 2.3 新增 notification_templates 表

通知模板

字段：
- code 模板代码
- category 分类
- title_template 标题模板
- content_template 内容模板
- action_url_template 链接模板

## 三、通知类型设计

### 3.1 作业相关
- assignment_published: 新作业发布
- assignment_due_soon: 作业即将截止
- assignment_overdue: 作业已逾期
- assignment_graded: 作业已批改

### 3.2 成绩相关
- grade_published: 成绩已发布
- grade_changed: 成绩已修改

### 3.3 课程相关
- course_material_added: 新增学习资料
- course_lesson_published: 新增课时
- course_announcement: 课程公告

### 3.4 项目相关
- project_approved: 项目审核通过
- project_rejected: 项目审核拒绝

## 四、API 接口设计

### 4.1 发送通知
POST /api/notifications/send

### 4.2 批量发送通知
POST /api/notifications/send-batch

### 4.3 查询通知列表
GET /api/notifications

### 4.4 标记已读
POST /api/notifications/{id}/read
POST /api/notifications/read-all

### 4.5 通知偏好设置
GET /api/notifications/preferences
PUT /api/notifications/preferences

## 五、前端改动

### 5.1 通知中心页面
路由: /student/notifications

功能：
- 分类筛选
- 未读/已读标签
- 批量已读
- 跳转到相关页面

### 5.2 通知偏好设置
路由: /student/settings/notifications

### 5.3 顶部通知图标
- 显示未读数量
- 下拉显示最近通知

## 六、定时任务设计

### 6.1 作业截止提醒
每小时检查，提前24小时提醒

### 6.2 清理过期通知
每天凌晨2点清理30天前的已读通知

## 七、数据迁移

1. 扩展 student_notifications 表
2. 创建 notification_preferences 表
3. 创建 notification_templates 表
4. 插入默认模板

## 八、测试计划

单元测试：
- 发送单个通知
- 批量发送通知
- 模板变量替换
- 通知偏好过滤

集成测试：
- 定时任务触发通知
- 学生查看通知列表
- 标记已读
- 修改通知偏好

## 九、实施风险

中风险：
- 定时任务性能（分批发送）
- 通知模板维护

低风险：
- 新增表不影响现有功能

## 十、服务器部署

1. 备份数据库
2. 执行迁移
3. 配置定时任务
4. 重启后端
5. 构建前端

验证清单：
- 发送测试通知
- 学生查看通知
- 定时任务执行
- 通知偏好设置生效

## 十一、后续优化

1. 推送到微信公众号
2. 邮件通知
3. 短信通知
4. 通知统计
5. 通知分组

## 十二、实施记录（2026-07-09）

### 已落地内容
- 扩展 `student_notifications` 字段：分类、优先级、跳转链接、扩展数据、过期时间、发送时间。
- 新增 `notification_preferences` 与 `notification_templates` 模型及兼容建表逻辑。
- 通知服务支持学生偏好读取/更新、单条发送、批量发送、分类筛选、未读筛选、全部已读和模板渲染能力。
- 通知 API 新增/扩展：`GET /api/notifications?category=&unread_only=`、`POST /api/notifications/send`、`POST /api/notifications/send-batch`、`GET/PUT /api/notifications/preferences`、`POST /api/notifications/read-all`。
- 学生端消息入口升级为通知中心，合并展示作业通知与系统通知，支持分类筛选、只看未读、全部已读、跳转详情和通知偏好弹窗。
- 新增 `/student/notifications` 路由，与现有 `/inbox` 共用通知中心页面。
- 顶部未读数继续合并作业公告未读数与系统通知未读数。
- 顶部通知铃铛新增“最近通知”下拉层，展示最多 5 条未读系统通知、类别、时间和“查看全部”入口。
- 新增 `send_assignment_due_soon_reminders` 服务函数，可由外部定时器调用，按班级学生发送作业截止提醒，并尊重学生通知偏好和重复通知去重。
- 兼容层会幂等初始化作业截止、成绩发布、课程资料更新和作品驳回等默认通知模板；服务层支持模板变量替换。
- 新增 `cleanup_read_expired_notifications` 服务函数，可由外部定时任务清理已读且已过期通知，未读通知不会被误删。
- 通知列表和未读角标会主动排除已过期通知；未读但已过期的通知不会继续占用未读数，也不会在通知中心显示。
- 新增 `/student/settings/notifications` 通知偏好深链接，复用通知中心页面并自动打开偏好设置弹窗。
- 修复作业截止提醒用户可见文案乱码，并将前端“全部已读”返回类型与后端 `updated_count` 对齐。
- 补齐通知中心使用的 `ElSegmented` 与 `ElCheckbox` 全局注册，消除真实浏览器中的组件解析警告并恢复分类、未读筛选控件。
- 通知偏好弹窗增加视口宽度约束，分类分段控件在窄屏容器内支持横向滚动；390px 视口下页面不再产生横向溢出。

### 当前边界
- 第一版已提供作业截止提醒服务函数，但不内置后台定时调度进程；服务器若要自动执行，需额外配置定时任务或后续接入调度器。
- 默认模板初始化与渲染已落地；模板管理界面仍作为后续增强。
- 过期通知清理服务函数已落地，但服务器需配置外部定时任务后才会自动执行。

### 验证记录
- `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_030405_management_systems.py -q`：10 passed, 1 warning。
- `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_lessons_progress.py backend/tests/test_030405_management_systems.py -q`：22 passed, 1 warning。
- `node ./tests/notification-center-static.test.mjs`：通知中心静态检查通过。
- `node ./tests/vue-console-warning-static.test.mjs`：Element Plus 组件注册与控制台警告回归检查通过。
- `frontend` 下 `npm run build`：通过。
- 真实浏览器验收：`/student/settings/notifications` 可自动打开通知偏好弹窗，通知列表、分类分段控件、只看未读复选框和四类偏好开关正常渲染；偏好保存 `PUT /api/notifications/preferences` 返回 200，控制台 0 error / 0 warning。
- 响应式验收：1440px 与 390px 视口均无页面级横向溢出；390px 下弹窗宽 358px、左右各保留 16px 安全边距。

### 服务器部署影响
- 需要服务器拉取代码并重启后端，使兼容层补齐通知扩展字段、偏好表和模板表。
- 需要重新构建并部署前端静态资源，学生端通知中心和偏好入口才会生效。
- 若启用作业截止提醒和过期通知自动清理，还需要额外配置调度进程或服务器定时任务；本次不需要调整环境变量或 Nginx 配置。

## 十三、发送权限修正（2026-07-10）

### 最终语义

- 通知路由把当前教师或管理员身份传入服务层，权限判断不再只依赖“已登录角色”。
- 教师单发通知只能选择自己创建且未删除班级中的未删除学生；跨教师目标返回 403。
- 教师批量发送会过滤无权访问、已删除或偏好关闭的学生，并在 `skipped_count` 中返回跳过数量。
- 管理员可以通知任意未删除学生。
- 单发和批量通知的 `action_url` 只允许 `/` 开头且不能以 `//` 开头的站内路径，拒绝外部 URL。

### 验证记录

- `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_030405_management_systems.py -k "notification" -q`：4 passed, 1 warning。
- 后端全量测试：241 passed, 1 warning。

### 服务器部署影响

- 需要服务器拉取代码并重启后端。
- 本次权限修正不需要数据库迁移、环境变量或 Nginx 修改。
- 阶段 A 整体包含前端改密 Token 保存修复，需要重新构建并部署前端静态资源；部署前建议备份数据库。

## 十四、通知刷新与作品跳转修正（2026-07-11）

### 最终语义

- 通知中心把公告和系统通知加载集中到 `loadMessages()`；首屏并行加载消息与偏好，后台刷新不切换首屏加载态。
- 消息列表每 15 秒刷新一次，页面重新可见和跨组件消息事件会立即刷新；偏好设置不参与轮询，避免覆盖未保存的开关。
- 成功标记已读、全部已读和完成作业后广播刷新，页头未读数和通知中心保持一致。
- 页头最近通知必须先标记已读成功，再关闭下拉并跳转；失败时保留未读状态、不跳转，并显示中文错误提示。
- 作品审核通知统一跳转 `/create/project/{id}`；作品广场 `/create` 继续要求登录。

### 验证记录

- 消息刷新、通知中心、文案一致性、课程布局和首页品牌静态测试通过。
- 前端全部静态测试与生产构建通过，仅保留既有大 chunk 警告。

### 服务器部署影响

- 需要服务器拉取代码并重启后端，使作品通知新跳转地址生效。
- 需要重新构建并部署前端静态资源，使通知刷新和页头跳转修正生效。
- 不需要数据库迁移、环境变量或 Nginx 修改。
