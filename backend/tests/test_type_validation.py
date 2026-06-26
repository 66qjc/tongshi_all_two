"""资料和题目类型校验测试。"""

import pytest
from pydantic import ValidationError

from app.schemas.common import AdminMaterialUpdate, AdminQuestionCreate, MaterialCreate, QuestionCreate


def test_material_type_allows_known_values():
    assert MaterialCreate(course_id=1, type="video", title="视频").type == "video"
    assert MaterialCreate(course_id=1, type="pdf", title="讲义").type == "pdf"
    assert AdminMaterialUpdate(type="link", title="链接").type == "link"


def test_material_type_rejects_unknown_value():
    with pytest.raises(ValidationError):
        MaterialCreate(course_id=1, type="bad", title="脏数据")


def test_question_type_allows_known_values():
    assert QuestionCreate(course_id=1, type="choice", stem="题干", answer="A").type == "choice"
    assert QuestionCreate(course_id=1, type="fill", stem="题干", answer="答案").type == "fill"
    assert AdminQuestionCreate(type="multi_choice", stem="题干", answer="AB").type == "multi_choice"


def test_question_type_rejects_unknown_value():
    with pytest.raises(ValidationError):
        QuestionCreate(course_id=1, type="essay", stem="题干", answer="答案")


def test_material_title_max_length():
    """资料标题不能超过 128 个字符。"""
    with pytest.raises(ValidationError):
        AdminMaterialUpdate(type="pdf", title="A" * 129)
    assert AdminMaterialUpdate(type="pdf", title="A" * 128).title == "A" * 128
