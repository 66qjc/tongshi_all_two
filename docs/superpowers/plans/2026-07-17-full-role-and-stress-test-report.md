# 2026-07-17 全角色功能与压力极限测试报告

## 状态

- 执行状态：本轮已完成可复现范围内的测试与汇总
- 执行日期：2026-07-17
- 测试对象：当前工作区代码（含并行整改未提交改动，本轮不修改业务代码）
- 测试原则：只测只记，不修业务；隔离 SQLite + 临时上传目录；仅本机 `127.0.0.1`
- 并行任务排除：`019f6f8c-b738-7671-9f13-6dd1b18e8e2f` 负责的题库导入/贡献日志、公共课阶段资料删除、`Settings` 隔离、MySQL cleanup 脚本等，本轮不重复验收

## 一、环境

| 项 | 值 |
| --- | --- |
| 后端 | `http://127.0.0.1:8051`，`C:/tmp/tongshi_e2e_server.py` 启动 |
| 前端 | `http://127.0.0.1:5173`，Vite dev，代理到 8051 |
| 数据库 | 全新 SQLite：`output/e2e/tongshi-e2e-*.sqlite` |
| 上传目录 | `output/e2e/tongshi-e2e-uploads-*` |
| 账号 | 学生 `2025001/abc123`、未选课学生 `2025002/abc123`、教师 `T001/abc123`、其他教师 `T002/abc123`、管理员 `admin/Admin#2026` |
| 预置数据 | 私有课/公开课/越权课、201 名班级学生、502+ 题、作业、作品、通知、公开活动 |

证据目录：

- API：`output/e2e/api-probe.json`
- 浏览器：`output/e2e/browser-role-flows.parsed.json`、`output/e2e/browser-correct-routes.parsed.json`
- 压力：`output/e2e/stress-results.jsonl`
- 后端测试：`output/e2e/backend-tests.out.log`
- 前端：`output/e2e/frontend-static.out.log`、`frontend-typecheck.out.log`、`frontend-build.out.log`

## 二、四身份结论摘要

### 2.1 游客

| 项 | 结论 |
| --- | --- |
| 首页/公开教程/公开课阅读/活动/关于/隐私/联系 | 通过 |
| `/practice` `/create` `/teacher` `/admin/*` | 跳转登录，通过 |
| 未授权 API（课程/题库/教师/管理） | 统一 `401 无效的认证凭据`，通过 |
| 公开 API | `/api/public/learning/*`、`/api/showcase` 可访问，通过 |

### 2.2 学生

| 项 | 结论 |
| --- | --- |
| 登录、学/思/践、作品、成长档案、消息、通知、改密 | 页面可打开，中文正常 |
| 自由练习 | 提交前不显示正确答案；答错后显示解析，通过 |
| 作业练习 | 可答题并推进，任务可完成，通过 |
| 未加入私有课 API | `/api/courses/2` 返回 404，后端通过 |
| 未加入私有课页面 | **失败/体验缺陷**：页面落到“本教程暂无学习资料”，未明确拒绝访问 |
| 错角色 `/teacher` `/admin` | 回首页，通过 |
| 移动端课程页 | 无横向溢出，通过 |

### 2.3 教师

| 项 | 结论 |
| --- | --- |
| 正确路由工作台/课程/班级/发布/成绩/任务/审核/学生/题库/点名 | 全部可打开 |
| 已退役 `/teacher/materials` | 404，符合预期 |
| 数据隔离：他人课程/班级学生列表 | 404 或空，主体通过 |
| 导出他人 `class_id` | **文件名泄漏他人班级名**（见缺陷 P1） |
| 对公开课创建班级 | **可创建**；后续发作业失败，形成脏数据（见缺陷 P1） |
| 作品审核、新增题目、完成报告 | API 通过 |

### 2.4 管理员

| 项 | 结论 |
| --- | --- |
| 教师/公共课/共享题库/内容/密码重置/回收站/审计 | 正确路由均可打开 |
| 教师/学生访问管理 API | `403 需要admin权限`，通过 |
| 旧错误路径 `/admin/content` 等 | 404；真实路径为 `/admin/showcase`、`/admin/password-reset` |

## 三、缺陷清单（本轮不修复）

### P1-1 教师可在公开课上建班，但无法在其上发作业

- **现象**：`POST /api/classes` 对公开课 `course_id=3` 返回成功，班级进入教师班级列表；`POST /api/announcements` 带 `course_id=3` 返回 `404 课程不存在`。
- **影响**：可产生“公开课空班级”脏数据，作业闭环断裂。
- **证据**：`output/e2e/api-probe.json` 中 `teacher_create_class_on_public` / `assignment_on_public_class`；代码 `class_service.create_class` 用“自有课或公开课”可访问规则，公告创建对课程归属更严。
- **建议方向**：要么禁止教师在公开课建班，要么允许并贯通作业发布与权限模型，二者必须一致。

### P1-2 跨教师导出文件名泄漏班级名

- **现象**：`T001` 请求 `/api/teacher/students/export?class_id=2` 时，Excel 内容为空（数据隔离有效），但 `Content-Disposition` 文件名为 `学生成绩_其他教师班级_....xlsx`。
- **影响**：信息泄漏（他人班级命名），且对调用方造成“似乎导出了对方班级”的误导。
- **证据**：API probe export_probe；`teacher_routes.export_students_excel` 在 `class_id` 存在时直接 `db.query(Class).filter(Class.id == class_id)` 取名，未校验 `created_by`。
- **建议方向**：文件名只允许使用已通过归属校验的班级；无权限时直接业务错误，不要用全局 Class 查询填文件名。

### P1-3 学生访问未授权课程详情页体验错误

- **现象**：后端对未加入私有课正确 404；前端 `CourseDetailView` 认证失败后回退公开课接口，公开也失败后仍可能呈现“暂无学习资料”空态，而非明确无权限。
- **影响**：权限失败被伪装成内容为空，验收和用户理解成本高。
- **证据**：浏览器 `/learn/course/2` 文本；`CourseDetailView.loadData` 的 catch 回退逻辑。

### P2-1 部分“学生业务”接口缺少显式 student 角色门禁

- **现象**：教师/管理员调用以下接口 `code=0` 成功：
  - `GET /api/portfolio`
  - `GET /api/projects/mine`
  - `POST /api/projects/{id}/like`
- **对照**：`/api/quiz/*`、`/api/notifications`、任务 complete/questions 正确要求 student。
- **影响**：角色边界不一致；非学生可点赞、读成长档案结构，扩大攻击面与语义混乱。
- **证据**：`candidate_bugs.student_endpoint_roles`；`project_routes`/`portfolio_routes` 仅 `get_current_user`。

### P2-2 随机抽题在较高并发下成为明显瓶颈

- **现象**：`GET /api/quiz/questions?random=20`：
  - L1：20 并发 200 次，成功率 100%，P95 ≈ 1.70s，RPS ≈ 19.7
  - L2：50 并发 300 次，成功率 12.7%，Timeout 262，P95 ≈ 20.4s
- **影响**：练习首页/自由练习在并发升高时易超时；本地 SQLite 会放大，但代码路径本身偏重。
- **说明**：因 L2 错误率 >5%，原计划的 L3 并发提交/点赞阶段按客户端保护逻辑未继续加压。

### P3 / 未证实

- **公开展示洗白私有文件**：本轮种子只有 link 资料，未复现文件链洗白；保留为待专用文件夹具复测项。
- **教师导出数据越权**：未证实。他人 `class_id` 导出内容为空。
- **管理员/教师前端错误旧路径**：测试脚本曾用错路径导致 404，不等于产品导航坏；正确路由已通过。

## 四、自动化与构建

| 项 | 结果 |
| --- | --- |
| 后端 pytest | **460 passed**，**9 errors** |
| 9 errors 原因 | Windows `PermissionError: C:\Users\ASUS\AppData\Local\Temp\pytest-of-ASUS`，属本机临时目录权限环境问题，不是断言失败 |
| 前端静态 `node --test tests/*.mjs` | **44/44 通过** |
| `vue-tsc --build` | 通过 |
| `vite build` | 通过（仅有 >500kB chunk 警告） |

## 五、压力测试明细（本机 SQLite，不可当作生产 MySQL 容量）

| 阶段 | 请求/并发 | 成功 | 错误率 | RPS | avg/P95 ms |
| --- | --- | --- | --- | --- | --- |
| L0-health | 100/10 | 100 | 0% | 353 | 27 / 47 |
| L1-public-courses | 300/20 | 300 | 0% | 212 | 91 / 108 |
| L1-login-bcrypt | 40/5 | 40 | 0% | 115 | 41 / 52 |
| L1-quiz-random-20 | 200/20 | 200 | 0% | 20 | 999 / 1700 |
| L1-teacher-students | 200/20 | 200 | 0% | 55 | 354 / 525 |
| L3-invalid-random=201 | 100/20 | 100 | 0% | 337 | 56 / 76（正确 422） |
| L2-health | 1000/50 | 1000 | 0% | 788 | 62 / 73 |
| L2-public-courses | 500/50 | 500 | 0% | 314 | 151 / 169 |
| L2-quiz-random-20 | 300/50 | 38 | **87.3%** | 3.1 | 15698 / 20432 |

## 六、未覆盖 / 受阻项

1. 并行整改四条浏览器流程：由另一会话负责，本轮只吸收其后续结论，不重复写同一批代码。
2. 真实 MySQL / `MYSQL_VERIFY_*`：当前未配置，未跑 cleanup 外键矩阵。
3. 大文件上传 1GB、同步预览、Nginx X-Accel、多 worker + Redis 限流：仅代码与已有单测边界核对，未做生产级压测。
4. 注册/忘记密码完整 UI 表单、密保、密码重置审批端到端：API 与页面可达性覆盖为主，未做完整邮件/人工审批闭环。
5. 公开展示私有文件链：缺专用私有 file 夹具，未证实。
6. L3 并发提交/点赞：因 L2 抽题失败率触发停止条件，未继续。

## 七、服务器部署影响

本轮仅新增/更新测试计划与报告，并在本地隔离环境执行测试，**不需要服务器修改**（无需拉代码、重启、重建前端、迁移库或改环境变量）。

若后续按本报告缺陷修复，需在对应整改记录中重新说明部署影响。

## 八、建议的下一步（仍不在本轮实施）

1. 先修 P1-1/P1-2/P1-3：公开课建班策略统一、导出文件名归属校验、课程详情无权限态。
2. 再收 P2-1 角色门禁一致性，以及抽题查询/缓存优化评估。
3. 环境修好 Windows pytest 临时目录权限后，重跑全量后端测试确认 0 error。
4. 专用验证库可用后，补真实 MySQL 与文件链专项。
