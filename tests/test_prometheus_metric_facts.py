"""Tests for periodic device facts produced by the Prometheus connector."""

from app.services import prometheus_connector as connector_module
from app.services.prometheus_connector import (
    PrometheusConnector,
    _build_device_metric_payload,
)
from app.shared.models import Device, DeviceInterface, DeviceMetricSample


def test_build_device_metric_payload_aggregates_interfaces():
    payload = _build_device_metric_payload(
        {
            1: {"ifOperStatus": 1, "ifInErrors": 2, "ifOutErrors": 1},
            2: {"ifOperStatus": 2, "ifInErrors": 0, "ifOutErrors": 3},
            3: {"ifOperStatus": 6},
        },
        uptime_days=19,
    )

    assert payload["uptime"]["uptime_days"] == 19
    assert payload["interfaces"] == {"up": 1, "down": 1, "total": 3}
    assert payload["errors"]["total_errors"] == 6
    assert payload["errors"]["has_errors"] is True

    unknown = _build_device_metric_payload(
        {1: {"ifInErrors": 0, "ifOutErrors": 0}},
        uptime_days=None,
    )
    assert unknown["interfaces"] == {"up": None, "down": None, "total": None}


def test_fetch_device_uptimes_converts_exporter_seconds(monkeypatch):
    connector = PrometheusConnector("http://prometheus.test")
    monkeypatch.setattr(
        connector,
        "_query",
        lambda metric: [
            {"metric": {"instance": "192.0.2.40"}, "value": [1, "1641600"]},
            {"metric": {}, "value": [1, "100"]},
            {"metric": {"instance": "192.0.2.41"}, "value": [1, "invalid"]},
        ],
    )

    try:
        assert connector._fetch_device_uptimes() == {"192.0.2.40": 19}
    finally:
        connector._http.close()


def test_poll_once_records_one_periodic_metric_fact(
    db_manager,
    db_session,
    monkeypatch,
):
    device = Device(
        name="Prometheus-Fact-Device",
        ip="192.0.2.42",
        snmp_enabled=True,
        snmp_community="test-read",
    )
    db_session.add(device)
    db_session.commit()

    connector = PrometheusConnector("http://prometheus.test")
    monkeypatch.setattr(connector, "sync_targets", lambda db: False)
    monkeypatch.setattr(
        connector,
        "_fetch_all_interfaces",
        lambda: {
            device.ip: {
                1: {"ifOperStatus": 1, "ifInErrors": 2, "ifOutErrors": 3},
                2: {"ifOperStatus": 2, "ifInErrors": 0, "ifOutErrors": 0},
            }
        },
    )
    monkeypatch.setattr(
        connector,
        "_fetch_device_uptimes",
        lambda: {device.ip: 7},
    )
    monkeypatch.setattr(connector_module, "get_db_manager", lambda: db_manager)

    try:
        connector.poll_once()
    finally:
        connector._http.close()

    sample = db_session.query(DeviceMetricSample).filter(
        DeviceMetricSample.device_id == device.id
    ).one()
    assert sample.source == "prometheus_snmp"
    assert sample.collection_status == "partial"
    assert sample.uptime_days == 7
    assert sample.interfaces_up == 1
    assert sample.interfaces_down == 1
    assert sample.interfaces_total == 2
    assert sample.total_errors == 5


def test_metric_fact_failure_preserves_interface_updates(
    db_manager,
    db_session,
    monkeypatch,
):
    device = Device(
        name="Prometheus-Fallback-Device",
        ip="192.0.2.43",
        snmp_enabled=True,
        snmp_community="test-read",
    )
    db_session.add(device)
    db_session.flush()
    interface = DeviceInterface(
        device_id=device.id,
        if_index=1,
        if_name="GigabitEthernet0/1",
        oper_status="down",
        admin_status="down",
    )
    db_session.add(interface)
    db_session.commit()

    connector = PrometheusConnector("http://prometheus.test")
    monkeypatch.setattr(connector, "sync_targets", lambda db: False)
    monkeypatch.setattr(
        connector,
        "_fetch_all_interfaces",
        lambda: {
            device.ip: {
                1: {
                    "ifOperStatus": 1,
                    "ifAdminStatus": 1,
                    "ifInErrors": 0,
                    "ifOutErrors": 0,
                }
            }
        },
    )
    monkeypatch.setattr(
        connector,
        "_fetch_device_uptimes",
        lambda: {device.ip: 1},
    )
    monkeypatch.setattr(connector_module, "get_db_manager", lambda: db_manager)

    def fail_metric_fact(*args, **kwargs):
        raise RuntimeError("metric fact table unavailable")

    monkeypatch.setattr(
        connector_module,
        "record_device_metric_sample",
        fail_metric_fact,
    )

    try:
        connector.poll_once()
    finally:
        connector._http.close()

    db_session.expire_all()
    refreshed = db_session.query(DeviceInterface).filter(
        DeviceInterface.id == interface.id
    ).one()
    assert refreshed.oper_status == "up"
    assert refreshed.admin_status == "up"
    assert refreshed.last_check is not None
    assert db_session.query(DeviceMetricSample).filter(
        DeviceMetricSample.device_id == device.id
    ).count() == 0