"""
批次十 · Part ② 保留配置 config 化测试。

机制本身在 test_metric_retention.py（清理/分页/时序索引），本文件只测
「保留参数如何从 config.yaml / env 流入 Config.metrics 与 PrometheusConnector」：
- Config.load() 无 metrics 块时的默认值
- config.yaml 的 metrics: 块生效
- env（DEVICE_METRIC_*）覆盖 YAML
- Connector 未显式传参时读 Config.metrics，显式传参时以显式值为准
"""

import pytest

from app.services.prometheus_connector import PrometheusConnector
from app.shared.config import Config


def _write_config(tmp_path, metrics_block):
    text = (
        "app:\n  debug: false\n"
        "security:\n  auth_enabled: false\n"
    )
    if metrics_block is not None:
        text += metrics_block
    path = tmp_path / "config.yaml"
    path.write_text(text, encoding="utf-8")
    return str(path)


class TestMetricsConfig:
    def test_defaults_when_no_metrics_block(self, tmp_path):
        cfg = Config.load(_write_config(tmp_path, None))
        assert cfg.metrics.retention_days == 90
        assert cfg.metrics.cleanup_interval_seconds == 86400
        assert cfg.metrics.cleanup_batch_size == 5000

    def test_yaml_block_honored(self, tmp_path):
        block = (
            "metrics:\n"
            "  retention_days: 30\n"
            "  cleanup_interval_seconds: 7200\n"
            "  cleanup_batch_size: 100\n"
        )
        cfg = Config.load(_write_config(tmp_path, block))
        assert cfg.metrics.retention_days == 30
        assert cfg.metrics.cleanup_interval_seconds == 7200
        assert cfg.metrics.cleanup_batch_size == 100


class TestMetricsEnvOverride:
    def test_env_wins_over_yaml(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DEVICE_METRIC_RETENTION_DAYS", "45")
        monkeypatch.setenv("DEVICE_METRIC_CLEANUP_INTERVAL", "10800")
        monkeypatch.setenv("DEVICE_METRIC_CLEANUP_BATCH_SIZE", "200")
        block = (
            "metrics:\n"
            "  retention_days: 30\n"
            "  cleanup_interval_seconds: 7200\n"
            "  cleanup_batch_size: 100\n"
        )
        cfg = Config.load(_write_config(tmp_path, block))
        assert cfg.metrics.retention_days == 45
        assert cfg.metrics.cleanup_interval_seconds == 10800
        assert cfg.metrics.cleanup_batch_size == 200

    def test_invalid_env_int_raises(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DEVICE_METRIC_RETENTION_DAYS", "not-an-int")
        with pytest.raises(ValueError, match="DEVICE_METRIC_RETENTION_DAYS"):
            Config.load(_write_config(tmp_path, None))


class TestConnectorPicksUpConfig:
    def test_uses_config_defaults_when_params_none(self, monkeypatch):
        class FakeMetrics:
            retention_days = 90
            cleanup_interval_seconds = 86400
            cleanup_batch_size = 5000

        class FakeConfig:
            metrics = FakeMetrics()

        monkeypatch.setattr(
            "app.services.prometheus_connector.get_config", lambda: FakeConfig()
        )
        connector = PrometheusConnector("http://prometheus.test")
        try:
            assert connector._metric_retention_days == 90
            assert connector._metric_cleanup_batch_size == 5000
            assert connector._metric_cleanup_interval == 86400
        finally:
            connector._http.close()

    def test_explicit_params_win_over_config(self, monkeypatch):
        class FakeMetrics:
            retention_days = 90
            cleanup_interval_seconds = 86400
            cleanup_batch_size = 5000

        class FakeConfig:
            metrics = FakeMetrics()

        monkeypatch.setattr(
            "app.services.prometheus_connector.get_config", lambda: FakeConfig()
        )
        connector = PrometheusConnector(
            "http://prometheus.test",
            metric_retention_days=5,
            metric_cleanup_batch_size=2,
            metric_cleanup_interval=3600,
        )
        try:
            assert connector._metric_retention_days == 5
            assert connector._metric_cleanup_batch_size == 2
            assert connector._metric_cleanup_interval == 3600
        finally:
            connector._http.close()
