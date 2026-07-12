# 审计日志系统设计

## 一、背景与目标

### 当前问题
- 无法追溯操作记录（谁修改了什么）
- 无法追查数据异常来源
- 缺少安全审计能力
- 合规性不足
- 敏感操作无二次确认

### 目标
1. 记录所有关键操作
2. 支持操作回溯查询
3. 支持审计日志导出
4. 敏感操作二次确认
5. 异常操作告警

## 二、数据库设计

### 2.1 新增 audit_logs 表

字段设计：
- id 主键
- user_id 操作人
- user_role 操作人角色
- action 操作类型
- resource_type 资源类型
- resource_id 资源ID
- resource_name 资源名称
- details JSON 操作详情
- ip_address IP地址
- user_agent 浏览器信息
- status 操作状态（success/failed）
- error_message 错误信息
- created_at 操作时间

索引：
- ix_audit_logs_user_id
- ix_audit_logs_action
- ix_audit_logs_resource_type
- ix_audit_logs_created_at

### 2.2 操作类型定义

用户管理：
- user.create 创建用户
- user.update 修改用户
- user.delete 删除用户
- user.password_reset 重置密码

课程管理：
- course.create 创建课程
- course.update 修改课程
- course.delete 删除课程
- course.publish 发布课程

班级管理：
- class.create 创建班级
- class.update 修改班级
- class.delete 删除班级
- class.import_students 导入学生

作业管理：
- assignment.create 创建作业
- assignment.update 修改作业
- assignment.delete 删除作业
- assignment.grade 批改作业

成绩管理：
- grade.update 修改成绩
- grade.export 导出成绩
- grade.return 返还成绩

项目管理：
- project.approve 审核通过
- project.reject 审核拒绝
- project.delete 删除项目

系统管理：
- system.backup 数据库备份
- system.restore 数据库恢复
- system.config_update 配置修改

## 三、日志记录设计

### 3.1 拦截器实现

FastAPI 中间件自动记录：

```python
@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    # 获取当前用户
    user = get_current_user_from_request(request)
    
    # 记录开始时间
    start_time = time.time()
    
    # 执行请求
    response = await call_next(request)
    
    # 判断是否需要审计
    if should_audit(request.method, request.url.path):
        log_audit(
            user_id=user.id if user else None,
            action=extract_action(request),
            resource_type=extract_resource_type(request),
            resource_id=extract_resource_id(request),
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            status="success" if response.status_code < 400 else "failed"
        )
    
    return response
```

### 3.2 手动记录关键操作

对于重要操作显式记录：

```python
def delete_course(db: Session, course_id: int, operator_id: str):
    course = db.query(Course).get(course_id)
    
    # 记录审计日志
    audit_log = AuditLog(
        user_id=operator_id,
        action="course.delete",
        resource_type="course",
        resource_id=course_id,
        resource_name=course.name,
        details={
            "course_name": course.name,
            "class_count": len(course.classes),
            "material_count": len(course.materials)
        },
        ip_address=get_client_ip(),
        status="success"
    )
    db.add(audit_log)
    
    # 执行删除
    soft_delete(db, course, operator_id)
    db.commit()
```

## 四、API 接口设计

### 4.1 查询审计日志
GET /api/admin/audit-logs

参数：
- user_id 操作人
- action 操作类型
- resource_type 资源类型
- start_date 开始日期
- end_date 结束日期
- page 页码
- page_size 每页数量

### 4.2 导出审计日志
GET /api/admin/audit-logs/export

响应：Excel 文件

### 4.3 查询用户操作历史
GET /api/admin/users/{user_id}/audit-logs

### 4.4 查询资源操作历史
GET /api/admin/resources/{resource_type}/{resource_id}/audit-logs

## 五、前端改动

### 5.1 管理员审计日志页面
路由: /admin/audit-logs

功能：
- 时间范围筛选
- 操作类型筛选
- 用户筛选
- 资源类型筛选
- 导出Excel

### 5.2 资源操作历史
在课程/班级/用户详情页增加"操作历史"标签

显示：
- 操作时间
- 操作人
- 操作类型
- 操作详情

### 5.3 敏感操作二次确认
删除课程/班级/用户时弹窗：
- 输入验证码
- 填写删除原因
- 确认按钮

## 六、敏感操作定义

需要二次确认的操作：
- 删除课程（影响多个班级）
- 删除班级（影响多个学生）
- 删除用户（影响历史数据）
- 修改成绩（已发布的成绩）
- 导出学生数据（隐私敏感）

二次确认机制：
1. 弹窗显示影响范围
2. 要求输入操作原因
3. 高危操作要求输入验证码
4. 记录到审计日志

## 七、数据迁移

```python
def upgrade():
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.String(32), nullable=True),
        sa.Column('user_role', sa.String(16), nullable=True),
        sa.Column('action', sa.String(64), nullable=False),
        sa.Column('resource_type', sa.String(32), nullable=True),
        sa.Column('resource_id', sa.Integer(), nullable=True),
        sa.Column('resource_name', sa.String(256), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(64), nullable=True),
        sa.Column('user_agent', sa.String(512), nullable=True),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('error_message', sa.String(512), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL')
    )
    
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_resource_type', 'audit_logs', ['resource_type'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])

def downgrade():
    op.drop_table('audit_logs')
```

## 八、测试计划

单元测试：
- 创建审计日志
- 查询审计日志（各种过滤条件）
- 导出审计日志

集成测试：
- 中间件自动记录
- 敏感操作二次确认
- 操作失败记录

## 九、实施风险

### 中风险
1. 日志量大：高频操作产生大量日志
   - 缓解：只记录关键操作
   - 缓解：定期归档（保留1年）

2. 性能影响：每次操作都写日志
   - 缓解：异步写入
   - 缓解：批量写入

### 低风险
- 新增表不影响现有功能

## 十、服务器部署

1. 备份数据库
2. 执行迁移
3. 重启后端
4. 构建前端

验证清单：
- 执行测试操作，检查日志记录
- 查询审计日志列表
- 导出审计日志Excel
- 敏感操作二次确认生效

## 十一、数据保留策略

### 日志保留期限
- 普通操作日志：保留1年
- 敏感操作日志：保留3年
- 系统级操作日志：永久保留

### 自动归档
每月1号归档上月日志到独立表：
- audit_logs_archive_202607
- audit_logs_archive_202608

### 定期清理
每年1月1号清理3年前的普通操作日志

## 十二、后续优化

1. 实时监控面板（今日操作统计）
2. 异常操作告警（短时间大量删除）
3. 操作回放（查看修改前后对比）
4. 审计报告生成（月度/年度）
5. 日志加密存储（敏感字段）

## 十三、实施记录（2026-07-09）

### 已落地内容
- 新增 `AuditLog` ORM 模型与 `audit_logs` 兼容建表逻辑，字段覆盖操作人、角色、动作、资源类型、资源 ID、资源名称、详情、状态、错误信息和操作时间。
- `resource_id` 已按字符串存储，支持数字 ID、学号、工号等非数字资源标识；兼容层对 MySQL 既有表尝试将该列调整为 `VARCHAR(64)`。
- 新增 `audit_service.py`，支持创建审计日志、分页查询、按用户/动作/资源类型/资源 ID/状态/时间范围过滤，以及按筛选条件导出 Excel。
- 管理员 API 新增/扩展：`GET /api/admin/audit-logs`、`GET /api/admin/audit-logs/export`、`GET /api/admin/users/{user_id}/audit-logs`、`GET /api/admin/resources/{resource_type}/{resource_id}/audit-logs`。
- 审计日志导出会额外写入 `audit_log.export` 审计记录，记录导出条数和筛选条件。
- 日期参数格式错误时返回业务错误 `400 日期格式错误`，避免 500。
- 软删除、恢复、彻底删除会记录对应审计动作；课程删除链路已验证可产生 `course.delete` 日志。
- 管理员端新增“审计日志”页面，支持操作人、动作、资源类型、资源 ID、状态、时间范围筛选，并可按当前筛选条件导出 Excel。
- 教师账号创建、删除、密码重置与密码重置审批/驳回等敏感账号操作已接入审计日志。
- `AuditLogQuery` Schema 已与实际接口筛选能力对齐，补充资源 ID 和成功/失败状态字段；管理员页面眉题统一为中文。
- 管理员审计页支持通过 URL 查询参数直接查看指定资源操作历史；数据回收站为七类资源提供“操作历史”入口并自动带入资源类型与资源 ID。

### 当前边界
- 第一版采用关键操作显式记录，不启用全局 FastAPI 中间件，避免误记录和性能风险。
- 异常操作实时告警、日志归档、审计报表和更多业务敏感操作的细粒度接入作为后续增强。

### 验证记录
- `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_030405_management_systems.py -q`：10 passed, 1 warning。
- `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_lessons_progress.py backend/tests/test_030405_management_systems.py -q`：22 passed, 1 warning。
- `node ./tests/admin-audit-logs-static.test.mjs`：管理员审计日志静态检查通过。
- `frontend` 下 `npm run build`：通过。
- 真实浏览器验收：管理员从回收站点击“操作历史”后跳转到 `/admin/audit-logs?resource_type=courses&resource_id=2`，资源类型和资源 ID 自动回填，`GET /api/admin/audit-logs?resource_type=courses&resource_id=2` 返回 200 且只展示对应 `course.delete` 记录；1440px 视口无横向溢出，控制台 0 error / 0 warning。

### 服务器部署影响
- 需要服务器拉取代码并重启后端，使兼容层创建 `audit_logs` 表并补齐/调整 `resource_id` 字段类型。
- 需要重新构建并部署前端静态资源，管理员端“审计日志”筛选和导出能力才会生效。
- 建议部署前备份数据库；如服务器采用正式迁移流程，应补 Alembic 迁移后执行。
- 不需要修改环境变量或 Nginx 配置。
