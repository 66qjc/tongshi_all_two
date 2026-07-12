# 作业评分系统设计

## 一、背景与目标

### 当前问题
- TaskCompletion 表只有完成标记，无分数字段
- QuizAttempt 表只有对错，无得分记录
- Announcement 表缺少评分配置
- 教师无法给主观题打分，无法导出成绩单

### 目标
1. 支持客观题自动评分
2. 支持主观题手动评分
3. 支持混合模式
4. 支持教师批改反馈
5. 支持成绩导出

## 二、数据库设计

### 2.1 扩展 announcements 表

新增字段：
- max_score FLOAT 满分
- pass_score FLOAT 及格分
- grading_mode VARCHAR(16) 评分模式
- question_scores JSON 题目分值
- allow_file_upload BOOLEAN 允许上传附件
- max_file_count INT 最多文件数
- require_submission_content BOOLEAN 必须填写答案

### 2.2 扩展 task_completions 表

新增字段：
- score FLOAT 最终得分
- max_score FLOAT 满分
- auto_score FLOAT 自动评分
- manual_score FLOAT 手动评分
- status VARCHAR(16) 状态
- submission_content TEXT 答案内容
- submission_file_ids JSON 附件列表
- teacher_comment TEXT 教师评语
- graded_by VARCHAR(32) 批改教师
- graded_at DATETIME 批改时间
- returned_at DATETIME 返还时间

重命名：completed_at -> submitted_at

新增索引：
- ix_task_completion_status
- ix_task_completion_graded_by

## 三、API 接口设计

### 3.1 学生提交作业
POST /api/assignments/{announcement_id}/submit

### 3.2 教师批改作业
POST /api/assignments/{announcement_id}/grade

### 3.3 批量返还成绩
POST /api/assignments/{announcement_id}/return

### 3.4 导出成绩单
GET /api/classes/{class_id}/grades/export

## 四、前端改动

### 4.1 教师端批改页面
路由: /teacher/assignments/{id}/grading
组件: TeacherAssignmentGrading.vue

### 4.2 学生端成绩查看
路由: /student/assignments/{id}/result

## 五、数据迁移

Alembic迁移脚本：
1. 扩展announcements表
2. 扩展task_completions表
3. 重命名completed_at字段
4. 添加索引

## 六、测试计划

单元测试：
- 纯客观题自动评分
- 纯主观题手动评分
- 混合模式评分
- 成绩导出Excel

## 七、实施风险

高风险：
- 字段重命名影响现有代码
- 状态字段改变查询逻辑

中风险：
- JSON字段查询性能

## 八、服务器部署

部署步骤：
1. 备份数据库
2. 拉取代码
3. 执行迁移
4. 重启后端
5. 构建前端

验证清单：
- 创建测试作业
- 学生提交
- 教师批改
- 导出成绩单

回滚方案：
- git reset
- alembic downgrade

## 九、后续优化

1. 批量批改
2. 评语模板
3. 成绩统计图表
4. 成绩申诉
5. 分段评分

## 十、正确性修正记录（2026-07-10）

### 最终语义

- `QuizAttempt` 是答题事实来源；单题提交先 `flush`，评分更新和完成记录在同一事务中一次提交。
- 只有作业配置的全部题目均已有答题记录时，才创建或更新 `TaskCompletion`；部分答题只保存答题记录和阶段得分，不标记完成。
- `mark_completed()` 即使已经存在完成记录，也必须先校验时间窗口和题目完整性，不能通过历史记录绕过校验。
- 并发提交最后一题时，完成记录唯一键冲突通过保存点恢复，答题记录不随冲突回滚，最终只保留一条完成记录。
- SQL 写入异常统一回滚并返回中文业务错误，不向前端暴露数据库异常。

### 验证记录

- `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_assignment_practice_flow.py backend/tests/test_assignment_scoring.py -q`：15 passed, 1 warning。
- `backend\.venv\Scripts\python.exe -m pytest backend/tests -q --basetemp=tmp/pytest-phase-a-full`：241 passed, 1 warning。

### 服务器部署影响

- 需要服务器拉取代码并重启后端服务。
- 本次正确性修正不新增数据库字段，不需要数据库迁移、环境变量或 Nginx 修改。
- 本轮阶段 A 同时包含前端 Token 保存修复，因此整体上线仍需要重新构建并部署前端静态资源；部署前建议备份数据库。
