"""add lessons and course progress

Revision ID: 20260629_add_lessons_course_progress
Revises: None
Create Date: 2026-06-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "20260629_add_lessons_course_progress"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def upgrade() -> None:
    """创建课时表和学习进度表。"""
    if not _has_table("lessons"):
        op.create_table(
            "lessons",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("course_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("content", sa.Text(), nullable=False, server_default=""),
            sa.Column(
                "status",
                sa.Enum("draft", "published", name="lesson_status"),
                nullable=False,
                server_default="published",
            ),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_lessons_course_id", "lessons", ["course_id"])
        op.create_index("ix_lessons_sort_order", "lessons", ["sort_order"])

    if not _has_table("course_progress"):
        op.create_table(
            "course_progress",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.String(length=32), nullable=False),
            sa.Column("course_id", sa.Integer(), nullable=False),
            sa.Column("last_lesson_id", sa.Integer(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["last_lesson_id"], ["lessons.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("user_id", "course_id", name="uq_course_progress_user_course"),
        )
        op.create_index("ix_course_progress_user_id", "course_progress", ["user_id"])
        op.create_index("ix_course_progress_course_id", "course_progress", ["course_id"])


def downgrade() -> None:
    """回滚课时和学习进度表。"""
    if _has_table("course_progress"):
        op.drop_index("ix_course_progress_course_id", table_name="course_progress")
        op.drop_index("ix_course_progress_user_id", table_name="course_progress")
        op.drop_table("course_progress")

    if _has_table("lessons"):
        op.drop_index("ix_lessons_sort_order", table_name="lessons")
        op.drop_index("ix_lessons_course_id", table_name="lessons")
        op.drop_table("lessons")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(name="lesson_status").drop(bind, checkfirst=True)
