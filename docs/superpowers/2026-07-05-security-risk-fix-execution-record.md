# 2026-07-05 安全风险按序修复执行记录

## 背景

本轮按 `docs/superpowers/2026-07-04-security-risk-fix-order.md` 执行，目标是优先关闭审查报告中的 P0 风险，再处理 P1 核心安全边界。用户要求删除临时修复分支并直接在 `main` 工作区修改；已删除 `codex/security-risk-fix-order` 分支，当前改动保留在 `main` 未提交工作区。

## 已完成修复

### P0-1 通用文件接口授权

- `/api/files/{file_id}` 当前通过文件专用可选鉴权解析用户。
- 匿名用户只能读取明确公开的白名单文件，例如已启用图文展示图片或公开课程资料预览封面。
- 登录用户读取 `StoredFile` 时按现有业务关系授权：
  - 管理员可读。
  - 上传者本人可读。
  - 资料文件复用 `can_view_course_materials()`，同一文件被多个资料引用时，只要任一资料对当前用户可见即可读取。
  - 作品报告、封面和图片按作者、已审核公开作品、教师审核范围授权。
  - 资料预览封面按资料课程权限授权。
- 本地文件读取前统一规范化 `object_key`，非法路径返回业务错误。
- 旧的“上传文件 URL 匿名直接打开”测试已改为新安全语义：默认匿名拒绝；显式允许 query token 时可用于浏览器预览和 Range 请求。

### P0-2 禁止公开教师注册

- 公开注册后端只允许 `student` 角色。
- 公开注册页移除教师选项，固定提交 `student`，注册成功后回到学生端首页。
- 新增前端静态测试防止教师注册入口回归。

### P0-3 教师密码重置审批范围

- 教师审批/驳回密码重置前，服务层校验申请人必须属于当前教师管理的班级。
- 管理员原有全局审批能力保持不变。
- 新增跨班级审批/驳回回归测试。

### P1-1 临时密码列表明文暴露

- 审批响应仍一次性返回临时密码，便于教师立即告知学生。
- 密码重置申请列表不再返回历史临时密码明文，`temp_password` 固定为空字符串。

### P1-2 本地文件路径边界

- `LocalStorageAdapter` 新增安全路径解析。
- `save_bytes()`、`open_write_stream()`、`open_stream()`、`exists()`、`delete()` 均拒绝解析到上传根目录外的路径。
- 新增目录穿越回归测试。

### P1-3 教师批量删除学生语义降级

- 教师端批量操作由“删除学生账号及所有关联数据”改为“从当前教师管理的班级中移出”。
- 学生账号、其他教师班级关系、其他课程数据不再被教师端批量操作删除。
- 前端教师学生管理页同步按钮、弹窗和 Toast 文案为“批量移出”。

## 验证记录

已通过：

```powershell
cd backend
py -m pytest tests/test_auth.py tests/test_material_file_acceleration.py tests/test_teacher_password_reset_scope.py tests/test_local_storage_boundaries.py tests/test_teacher_student_delete_scope.py -q
# 39 passed

py -m pytest tests/test_integration_bugfixes.py::TestTeacherRefactor::test_uploaded_pdf_requires_auth_but_supports_query_token_preview tests/test_integration_bugfixes.py::TestTeacherRefactor::test_uploaded_mp4_requires_auth_but_supports_query_token_range -q
# 2 passed

py -m pytest tests/ -q --ignore=tests/test_deploy_env_check.py
# 209 passed

py -m pytest tests/ -q --basetemp=.pytest-tmp
# 212 passed
```

```powershell
cd frontend
node tests/register-student-only-static.test.mjs
# register student only static checks passed

npm run build
# build passed
```

说明：
- 直接运行 `py -m pytest tests/ -q` 时，本机 `C:\Users\ASUS\AppData\Local\Temp\pytest-of-ASUS` 权限导致 `tmp_path` fixture setup 失败；改用项目内 `--basetemp=.pytest-tmp` 后完整后端测试 212 个通过。
- `npm run build` 仍有 Vite chunk 超过 500 kB 的体积警告，这是现有前端打包体积问题，不影响本轮构建通过。

## 服务器部署影响

需要服务器操作：
- 服务器需要拉取本轮代码。
- 需要重启后端 FastAPI 服务，使文件访问授权、教师密码重置范围和教师学生移出语义生效。
- 需要重新构建并部署前端静态资源，使公开注册页和教师学生管理页文案生效。

不需要服务器操作：
- 不需要执行数据库迁移。
- 不需要新增或修改环境变量。
- 不需要调整 Nginx alias。

注意事项：
- 生产环境中如果存在历史异常 `stored_files.object_key` 指向上传根目录外，本轮修复会拒绝读取这些记录，需要人工清点并修正数据。
- `/api/files/{file_id}` 默认不再允许匿名读取普通上传文件；公开学习资料文件仍应优先通过 `/api/public/learning/materials/{material_id}/file` 访问。

