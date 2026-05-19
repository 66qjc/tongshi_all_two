"""Pydantic request / response schemas"""
from typing import List, Optional
from pydantic import BaseModel, Field


# ── Auth ────────────────────────────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthUser(BaseModel):
    id: str
    name: str
    role: str
    major: Optional[str] = None


class LoginRequest(BaseModel):
    id: str
    password: str


class RegisterRequest(BaseModel):
    id: str
    name: str
    password: str = Field(min_length=6)
    role: str = "student"
    major: Optional[str] = None


# ── Chapter ─────────────────────────────────────────────────────────────────
class ChapterOut(BaseModel):
    id: int
    num: str
    title: str
    desc: str
    topics: List[str]
    status: str
    videos: int = 0
    docs: int = 0
    progress: int = 0

    class Config:
        from_attributes = True


class ChapterUpdate(BaseModel):
    status: Optional[str] = None


# ── Material ────────────────────────────────────────────────────────────────
class MaterialOut(BaseModel):
    id: int
    chapter_id: int
    chapter: str = ""
    type: str
    title: str
    url: str
    duration: str = ""
    pages: int = 0
    size: str = ""
    date: str = ""

    class Config:
        from_attributes = True


class MaterialCreate(BaseModel):
    chapter_id: int
    type: str = "video"
    title: str = Field(min_length=1)


# ── Question ────────────────────────────────────────────────────────────────
class QuestionOut(BaseModel):
    id: int
    type: str
    chapter_id: int
    stem: str
    options: List[str] = []
    answer: str
    explanation: str = ""

    class Config:
        from_attributes = True


class QuestionCreate(BaseModel):
    type: str = "choice"
    chapter_id: int
    stem: str
    options: List[str] = []
    answer: str
    explanation: str = ""


class QuestionUpdate(QuestionCreate):
    pass


# ── Quiz ────────────────────────────────────────────────────────────────────
class QuizSubmitRequest(BaseModel):
    question_id: int
    user_answer: str


class QuizAttemptOut(BaseModel):
    id: int
    question_id: int
    user_answer: str
    is_correct: bool
    correct_answer: str = ""
    explanation: str = ""
    answered_at: str = ""

    class Config:
        from_attributes = True


class QuizStatsOut(BaseModel):
    total_questions: int
    questions_done: int
    accuracy: int
    today_count: int


class ChapterQuizStatsOut(BaseModel):
    chapter_id: int
    questions_done: int
    accuracy: int


# ── Project ─────────────────────────────────────────────────────────────────
class ProjectOut(BaseModel):
    id: int
    title: str
    author_id: str
    author_name: str = ""
    major: str = ""
    description: str
    tags: List[str] = []
    likes: int = 0
    featured: bool = False
    video_url: str = ""
    report_url: str = ""
    image_url: str = ""
    status: str = "pending"
    reject_reason: str = ""
    date: str = ""

    class Config:
        from_attributes = True


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1)
    description: str = ""
    tags: List[str] = []
    video_url: str = ""
    report_url: str = ""
    image_url: str = ""


class ProjectReviewAction(BaseModel):
    reason: Optional[str] = None


# ── Teacher ─────────────────────────────────────────────────────────────────
class StudentOut(BaseModel):
    id: str
    name: str
    major: str = ""
    progress: int = 0
    exercises: int = 0
    accuracy: int = 0


class TeacherStatsOut(BaseModel):
    total_students: int
    published_chapters: int
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
    url: str
    filename: str
    size: int
