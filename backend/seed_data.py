"""
种子数据模块（已废弃）。

历史用途：创建默认管理员和测试种子数据。
第 15 轮已将种子账号注释，第 30 轮完全清空为安全占位函数。
第 45 轮：完全移除 seed() 函数体，保留文件用于测试兼容。

生产环境初始化管理员请使用：
    py scripts/create_admin.py --id 管理员账号 --name 管理员姓名 --password 强密码
"""

# 导入保留以供 tests/test_auth.py::test_seed_data_does_not_create_default_admin 引用
from app.db.session import SessionLocal
from app.models.entities import Course, User


def seed():
    """空函数：生产环境不创建任何种子数据。

    数据库应由 scripts/create_admin.py 和业务操作填充。
    保留此函数签名供下游测试调用，确保即使误用也不会创建数据。
    """
    pass
