#!/usr/bin/env bash
set -e

# ============================================================
#  AI 通识课平台 — 一键启动脚本 (MySQL + Backend + Frontend)
#  Ctrl+C 停止所有服务
# ============================================================

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

MYSQL_PORT=3307
BACKEND_PORT=8050
FRONTEND_PORT=5173

# ── 颜色输出 ────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*"; }

# ── 清理 ────────────────────────────────────────────────────
cleanup() {
    echo ""
    info "正在关闭所有服务..."
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null && ok "后端已停止"
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null && ok "前端已停止"
    ok "所有服务已关闭"
    exit 0
}
trap cleanup SIGINT SIGTERM

# ── 1. MySQL ────────────────────────────────────────────────
echo ""
echo "=========================================="

info "检测 MySQL (127.0.0.1:$MYSQL_PORT) ..."

MYSQL_RUNNING=false
if mysqladmin ping -h 127.0.0.1 -P $MYSQL_PORT -u root -p'123456' --silent 2>/dev/null; then
    ok "MySQL 已在运行 (127.0.0.1:$MYSQL_PORT)"
    MYSQL_RUNNING=true
fi

if [ "$MYSQL_RUNNING" = false ]; then
    warn "MySQL 未运行，正在启动..."
    sudo mkdir -p /var/run/mysqld
    sudo chown mysql:mysql /var/run/mysqld
    sudo mysqld --port=$MYSQL_PORT --mysqlx=0 --user=mysql --datadir=/var/lib/mysql &
    MYSQL_START_PID=$!

    # 等待就绪
    for i in $(seq 1 15); do
        if mysqladmin ping -h 127.0.0.1 -P $MYSQL_PORT -u root -p'123456' --silent 2>/dev/null; then
            ok "MySQL 启动成功 (127.0.0.1:$MYSQL_PORT)"
            MYSQL_RUNNING=true
            break
        fi
        sleep 1
    done

    if [ "$MYSQL_RUNNING" = false ]; then
        err "MySQL 启动失败，请检查日志: tail /var/log/mysql/error.log"
        exit 1
    fi
fi

# ── 2. Backend ──────────────────────────────────────────────
echo ""
info "启动后端 (port $BACKEND_PORT) ..."

# 自动初始化数据库（如果表不存在）
cd "$BACKEND_DIR"
if ! .venv/bin/python -c "from app.db.session import SessionLocal; db=SessionLocal(); db.close()" 2>/dev/null; then
    warn "数据库未初始化，正在执行 database_setup.py ..."
    .venv/bin/python database_setup.py
    ok "数据库初始化完成"
fi

.venv/bin/python main.py &
BACKEND_PID=$!

# 等待后端就绪
for i in $(seq 1 20); do
    if curl -s http://127.0.0.1:$BACKEND_PORT/health 2>/dev/null | grep -q '"ok"'; then
        ok "后端启动成功: http://127.0.0.1:$BACKEND_PORT"
        break
    fi
    sleep 1
done
if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    err "后端启动失败"
    cleanup && exit 1
fi

# ── 3. Frontend ──────────────────────────────────────────────
echo ""
info "启动前端 (port $FRONTEND_PORT) ..."

cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!

# 等待前端就绪
for i in $(seq 1 15); do
    if curl -s http://localhost:$FRONTEND_PORT 2>/dev/null | grep -q '<html'; then
        ok "前端启动成功: http://localhost:$FRONTEND_PORT"
        break
    fi
    sleep 1
done
if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
    err "前端启动失败"
    cleanup && exit 1
fi

# ── 就绪 ────────────────────────────────────────────────────
echo ""
echo "=========================================="
echo -e "  ${GREEN}${PROJECT_NAME:-AI 通识课平台} 全部就绪 ✓${NC}"
echo ""
echo -e "  ${CYAN}前端页面:${NC}   http://localhost:$FRONTEND_PORT"
echo -e "  ${CYAN}后端 API:${NC}   http://localhost:$BACKEND_PORT"
echo -e "  ${CYAN}API 文档:${NC}   http://localhost:$BACKEND_PORT/docs"
echo -e "  ${CYAN}数据库:${NC}     127.0.0.1:$MYSQL_PORT"
echo ""
echo -e "  ${YELLOW}默认账号:${NC}   admin / admin123456"
echo -e "  ${YELLOW}停止服务:${NC}   Ctrl+C"
echo "=========================================="
echo ""

# 等待任意子进程退出
wait
