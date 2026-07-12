import pytest

from app.models.entities import AuditLog, PasswordResetRequest, User
from app.api.v1.routes import teacher_routes
from tests.conftest import auth_header


def _reset_request(db_session, user_id="2025002"):
    req = PasswordResetRequest(user_id=user_id, message="忘记密码")
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)
    return req


def test_teacher_cannot_approve_reset_request_for_other_class_student(client, db_session, teacher_token):
    req = _reset_request(db_session, "2025002")

    response = client.post(
        f"/api/teacher/password-reset-requests/{req.id}/approve",
        headers=auth_header(teacher_token),
    )
    data = response.json()

    assert response.status_code == 200
    assert data["code"] == 404


def test_teacher_cannot_reject_reset_request_for_other_class_student(client, db_session, teacher_token):
    req = _reset_request(db_session, "2025002")

    response = client.post(
        f"/api/teacher/password-reset-requests/{req.id}/reject",
        json={"reason": "信息不匹配"},
        headers=auth_header(teacher_token),
    )
    data = response.json()

    assert response.status_code == 200
    assert data["code"] == 404


def test_teacher_can_approve_reset_request_for_own_class_student(client, db_session, teacher_token, student_token):
    req = _reset_request(db_session, "2025001")

    response = client.post(
        f"/api/teacher/password-reset-requests/{req.id}/approve",
        headers=auth_header(teacher_token),
    )
    data = response.json()

    assert response.status_code == 200
    assert data["code"] == 0
    assert data["data"]["temp_password"]
    assert client.get("/api/me", headers=auth_header(student_token)).json()["code"] == 401
    assert db_session.query(AuditLog).filter(
        AuditLog.user_id == "T001",
        AuditLog.action == "user.password_reset",
        AuditLog.resource_id == "2025001",
    ).count() == 1


def test_teacher_approval_rolls_back_when_audit_write_fails(
    client,
    db_session,
    teacher_token,
    monkeypatch,
):
    """审计写入失败时，审批状态和目标用户密码必须一并回滚。"""
    req = _reset_request(db_session, "2025001")
    user = db_session.get(User, "2025001")
    original_password_hash = user.hashed_password
    original_token_version = user.token_version

    def fail_audit_write(*args, **kwargs):
        raise RuntimeError("模拟审计写入失败")

    monkeypatch.setattr(teacher_routes, "create_audit_log", fail_audit_write, raising=False)

    with pytest.raises(RuntimeError, match="模拟审计写入失败"):
        client.post(
            f"/api/teacher/password-reset-requests/{req.id}/approve",
            headers=auth_header(teacher_token),
        )

    db_session.expire_all()
    refreshed_request = db_session.get(PasswordResetRequest, req.id)
    refreshed_user = db_session.get(User, "2025001")
    assert refreshed_request.status == "pending"
    assert refreshed_user.hashed_password == original_password_hash
    assert refreshed_user.token_version == original_token_version


def test_teacher_reset_request_list_does_not_return_temp_password_after_approval(client, db_session, teacher_token):
    req = _reset_request(db_session, "2025001")
    approve = client.post(
        f"/api/teacher/password-reset-requests/{req.id}/approve",
        headers=auth_header(teacher_token),
    )
    assert approve.json()["code"] == 0
    assert approve.json()["data"]["temp_password"]

    listing = client.get("/api/teacher/password-reset-requests", headers=auth_header(teacher_token))
    item = next(row for row in listing.json()["data"] if row["id"] == req.id)

    assert item["temp_password"] == ""
