"""
批次三 3.5 · 启动与关闭 · 静态断言测试

不依赖运行态（不 import app，避免触发启动副作用），直接读源文件断言关键生命周期代码存在。
对应 3.5 四项：shutdown 事件、prometheus 轮询 job、中间件顺序、trap_receiver join。
"""

from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[1] / "app"


def _read(rel_path: str) -> str:
    return (APP_DIR / rel_path).read_text(encoding="utf-8")


class TestShutdownEvent:
    def test_has_on_event_shutdown(self):
        """main.py 注册 shutdown 事件（优雅关闭在 lifespan 触发，而非被覆盖的 signal handler）"""
        src = _read("main.py")
        assert 'on_event("shutdown")' in src
        assert "async def shutdown_event" in src

    def test_no_module_level_signal_signal(self):
        """已删除模块级 signal.signal（会被 uvicorn handler 覆盖，属无效注册）"""
        src = _read("main.py")
        assert "signal.signal(" not in src
        assert "import signal" not in src

    def test_shutdown_stops_services_and_disposes_pool(self):
        """shutdown 事件仍清理三服务 + 连接池 + 缓存"""
        src = _read("main.py")
        for token in (
            "stop_reachability_monitor",
            "stop_connector",
            "stop_trap_receiver",
            "engine.dispose",
            "cache.clear",
        ):
            assert token in src


class TestPrometheusConnector:
    def test_poll_job_no_blocking_immediate_run(self):
        """start() 不再同步阻塞 poll_once()"""
        src = _read("services/prometheus_connector.py")
        start_block = src.split("def start(self):", 1)[1].split("def stop(self):", 1)[0]
        assert "self.poll_once()" not in start_block

    def test_poll_job_has_max_instances_and_coalesce(self):
        """轮询 job 设置 max_instances=1 / coalesce=True，防周期重叠"""
        src = _read("services/prometheus_connector.py")
        poll_job = src.split('id="prometheus_connector_poll"', 1)[1].split(
            'id="prometheus_metric_retention"', 1
        )[0]
        assert "max_instances=1" in poll_job
        assert "coalesce=True" in poll_job
        assert "next_run_time=datetime.now()" in poll_job

    def test_last_counters_lock_guarded(self):
        """_last_counters 读写受 threading.Lock 保护（避免速率算错）"""
        src = _read("services/prometheus_connector.py")
        assert "_counters_lock" in src
        assert src.count("with self._counters_lock:") >= 2


class TestMiddlewareOrder:
    def test_rate_limit_registered_before_auth(self):
        """RateLimitMiddleware 注册在 auth_middleware 之前 → 入站先认证后限流"""
        src = _read("main.py")
        rate_limiter_pos = src.find("app.add_middleware(RateLimitMiddleware)")
        auth_pos = src.find("app.middleware(\"http\")(auth_middleware)")
        assert rate_limiter_pos != -1 and auth_pos != -1
        assert rate_limiter_pos < auth_pos

    def test_middleware_reads_user_id(self):
        """限流中间件读取 scope['state']['user_id'] 支持按用户限流"""
        src = _read("shared/middleware/rate_limiter_v2.py")
        assert "user_id" in src
        assert 'scope.get("state")' in src or 'scope["state"]' in src


class TestTrapReceiverStop:
    def test_stop_joins_thread(self):
        """stop() 关 socket 后 join 接收线程"""
        src = _read("services/trap_receiver.py")
        stop_block = src.split("def stop(self):", 1)[1].split("def diagnostics", 1)[0]
        assert "self._thread.join(timeout=2.0)" in stop_block
