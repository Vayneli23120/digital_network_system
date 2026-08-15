"""数据库连接池监控 —— 检测 idle-in-transaction 连接泄漏并告警。

后台 APScheduler 定时扫描（进程内运行，物理机/Docker 均可用）：
- 用独立 psycopg2 连接（绕过 SQLAlchemy 连接池）查询 pg_stat_activity，
  因此即使连接池被泄漏连接打满，监控本身仍能工作。
- idle-in-transaction 超过 WARN_THRESHOLD → WARNING 日志 + 泄漏详情；
- 超过 CRITICAL_THRESHOLD → ERROR 日志 + 站内通知 admin。

阈值可通过环境变量 DB_LEAK_WARN_THRESHOLD / DB_LEAK_CRITICAL_THRESHOLD 覆盖。
"""

import os
from typing import List, Optional, Tuple

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

MONITOR_INTERVAL_SECONDS = 30
WARN_THRESHOLD = 5
CRITICAL_THRESHOLD = 10

_scheduler: Optional[BackgroundScheduler] = None


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _idle_in_transaction_rows() -> List[Tuple]:
    """用独立 psycopg2 连接查询 idle-in-transaction 详情（绕过连接池）。"""
    import psycopg2

    from app.shared.database import get_db_manager

    url = get_db_manager().engine.url
    conn = psycopg2.connect(
        host=url.host,
        port=url.port or 5432,
        dbname=url.database,
        user=url.username,
        password=url.password,
        connect_timeout=3,
    )
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT pid,
                   round(extract(epoch FROM (now() - xact_start)))::int AS xact_age_s,
                   left(coalesce(query, ''), 120) AS query,
                   coalesce(application_name, '') AS app_name,
                   coalesce(client_addr::text, '') AS client_addr
            FROM pg_stat_activity
            WHERE state = 'idle in transaction'
            ORDER BY xact_start
            """
        )
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        conn.close()


def _format_rows(rows: List[Tuple]) -> str:
    lines = []
    for pid, age_s, query, app, addr in rows:
        age_s = int(age_s) if age_s is not None else 0
        lines.append(
            f"  pid={pid} 持有时长={age_s}s app={app or '-'} client={addr or '-'} query={query or '-'}"
        )
    return "\n".join(lines)


def _notify_admin(count: int, details: str) -> None:
    """尽力而为：向 admin 发送站内通知（连接池接近打满时可能失败）。"""
    try:
        from app.services.notification_service import get_notification_service
        from app.shared.database import get_db_manager

        db_manager = get_db_manager()
        with db_manager.session_scope() as db:
            get_notification_service().dispatch(
                db,
                event_type="db_connection_leak",
                title=f"[数据库连接泄漏] idle-in-transaction 连接数 {count}",
                content=(
                    f"检测到 {count} 个连接卡在 idle in transaction，疑似连接泄漏，"
                    f"请排查后台任务。\n\n{details}"
                ),
                recipients=["admin"],
            )
    except Exception:
        logger.exception("连接泄漏告警通知发送失败（连接池可能已满）")


def run_connection_check() -> None:
    warn_threshold = _env_int("DB_LEAK_WARN_THRESHOLD", WARN_THRESHOLD)
    critical_threshold = _env_int("DB_LEAK_CRITICAL_THRESHOLD", CRITICAL_THRESHOLD)

    try:
        rows = _idle_in_transaction_rows()
    except Exception as exc:
        # 查询失败（如 PG 不可达）不致命，但连接池可能已彻底打满
        logger.warning("连接监控查询失败: {}", exc)
        return

    count = len(rows)
    if count >= critical_threshold:
        details = _format_rows(rows)
        logger.error("数据库连接泄漏告警：idle-in-transaction={}（临界）\n{}", count, details)
        _notify_admin(count, details)
    elif count >= warn_threshold:
        details = _format_rows(rows)
        logger.warning("数据库连接异常：idle-in-transaction={}\n{}", count, details)


def start_connection_monitor() -> BackgroundScheduler:
    """启动数据库连接监控调度器（幂等）。"""
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        run_connection_check,
        trigger=IntervalTrigger(seconds=MONITOR_INTERVAL_SECONDS),
        max_instances=1,
        coalesce=True,
        misfire_grace_time=30,
        id="connection_monitor",
    )
    _scheduler.start()
    logger.info("数据库连接监控已启动（每 {}s 一次）", MONITOR_INTERVAL_SECONDS)
    return _scheduler


def stop_connection_monitor() -> None:
    """停止数据库连接监控调度器。"""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("数据库连接监控已停止")
