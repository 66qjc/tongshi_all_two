"""Pydantic request / response schemas"""
import re
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

MATERIAL_TYPES = {"video", "pdf", "link"}
QUESTION_TYPES = {"choice", "fill", "multi_choice"}


# ── Auth ────────────────────────────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthUser(BaseModel):
    id: str
    name: str
    role: str
    major: Optional[str] = None
    needs_password_change: bool = False


class LoginRequest(BaseModel):
    id: str
    password: str


class RegisterRequest(BaseModel):
    id: str
    name: str
    password: str = Field(min_length=6)
    role: str = "student"
    major: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not re.search(r"[a-zA-Z]", v):
            raise ValueError("密码必须包含至少一个字母")
        if not re.search(r"\d", v):
            raise ValueError("密码必须包含至少一个数字")
        return v


# ── Class ───────────────────────────────────────────────────────────────────
class ClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    course_id: int
    course_name: str = ""
    student_count: int = 0
    created_at: Optional[str] = None


class ClassCreate(BaseModel):
    name: str = Field(min_length=1)
    course_id: int


class ClassUpdate(BaseModel):
    name: Optional[str] = None
    course_id: Optional[int] = None


class ClassStudentOut(BaseModel):
    serial_no: int = 0
    id: str
    name: str
    major: str = ""
    enrolled_at: Optional[str] = None


class ClassImportResult(BaseModel):
    success_count: int = 0
    skip_count: int = 0
    fail_count: int = 0
    errors: List[dict] = []


class ClassEnrollRequest(BaseModel):
    student_id: str = Field(min_length=1)
    name: str = ""  # 姓名，为空时仅添加已存在账号；非空时可自动创建账号
    major: str = ""  # 专业，自动创建时写入；已有学生若提供则更新


class AnnouncementCreate(BaseModel):
    course_id: int
    class_ids: List[int] = Field(default_factory=list)
    title: str = Field(min_length=1)
    question_ids: List[int] = []
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class CourseCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    is_public: bool = False


class CourseUpdateRequest(BaseModel):
    name: str = Field(min_length=1)
    is_public: Optional[bool] = None


# ── Material ────────────────────────────────────────────────────────────────
class MaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    course_name: str = ""
    type: str
    title: str
    url: str
    duration: str = ""
    pages: int = 0
    size: str = ""
    date: str = ""
    file_id: Optional[int] = None
    source_material_id: Optional[int] = None
    is_synced: bool = False


class MaterialCreate(BaseModel):
    course_id: int
    type: str = "video"
    title: str = Field(min_length=1)
    url: str = ""
    size: str = "0 MB"
    file_id: Optional[int] = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if value not in MATERIAL_TYPES:
            raise ValueError("资料类型必须为 video、pdf 或 link")
        return value


# ── Question ────────────────────────────────────────────────────────────────
class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    course_id: int
    course_name: str = ""
    stem: str
    options: List[str] = []
    answer: str
    explanation: str = ""
    tags: List[str] = []
    source_question_id: Optional[int] = None
    is_synced: bool = False


class QuestionCreate(BaseModel):
    type: str = "choice"
    course_id: int
    stem: str
    options: List[str] = []
    answer: str
    explanation: str = ""
    tags: List[str] = []

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if value not in QUESTION_TYPES:
            raise ValueError("题型必须为 choice、fill 或 multi_choice")
        return value


class QuestionUpdate(QuestionCreate):
    pass


class AdminPublicCourseCreate(BaseModel):
    name: str = Field(min_length=1)


class AdminPublicCourseUpdate(BaseModel):
    name: str = Field(min_length=1)


class AdminMaterialUpdate(BaseModel):
    type: str = "video"
    title: str = Field(min_length=1)
    url: str = ""
    size: str = "0 MB"
    file_id: Optional[int] = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if value not in MATERIAL_TYPES:
            raise ValueError("资料类型必须为 video、pdf 或 link")
        return value


class AdminQuestionCreate(BaseModel):
    type: str = "choice"
    stem: str
    options: List[str] = []
    answer: str
    explanation: str = ""
    tags: List[str] = []

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if value not in QUESTION_TYPES:
            raise ValueError("题型必须为 choice、fill 或 multi_choice")
        return value


class AdminQuestionUpdate(AdminQuestionCreate):
    pass


# ── Quiz ────────────────────────────────────────────────────────────────────
class QuizSubmitRequest(BaseModel):
    question_id: int
    user_answer: str
    announcement_id: Optional[int] = None


class QuizAttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    user_answer: str
    is_correct: bool
    correct_answer: str = ""
    explanation: str = ""
    answered_at: str = ""


class QuizStatsOut(BaseModel):
    total_questions: int
    questions_done: int
    accuracy: int
    today_count: int


class CourseQuizStatsOut(BaseModel):
    course_id: int
    questions_done: int
    accuracy: int


class ProjectImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    image_url: str = ""
    sort_order: int = 0
    file_id: Optional[int] = None


# ── Project ─────────────────────────────────────────────────────────────────
class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author_id: str
    author_name: str = ""
    course_id: Optional[int] = None
    course_name: str = ""
    major: str = ""
    description: str
    tags: List[str] = []
    likes: int = 0
    featured: bool = False
    video_url: str = ""
    report_url: str = ""
    image_url: str = ""
    images: List[ProjectImageOut] = []
    link_url: str = ""
    status: str = "pending"
    reject_reason: str = ""
    date: str = ""
    report_file_id: Optional[int] = None
    cover_file_id: Optional[int] = None


class ProjectCreate(BaseModel):
    course_id: int
    title: str = Field(min_length=1)
    description: str = ""
    tags: List[str] = []
    video_url: str = ""
    report_url: str = ""
    image_url: str = ""
    image_urls: List[str] = []
    link_url: str = ""
    report_file_id: Optional[int] = None
    cover_file_id: Optional[int] = None
    image_file_ids: List[int] = []


class ProjectUpdate(BaseModel):
    course_id: int
    title: str = Field(min_length=1)
    description: str = ""
    tags: List[str] = []
    video_url: str = ""
    report_url: str = ""
    image_url: str = ""
    image_urls: List[str] = []
    link_url: str = ""
    report_file_id: Optional[int] = None
    cover_file_id: Optional[int] = None
    image_file_ids: List[int] = []


class ProjectReviewAction(BaseModel):
    reason: Optional[str] = None


# ── Teacher ─────────────────────────────────────────────────────────────────
class StudentTaskScoreOut(BaseModel):
    announcement_id: int
    title: str
    score: Optional[int] = None
    is_completed: bool = False


class StudentOut(BaseModel):
    serial_no: int = 0
    id: str
    name: str
    major: str = ""
    class_id: Optional[int] = None
    class_name: str = ""
    progress: int = 0
    exercises: int = 0
    accuracy: int = 0
    completed_tasks: int = 0
    incomplete_tasks: int = 0
    task_completion_rate: int = 0
    task_scores: List[StudentTaskScoreOut] = []


class TeacherStatsOut(BaseModel):
    total_students: int
    my_courses: int
    public_courses: int = 0
    pending_reviews: int
    weekly_exercises: int


# ── Portfolio ───────────────────────────────────────────────────────────────
class PortfolioStatsOut(BaseModel):
    study_hours: int = 0
    total_exercises: int = 0
    accuracy: int = 0
    project_count: int = 0


class PortfolioOut(BaseModel):
    user: AuthUser
    stats: PortfolioStatsOut
    radar: dict = {}
    timeline: list = []
    projects: List[ProjectOut] = []


# ── Upload ──────────────────────────────────────────────────────────────────
class UploadOut(BaseModel):
    file_id: Optional[int] = None
    url: str
    filename: str
    size: int
    content_type: str = ""
    storage_provider: str = ""


# ── Admin ───────────────────────────────────────────────────────────────────
class CreateTeacherRequest(BaseModel):
    """管理员手动创建教师账号请求"""
    id: str = Field(..., description="工号")
    name: str = Field(..., description="姓名")
    major: Optional[str] = Field(None, description="专业")


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6,
                              description="新密码（至少6位，含字母和数字）")

    @field_validator("new_password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        import re
        if not re.search(r"[a-zA-Z]", v):
            raise ValueError("新密码必须包含至少一个字母")
        if not re.search(r"\d", v):
            raise ValueError("新密码必须包含至少一个数字")
        return v


class TeacherInfo(BaseModel):
    """教师信息（管理员列表用）"""
    id: str
    name: str
    major: Optional[str] = None
    created_at: Optional[str] = None
    needs_password_change: bool = False


class ForgotPasswordRequest(BaseModel):
    """忘记密码（已废弃，请使用新的两步验证流程）"""
    id: str
    new_password: str = Field(min_length=6)

    @field_validator("new_password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        import re
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("密码必须包含至少一个字母和一个数字")
        return v


# ── 密保问题 ─────────────────────────────────────────────────────────────

class SecurityQuestionItem(BaseModel):
    """单个密保问题"""
    question: str = Field(min_length=1, max_length=200)


class SecurityQuestionIn(BaseModel):
    """设置密保问题（含答案）"""
    question: str = Field(min_length=1, max_length=200)
    answer: str = Field(min_length=1, max_length=100)


class SecurityQuestionsUpdate(BaseModel):
    """批量设置密保问题"""
    questions: list[SecurityQuestionIn] = Field(min_length=0, max_length=3)


class SecurityQuestionOut(BaseModel):
    """密保问题输出（不含答案）"""
    id: int
    question: str


class ForgotPasswordCheckRequest(BaseModel):
    """忘记密码 — 提交答案验证"""
    user_id: str
    answers: list[dict]  # [{question_id: int, answer: str}]
    new_password: str = Field(min_length=6)

    @field_validator("new_password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        import re
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("密码必须包含至少一个字母和一个数字")
        return v


class ForgotPasswordManualRequest(BaseModel):
    """忘记密码 — 提交人工重置申请"""
    user_id: str
    message: str = Field(min_length=1, max_length=500)


class ResetRequestResolve(BaseModel):
    """审批密码重置请求"""
    reason: str = Field(default="", max_length=256)


class ResetRequestOut(BaseModel):
    """密码重置请求输出"""
    id: int
    user_id: str
    user_name: str = ""
    message: str
    status: str
    resolved_by: Optional[str] = None
    resolved_at: Optional[str] = None
    created_at: str = ""


# ===== Showcase（悟页面图文内容）=====

class ShowcaseItemCreate(BaseModel):
    """管理员新增图文内容"""
    section: str
    title: str = Field(min_length=1, max_length=128)
    content: str = ""
    cover_file_id: Optional[int] = None
    image_file_ids: List[int] = Field(default_factory=list)
    link_url: str = ""
    sort_order: int = 0


class ShowcaseItemUpdate(BaseModel):
    """管理员修改图文内容"""
    title: Optional[str] = None
    content: Optional[str] = None
    cover_file_id: Optional[int] = None
    image_file_ids: Optional[List[int]] = None
    link_url: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class ShowcaseItemImageOut(BaseModel):
    """图文内容图片输出"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_id: int
    url: str = ""
    sort_order: int = 0


class ShowcaseItemOut(BaseModel):
    """图文内容输出"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    section: str
    title: str
    content: str
    cover_url: str = ""
    images: List[ShowcaseItemImageOut] = Field(default_factory=list)
    link_url: str = ""
    sort_order: int = 0
    is_active: bool = True
    created_at: datetime
