"""软删除到期清理命令行入口。

供外部每周调度在周日 03:00 调用。不修改服务器配置，不启动 Web 服务。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 允许直接以脚本方式运行：python backend/scripts/run_soft_delete_cleanup.py
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal  # noqa: E402
from app.services.soft_delete_cleanup_service import cleanup_expired_resources  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="执行软删除到期快照与物理清理")
    parser.parse_args(argv)

    db = SessionLocal()
    try:
        result = cleanup_expired_resources(db)
    finally:
        db.close()

    cleaned = int(result.get("cleaned_count", 0) or 0)
    failed = int(result.get("failed_count", 0) or 0)
    print(f"软删除清理完成：成功 {cleaned} 项，失败 {failed} 项")
    if failed > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
