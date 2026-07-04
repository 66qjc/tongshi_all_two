from app.models.entities import PasswordResetRequest
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


def test_teacher_can_approve_reset_request_for_own_class_student(client, db_session, teacher_token):
    req = _reset_request(db_session, "2025001")

    response = client.post(
        f"/api/teacher/password-reset-requests/{req.id}/approve",
        headers=auth_header(teacher_token),
    )
    data = response.json()

    assert response.status_code == 200
    assert data["code"] == 0
    assert data["data"]["temp_password"]


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
