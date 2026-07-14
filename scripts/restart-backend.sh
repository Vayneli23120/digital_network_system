#!/bin/bash
# restart-backend.sh — 彻底重启后端服务
#
# 用法：./scripts/restart-backend.sh
#
# 说明：
#   1. 杀掉所有 uvicorn 相关进程（包括 python -m uvicorn）
#   2. 等端口释放
#   3. 重新启动 uvicorn
#
# 适用于 systemd / supervisor / 手动管理场景。
# 如需开机自启，可用 systemd 管理：
#   /etc/systemd/system/nas-backend.service

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$APP_DIR/.venv"
LOG="$APP_DIR/logs/uvicorn.log"
PORT=8000

# 加载 .env（若存在），集中管理跨物理机/Docker 的配置（PROMETHEUS_URL 等）
if [ -f "$APP_DIR/.env" ]; then
    set -a
    . "$APP_DIR/.env"
    set +a
fi

echo "[restart] 停止所有 uvicorn 进程..."

# 杀掉所有 uvicorn 相关进程
pkill -f "uvicorn app.main" 2>/dev/null || true
pkill -f "python.*uvicorn.*app.main" 2>/dev/null || true

# 确保端口释放（软杀 + 硬杀兜底）
for i in $(seq 1 10); do
    PID=$(ss -tlnp | grep ":$PORT " | grep -oP 'pid=\K[0-9]+' || true)
    [ -z "$PID" ] && break
    kill "$PID" 2>/dev/null || true
    sleep 1
    kill -9 "$PID" 2>/dev/null || true
    sleep 1
done

if ss -tlnp | grep -q ":$PORT "; then
    echo "[restart] 错误：无法释放端口 $PORT"
    exit 1
fi

echo "[restart] 启动 uvicorn..."

mkdir -p "$APP_DIR/logs"
nohup "$VENV/bin/uvicorn" app.main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    >> "$LOG" 2>&1 &

PID=$!
echo "[restart] 已启动 PID=$PID"

# 等待进程就绪
for i in $(seq 1 15); do
    if ss -tlnp | grep -q ":$PORT "; then
        echo "[restart] 就绪，端口 $PORT 已监听"
        # 验证健康状态
        sleep 1
        if curl -sf http://localhost:$PORT/ready > /dev/null 2>&1; then
            echo "[restart] 健康检查通过 ✓"
            echo "[restart] 诊断信息：curl http://localhost:$PORT/api/system/diagnostics"
        else
            echo "[restart] 警告：健康检查未通过，请检查日志: $LOG"
        fi
        exit 0
    fi
    sleep 1
done

echo "[restart] 启动超时，请检查日志: $LOG"
exit 1
