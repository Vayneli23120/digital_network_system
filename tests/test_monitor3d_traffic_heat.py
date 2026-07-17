"""
Tests for Monitor3D traffic heat-layer helpers.
"""

from datetime import datetime, timedelta

from app.services.monitor3d_traffic_heat import (
    build_traffic_heat_items,
    classify_traffic_heat,
    dominant_direction,
)
from app.shared.models import Device, DeviceInterface


def test_classify_traffic_heat_thresholds():
    now = datetime.utcnow()

    assert classify_traffic_heat(10, 15, "up", now, now)["level"] == "low"
    assert classify_traffic_heat(25, 40, "up", now, now)["level"] == "normal"
    assert classify_traffic_heat(65, 20, "up", now, now)["level"] == "high"
    critical = classify_traffic_heat(20, 85, "up", now, now)

    assert critical["level"] == "critical"
    assert critical["width"] == 6
    assert critical["particle_speed"] > 1


def test_classify_traffic_heat_down_overrides_utilization():
    heat = classify_traffic_heat(95, 90, "down", datetime.utcnow(), datetime.utcnow())

    assert heat["level"] == "down"
    assert heat["color"] == "#ef4444"
    assert heat["particle_speed"] == 0


def test_classify_traffic_heat_unreachable_device_is_down():
    now = datetime.utcnow()
    # 设备不可达：接口 oper_status 还是旧的 up、采样也还新鲜，
    # 但必须直接判为 down（中断），而不是空闲。
    heat = classify_traffic_heat(0, 0, "up", now, now, device_reachability="unreachable")

    assert heat["level"] == "down"
    assert heat["color"] == "#ef4444"
    assert heat["stale"] is False


def test_classify_traffic_heat_marks_stale_samples():
    now = datetime.utcnow()
    heat = classify_traffic_heat(90, 5, "up", now - timedelta(minutes=11), now)

    assert heat["level"] == "stale"
    assert heat["utilization"] == 0.0
    assert heat["color"] == "#64748b"
    assert heat["width"] == 1
    assert heat["particle_speed"] == 0
    assert heat["stale"] is True


def test_dominant_direction():
    assert dominant_direction(200, 100) == "in"
    assert dominant_direction(100, 200) == "out"
    assert dominant_direction(100, 100) == "balanced"


def test_build_traffic_heat_items_filters_monitored_interfaces_and_sorts(db_session):
    now = datetime.utcnow()
    core = Device(name="Core-01", ip="10.0.0.1", status="online")
    access = Device(name="Access-01", ip="10.0.0.2", status="online")
    ignored = Device(name="Ignored-01", ip="10.0.0.3", status="online")
    db_session.add_all([core, access, ignored])
    db_session.commit()

    core_iface = DeviceInterface(
        device_id=core.id,
        if_index=48,
        if_name="Gi1/0/48",
        oper_status="up",
        is_uplink=True,
        monitored=True,
        peer_device_id=access.id,
        peer_device_name=access.name,
        last_in_bps=1000,
        last_out_bps=2000,
        last_in_util=25,
        last_out_util=88,
        last_sample_at=now,
    )
    access_iface = DeviceInterface(
        device_id=access.id,
        if_index=1,
        if_name="Gi1/0/1",
        oper_status="up",
        monitored=True,
        last_in_bps=100,
        last_out_bps=50,
        last_in_util=15,
        last_out_util=10,
        last_sample_at=now,
    )
    ignored_iface = DeviceInterface(
        device_id=ignored.id,
        if_index=1,
        if_name="Gi1/0/1",
        oper_status="up",
        monitored=False,
        last_in_util=99,
        last_out_util=99,
        last_sample_at=now,
    )
    db_session.add_all([core_iface, access_iface, ignored_iface])
    db_session.commit()

    items = build_traffic_heat_items(db_session)

    assert [item["device_id"] for item in items] == [core.id, access.id]
    assert items[0]["level"] == "critical"
    assert items[0]["direction"] == "out"
    assert items[0]["is_uplink"] is True
    assert items[1]["level"] == "low"


def test_build_traffic_heat_items_marks_unreachable_device_down(db_session):
    now = datetime.utcnow()
    # 设备被中断：reachability=unreachable，但接口仍保留旧的 up 与新鲜采样。
    offline = Device(name="Offline-01", ip="10.0.2.1", status="online", reachability="unreachable")
    db_session.add(offline)
    db_session.commit()
    db_session.add(DeviceInterface(
        device_id=offline.id,
        if_index=1,
        if_name="Gi1/0/1",
        oper_status="up",
        is_uplink=True,
        monitored=True,
        last_in_util=0,
        last_out_util=0,
        last_sample_at=now,
    ))
    db_session.commit()

    items = build_traffic_heat_items(db_session, [offline.id])

    assert len(items) == 1
    assert items[0]["level"] == "down"


def test_build_traffic_heat_items_can_scope_to_floor_plan_devices(db_session):
    now = datetime.utcnow()
    in_plan = Device(name="InPlan-01", ip="10.0.1.1", status="online")
    outside_plan = Device(name="Outside-01", ip="10.0.1.2", status="online")
    db_session.add_all([in_plan, outside_plan])
    db_session.commit()
    db_session.add_all([
        DeviceInterface(
            device_id=in_plan.id,
            if_index=1,
            if_name="Gi1/0/1",
            oper_status="up",
            monitored=True,
            last_in_util=30,
            last_out_util=20,
            last_sample_at=now,
        ),
        DeviceInterface(
            device_id=outside_plan.id,
            if_index=1,
            if_name="Gi1/0/1",
            oper_status="up",
            monitored=True,
            last_in_util=90,
            last_out_util=90,
            last_sample_at=now,
        ),
    ])
    db_session.commit()

    items = build_traffic_heat_items(db_session, [in_plan.id])

    assert len(items) == 1
    assert items[0]["device_id"] == in_plan.id
    assert items[0]["level"] == "normal"
