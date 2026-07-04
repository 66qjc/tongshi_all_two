"""一键部署脚本：建库、建表。生产环境不填充种子数据（seed_data.py 已清空）。
管理员初始化请使用：
    py scripts/create_admin.py --id <管理员账号> --name <管理员姓名> --password <强密码>
"""

import os
import sys
from pathlib import Path

import pymysql
from dotenv import load_dotenv

# 确保能找到 app 模块
sys.path.insert(0, str(Path(__file__).resolve().parent))

load_dotenv(Path(__file__).resolve().parent / ".env", override=True)


def get_mysql_conn(db=None):
    """连接 MySQL（可选指定数据库）。"""
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", "123456"),
        database=db,
        charset="utf8mb4",
        autocommit=True,
    )


def create_database():
    """创建数据库（如果不存在）。"""
    db_name = os.getenv("MYSQL_DATABASE", "tongshi")
    conn = get_mysql_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            print(f"  数据库 `{db_name}` 已就绪")
    finally:
        conn.close()


def create_tables():
    """使用 SQLAlchemy 创建所有表。"""
    from app.db.schema_compat import ensure_schema_compatibility
    from app.db.session import Base, engine
    import app.models.entities  # noqa: F401

    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility(engine)
    print("  所有表已创建")


def drop_tables():
    """删除所有表。"""
    from app.db.session import Base, engine
    import app.models.entities  # noqa: F401

    Base.metadata.drop_all(bind=engine)
    print("  所有表已删除")


def check_connection():
    """检查数据库连接。"""
    db_name = os.getenv("MYSQL_DATABASE", "tongshi")
    try:
        conn = get_mysql_conn(db_name)
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        conn.close()
        print(f"  MySQL 连接成功: {db_name}")
        return True
    except Exception as exc:
        print(f"  MySQL 连接失败: {exc}")
        return False


def main():
    args = sys.argv[1:]

    if "--check" in args:
        ok = check_connection()
        sys.exit(0 if ok else 1)

    print("=" * 50)
    print("  AI 通识课平台 - 数据库部署")
    print("=" * 50)

    print("\n[1/3] 创建数据库...")
    create_database()

    if "--reset" in args:
        print("\n[2/3] 清空并重建表...")
        drop_tables()
    else:
        print("\n[2/3] 创建表...")
    create_tables()

    print("\n[3/3] 跳过种子数据（seed_data.py 已清空）")

    print("\n" + "=" * 50)
    print("  部署完成")
    print(f"  数据库: {os.getenv('MYSQL_DATABASE', 'tongshi')}")
    print("  启动: py main.py")
    print("  管理员初始化: py scripts/create_admin.py --id <管理员账号> --name <管理员姓名> --password <强密码>")
    print("=" * 50)


if __name__ == "__main__":
    main()
