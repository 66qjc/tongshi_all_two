"""点赞并发正确性测试。

覆盖：点赞递增、取消递减、计数不为负、并发 IntegrityError 兜底。
"""
from app.models.entities import Project, ProjectLike
from app.services.project_service import toggle_like
from app.api.v1.routes import project_routes
from tests.conftest import auth_header


def _create_approved_project(db_session, title="测试作品"):
    """创建一个已审核通过的作品。"""
    project = Project(
        title=title,
        description="测试",
        author_id="2025001",
        status="approved",
        likes=0,
    )
    db_session.add(project)
    db_session.commit()
    return project


# ─── 场景 1：点赞递增计数 ───


def test_like_increments_count(db_session):
    """点赞后 likes 应 +1，返回 liked=True。"""
    project = _create_approved_project(db_session)
    result = toggle_like(db_session, "2025001", project.id)
    assert result["liked"] is True
    assert result["likes"] == 1


# ─── 场景 2：取消点赞递减计数 ───


def test_unlike_decrements_count(db_session):
    """取消点赞后 likes 应 -1，返回 liked=False。"""
    project = _create_approved_project(db_session)
    toggle_like(db_session, "2025001", project.id)
    result = toggle_like(db_session, "2025001", project.id)
    assert result["liked"] is False
    assert result["likes"] == 0


# ─── 场景 3：计数不为负 ───


def test_likes_never_negative(db_session):
    """likes 已为 0 时取消点赞不应变为负数。"""
    project = _create_approved_project(db_session)
    # 手动插入一条 like 记录但 likes 保持 0（模拟数据不一致）
    db_session.add(ProjectLike(user_id="2025001", project_id=project.id))
    db_session.commit()

    result = toggle_like(db_session, "2025001", project.id)
    assert result["liked"] is False
    assert result["likes"] == 0, "likes 不应为负数"


# ─── 场景 4：多用户独立点赞 ───


def test_multiple_users_like_independently(db_session):
    """不同用户各自点赞，计数累加。"""
    project = _create_approved_project(db_session)
    r1 = toggle_like(db_session, "2025001", project.id)
    r2 = toggle_like(db_session, "2025002", project.id)
    assert r1["likes"] == 1
    assert r2["likes"] == 2


# ─── 场景 5：不存在的作品返回 None ───


def test_toggle_like_nonexistent_project(db_session):
    """对不存在的作品点赞应返回 None。"""
    result = toggle_like(db_session, "2025001", 99999)
    assert result is None


# ─── 场景 6：并发 IntegrityError 兜底（模拟） ───


def test_concurrent_like_integrity_fallback(db_session, monkeypatch):
    """flush 唯一冲突时应回滚，并返回另一请求已完成点赞的幂等状态。"""
    from sqlalchemy.exc import IntegrityError

    project = _create_approved_project(db_session)
    original_rollback = db_session.rollback
    rollback_called = False

    def fail_flush(*args, **kwargs):
        raise IntegrityError("INSERT project_likes", {}, Exception("duplicate key"))

    def track_rollback():
        nonlocal rollback_called
        rollback_called = True
        original_rollback()

    monkeypatch.setattr(db_session, "flush", fail_flush)
    monkeypatch.setattr(db_session, "rollback", track_rollback)

    result = toggle_like(db_session, "2025001", project.id)

    assert rollback_called
    assert result == {"liked": True, "likes": 0}


# ─── 场景 7：API 层游客点赞限流 ───


def test_guest_like_rate_limit(client, db_session):
    """游客点赞 3 秒内重复应被限流（429）。"""
    project = _create_approved_project(db_session, "限流测试作品")
    project_id = project.id

    # 第一次点赞成功
    resp1 = client.post(f"/api/projects/{project_id}/guest-like")
    assert resp1.json()["code"] == 0

    # 立即再次点赞应被限流
    resp2 = client.post(f"/api/projects/{project_id}/guest-like")
    assert resp2.status_code == 429 or resp2.json().get("code") == 429




def test_guest_like_does_not_reuse_limit_after_project_id_reuse(client, db_session):
    """数据库重建并复用作品 ID 后，第一次游客点赞不能继承旧限流状态。"""
    project_routes._guest_like_last.clear()
    project = _create_approved_project(db_session, "old-project")
    project_id = project.id

    first = client.post(f"/api/projects/{project_id}/guest-like")
    assert first.json()["code"] == 0

    db_session.delete(project)
    db_session.commit()
    replacement = Project(
        id=project_id,
        title="new-project",
        description="test",
        author_id="2025001",
        status="approved",
        likes=0,
    )
    db_session.add(replacement)
    db_session.commit()

    second = client.post(f"/api/projects/{project_id}/guest-like")

    assert second.json()["code"] == 0
