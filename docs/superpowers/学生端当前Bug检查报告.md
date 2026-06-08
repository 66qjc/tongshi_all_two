# 学生端当前 Bug 检查报告

检查时间：2026-06-06

本次只检查并记录问题，未修改业务代码。检查范围包括学生端页面、前端 API 封装、对应后端路由与服务层：

- 学生端页面：`frontend/src/views/LearnView.vue`、`CourseDetailView.vue`、`PracticeView.vue`、`PracticeQuizView.vue`、`InboxView.vue`、`CreateView.vue`、`ProjectDetailView.vue`、`ProjectUploadView.vue`、`ProfileView.vue`
- 通用组件：`frontend/src/components/AppHeader.vue`、`frontend/src/components/AnnouncementPopup.vue`
- 前端 API：`frontend/src/api/course.ts`、`question.ts`、`quiz.ts`、`announcement.ts`、`project.ts`、`profile.ts`
- 后端接口和服务：`backend/app/api/v1/routes/course_routes.py`、`question_routes.py`、`quiz_routes.py`、`announcement_routes.py`、`project_routes.py`、`profile_routes.py`，以及对应 service 文件

已验证：

- `frontend` 下执行 `npm run type-check`：通过
- `frontend` 下执行 `npm run build-only`：通过

说明：检查过程中 PowerShell 直接输出中文时出现乱码，但用 UTF-8 读取验证后确认源码文本本身正常，这不是学生端页面文案 bug。

## 高优先级 Bug

### 1. 学生可直接访问未加入课程的详情统计

严重程度：高

影响范围：课程详情接口、学生端课程详情页

复现路径：

1. 使用学生账号登录。
2. 直接访问一个自己未加入班级对应的课程详情地址，例如 `/learn/course/{其他课程ID}`。
3. 前端会调用 `/api/courses/{course_id}`。
4. 后端当前可能返回课程名称、资料数量、题目数量、班级数量等统计信息。

证据：

- `frontend/src/views/CourseDetailView.vue:22` 调用 `getCourseDetail(courseId.value)`。
- `frontend/src/api/course.ts:40` 请求 `/courses/{id}`。
- `backend/app/api/v1/routes/course_routes.py:76-80` 对学生访问课程详情时没有做班级归属校验；只有教师角色会传入 `teacher_id` 过滤。
- 同项目中题目和资料接口已经做了学生归属校验，可对照 `question_service.can_view_course_questions` 和 `material_service.can_view_course_materials`。

根因：

课程详情接口复用了教师端课程详情查询逻辑。学生角色下 `teacher_id` 为 `None`，`get_course_detail` 只按课程 ID 查询，缺少“学生必须加入该课程班级”的权限边界。

建议：

- 增加课程详情学生权限校验，规则与课程资料、课程题目接口保持一致。
- 补充后端测试：学生不能访问未加入课程详情；已加入课程可正常访问。

### 2. 任务可在未答题、未开始时手动标记完成

严重程度：高

影响范围：收件箱任务、教师端任务完成统计

复现路径：

1. 教师发布一个带开始时间和题目的任务。
2. 学生进入 `/inbox`，点击任务卡片使其变为已读。
3. 在任务未开始或未完成题目前，点击“标记完成”。
4. 当前前端只拦截已截止任务，后端也只校验截止时间；学生可以生成完成记录。

证据：

- `frontend/src/views/InboxView.vue:30-39` 的 `handleComplete` 只检查 `isExpired(item)`，未检查 `isNotStarted(item)`，也不检查答题进度。
- `frontend/src/views/InboxView.vue:136-144` 已读后展示“标记完成”按钮，显示条件只排除已截止任务。
- `backend/app/services/task_service.py:47-65` 的 `mark_completed` 只校验任务存在、学生可访问、是否过截止时间，然后直接写入 `TaskCompletion`。
- `TaskCompletion` 表只记录 `announcement_id + user_id`，没有和答题结果建立完成约束。

根因：

任务完成逻辑是独立的手动按钮，未绑定公告的 `question_ids`、开始时间、学生实际答题记录。

建议：

- 前端：未开始任务禁用完成按钮，按钮文案明确状态。
- 后端：`mark_completed` 校验 `start_time`，并校验公告 `question_ids` 中每道题至少有当前学生的有效答题记录。
- 更稳妥的方案：完成状态由后端根据答题记录自动计算，减少手动标记入口。

### 3. 通知任务的“去练习”没有进入指定题目集

严重程度：高

影响范围：收件箱、练习页、教师发布题目任务

复现路径：

1. 教师向班级发布一个只包含部分题目的任务。
2. 学生在 `/inbox` 点击该任务的“去练习”。
3. 页面只跳转到 `/practice`，学生需要再选择课程。
4. 进入课程练习后，练习页加载该课程全部题目，而不是公告指定的 `question_ids`。

证据：

- `frontend/src/views/InboxView.vue:119-125` 展示题目数量，但跳转目标固定为 `/practice`。
- `frontend/src/views/PracticeView.vue:69` 从课程卡进入 `/practice/quiz/${course.id}`。
- `frontend/src/views/PracticeQuizView.vue:10-18` 只读取 `courseId`，调用 `getCourseQuestions(courseId.value)`。
- `frontend/src/api/question.ts:39-41` 课程练习接口只按课程取题，没有公告 ID 或题目 ID 过滤参数。
- 后端公告数据包含 `course_id` 和 `question_ids`，见 `backend/app/services/announcement_service.py:38-56`。

根因：

发布任务和在线练习是两套松散流程。公告保存了指定题目，但学生练习页没有任务上下文，也没有按公告题目集加载题目的接口。

建议：

- 为任务练习增加路由，例如 `/practice/announcement/:announcementId`。
- 后端增加“按公告获取练习题”接口，统一校验班级归属、开始时间、截止时间。
- 任务完成统计应基于该公告题目集的答题记录。

### 4. 任务成绩会因重复答题超过 100 分

严重程度：高

影响范围：教师任务完成报告、学生练习记录

复现路径：

1. 学生完成某课程练习。
2. 重新进入同一课程练习，再次提交同一道题的正确答案。
3. 后端每次提交都会新增一条 `QuizAttempt`。
4. 教师查看任务完成报告时，正确次数按答题记录累计，而不是按题目去重，成绩可能超过 100 分。

证据：

- `frontend/src/views/PracticeQuizView.vue:87-95` 每次提交都会调用 `submitAnswer`，当前练习完成后会清理草稿，学生可重新进入再次提交。
- `backend/app/services/quiz_service.py:35-42` 每次提交都新增 `QuizAttempt`，没有按用户和题目去重。
- `backend/app/models/entities.py:116-125` 的 `quiz_attempts` 没有 `user_id + question_id` 唯一约束。
- `backend/app/services/task_service.py:121-133` 任务报告按所有正确答题记录累加 `score_counts[user_id] += 1`，没有按 `question_id` 去重，也没有取最新一次答题。

根因：

答题记录是历史流水，但任务成绩把流水当成题目完成情况统计。重复正确记录会被重复计分。

建议：

- 任务报告统计时按 `user_id + question_id` 去重，优先取每题最新一次答题结果。
- 补充测试：同一学生同一任务题目重复答对多次，任务分数仍不超过 100。

## 中优先级 Bug

### 5. 无班级学生看不到后端返回的明确提示

严重程度：中

影响范围：学习页、练习页

复现路径：

1. 使用未加入任何班级的学生账号登录。
2. 打开 `/learn`。
3. 后端会返回 `{"courses": [], "hint": "你尚未加入任何班级，请联系老师"}`。
4. 前端 API 封装丢弃 `hint`，页面只展示通用空状态。

证据：

- `backend/app/services/course_response_service.py:38-41` 未加入班级时返回明确 `hint`。
- `frontend/src/api/course.ts:22-28` 如果返回对象，只取 `data.courses`，丢弃 `data.hint`。
- `frontend/src/views/LearnView.vue:54` 只能展示“暂无课程内容”或搜索无结果。
- `frontend/src/views/PracticeView.vue` 同样调用 `getCourses()`，也无法显示后端提示。

根因：

前端为了兼容数组响应，把课程列表接口统一转换为 `Course[]`，没有保留学生端需要的状态提示。

建议：

- 新增学生端专用课程列表返回类型，保留 `hint`。
- 学习页和练习页根据 `hint` 展示“请联系老师加入班级/班级尚未分配课程”等明确提示。

### 6. 被驳回作品重新提交会错配或丢失已有图片 file_id

严重程度：中

影响范围：作品重提交流程、作品图片元数据

复现路径：

1. 学生提交带多张图片的作品。
2. 教师驳回。
3. 学生进入重新提交页面，保留已有图片并新增图片。
4. 前端提交 `image_urls` 为“已有图片 + 新图片”，但 `image_file_ids` 只包含新上传图片的 file_id。
5. 后端按数组下标把 file_id 绑定到图片，导致已有图片可能绑定新图片的 file_id，新图片反而没有 file_id。

证据：

- `frontend/src/views/ProjectUploadView.vue:113` 编辑模式只保存已有图片的 `image_url`。
- `frontend/src/views/ProjectUploadView.vue:136-160` `uploadedImageUrls` 包含已有图片和新图片，但 `uploadedImageFileIds` 只收集新上传图片。
- `backend/app/services/project_service.py:23-30` `sync_project_images` 按 `image_urls` 下标读取 `image_file_ids[index]`。
- `backend/app/services/project_service.py:116-117` 重新提交时会清空并重建图片列表。

根因：

前端没有保留已有图片的 `file_id`，后端又假设 `image_urls` 和 `image_file_ids` 一一按下标对齐。

建议：

- 前端保存已有图片的完整对象 `{ image_url, file_id }`。
- 提交时传递完整图片列表，或后端根据 URL 和已有图片记录合并 file_id。
- 增加测试：保留旧图并新增新图后，每张图片 file_id 仍对应正确文件。

### 7. 作品重新提交页面已有图片在分离部署下可能无法预览

严重程度：中

影响范围：作品重提交流程、生产部署

复现路径：

1. 前端和后端分离部署，后端地址通过 `VITE_API_BASE` 配置。
2. 学生编辑被驳回作品。
3. 页面渲染已有图片缩略图时直接使用原始 URL。
4. 如果前端域名没有代理 `/api` 或 `/uploads`，已有图片预览失败。

证据：

- `frontend/src/views/ProjectUploadView.vue:288-289` 已有图片 `<img :src="url">` 直接使用原始 URL。
- 其他展示页通常使用 `resolveFileUrl`，例如 `ProjectDetailView.vue` 和 `CreateView.vue`。
- `frontend/src/utils/url.ts` 已封装生产环境 `VITE_API_BASE` 拼接逻辑。

根因：

重提交表单的已有图片预览没有复用统一 URL 解析函数。

建议：

- 编辑页已有图片预览统一使用 `resolveFileUrl(url)`。
- 如果使用 file_id，优先构造 `/api/files/{file_id}` 并交给 `resolveFileUrl` 处理。

### 8. 错题本无法正确标记多选题选项状态

严重程度：中

影响范围：个人中心错题本

复现路径：

1. 学生答错一道多选题，例如正确答案为 `AB`，学生答案为 `AC`。
2. 打开个人中心的错题本。
3. 前端逐个选项用单个字母与整串答案比较，无法正确高亮 A、B、C 的正确/错误关系。

证据：

- `backend/app/services/quiz_service.py:179-186` 错题本返回 `answer` 和 `user_answer`，但没有返回题型。
- `frontend/src/views/ProfileView.vue:261-262` 使用 `String.fromCharCode(65 + i) === q.answer` 和 `=== q.user_answer`，只适用于单选题。
- `frontend/src/api/profile.ts:3-12` `WrongQuestion` 类型也缺少 `type`。

根因：

错题本前端按单选题逻辑展示所有题型，后端响应也缺少题型字段，无法区分单选、多选、填空。

建议：

- 错题本接口返回 `type`。
- 前端根据题型分别处理单选、多选、填空；多选题用 `answer.includes(label)` 和 `user_answer.includes(label)`。

## 低优先级 Bug

### 9. 顶部未读消息角标不会随已读操作刷新

严重程度：低

影响范围：顶部导航、消息通知体验

复现路径：

1. 学生登录后顶部通知角标显示未读数。
2. 进入 `/inbox` 点击未读消息，消息被标记已读。
3. 留在单页应用内时，顶部角标仍保持旧数字，直到刷新页面或重新挂载组件。

证据：

- `frontend/src/components/AppHeader.vue:15-20` 有 `fetchUnreadCount`。
- `frontend/src/components/AppHeader.vue:45-48` 只在组件挂载时调用一次。
- `frontend/src/views/InboxView.vue:20-27` 标记已读后只修改当前列表项状态，没有通知头部刷新。
- `frontend/src/components/AnnouncementPopup.vue:36-41` 弹窗标记已读后也没有同步头部角标。

根因：

未读数是 Header 内部局部状态，消息已读操作没有共享状态或事件同步。

建议：

- 将未读数放入 Pinia store，收件箱和弹窗标记已读后统一刷新。
- 或在路由切换到 `/inbox`、标记已读成功后派发全局事件刷新 Header。

### 10. 非法练习路由会回退到课程 1

严重程度：低

影响范围：练习页异常路径处理

复现路径：

1. 直接访问 `/practice/quiz/abc` 或其他非数字课程 ID。
2. `Number(route.params.courseId)` 得到 `NaN`。
3. 前端使用 `|| 1` 回退为课程 1，请求课程 1 的题目。

证据：

- `frontend/src/views/PracticeQuizView.vue:10` 定义 `const courseId = computed(() => Number(route.params.courseId) || 1)`。

根因：

非法路由参数被静默替换成真实课程 ID，容易造成错误页面内容。

建议：

- 非法课程 ID 直接展示错误状态或跳回 `/practice`。
- 不要默认请求课程 1。

## 排除项

- 前端类型检查和生产构建通过，本次未发现编译级错误。
- 终端中显示的中文乱码是 PowerShell 输出编码问题；用 UTF-8 读取源码确认文件内容正常，不计入 bug。
- 课程资料和课程题目接口已经做了学生课程归属校验，本次未发现这两个接口直接越权读取资料/题目的问题。

## 建议修复顺序

1. 先修课程详情学生权限泄露。
2. 再修通知任务到练习题集的闭环，包括未开始/未答题不能完成、按公告题目集练习。
3. 修任务成绩去重，避免超过 100 分。
4. 修作品重提交图片 file_id 对齐和预览 URL。
5. 补齐错题本多题型展示、课程空状态提示和未读角标同步。

