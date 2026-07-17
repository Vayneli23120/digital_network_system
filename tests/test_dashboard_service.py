"""
Tests for dashboard_service.py
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.shared.models import Device, BackupRecord, FaultRecord, MaintenanceRecord
from app.features.dashboard.dashboard_service import get_dashboard_summary, get_fault_trend


class TestGetDashboardSummary:
    def test_summary_empty_database(self, db_session):
        result = get_dashboard_summary(db_session)
        assert result["devices"]["total"] == 0
        assert result["devices"]["online"] == 0
        assert result["faults"]["count_30days"] == 0
        assert result["costs"]["month_total"] == 0

    def test_summary_device_counts(self, db_session):
        devices = [
            Device(name="core-01", ip="10.0.0.1", role="core", status="online"),
            Device(name="dist-01", ip="10.0.0.2", role="distribution", status="online"),
            Device(name="access-01", ip="10.0.0.3", role="access", status="offline"),
            Device(name="maint-01", ip="10.0.0.4", role="access", status="maintenance"),
        ]
        for d in devices:
            db_session.add(d)
        db_session.commit()

        result = get_dashboard_summary(db_session)
        assert result["devices"]["total"] == 4
        assert result["devices"]["online"] == 2
        assert result["devices"]["offline"] == 1
        assert result["devices"]["maintenance"] == 1

    def test_summary_recent_backups(self, db_session):
        device = Device(name="sw-01", ip="10.0.0.1", status="online")
        db_session.add(device)
        db_session.commit()

        for i in range(12):
            db_session.add(BackupRecord(
                device_id=device.id,
                device_name="sw-01",
                backup_file=f"/backups/sw-01-{i}.cfg",
                file_size=1024,
                has_change=(i % 3 == 0),
            ))
        db_session.commit()

        result = get_dashboard_summary(db_session)
        assert len(result["backups"]["recent"]) == 10  # limited to 10

    def test_summary_fault_counts(self, db_session):
        device = Device(name="sw-01", ip="10.0.0.1", status="online")
        db_session.add(device)
        db_session.commit()

        now = datetime.utcnow()
        faults = [
            FaultRecord(device_id=device.id, device_name="sw-01", fault_no="F-001",
                        severity="critical", created_at=now - timedelta(days=1)),
            FaultRecord(device_id=device.id, device_name="sw-01", fault_no="F-002",
                        severity="major", created_at=now - timedelta(days=5)),
            FaultRecord(device_id=device.id, device_name="sw-01", fault_no="F-003",
                        severity="minor", created_at=now - timedelta(days=40)),  # outside 30d
        ]
        for f in faults:
            db_session.add(f)
        db_session.commit()

        result = get_dashboard_summary(db_session)
        assert result["faults"]["count_30days"] == 2  # only 2 in last 30 days
        assert result["faults"]["critical_count"] == 1

    def test_summary_cost_stats(self, db_session):
        device = Device(name="sw-01", ip="10.0.0.1", status="online")
        db_session.add(device)
        db_session.commit()

        now = datetime.utcnow()
        maintenances = [
            MaintenanceRecord(device_id=device.id, device_name="sw-01", maint_no="M-001",
                              parts_cost=100.0, labor_cost=50.0, created_at=now),
            MaintenanceRecord(device_id=device.id, device_name="sw-01", maint_no="M-002",
                              parts_cost=200.0, labor_cost=100.0, created_at=now),
        ]
        for m in maintenances:
            db_session.add(m)
        db_session.commit()

        result = get_dashboard_summary(db_session)
        assert result["costs"]["month_maintenance"] == 300.0
        assert result["costs"]["month_labor"] == 150.0
        assert result["costs"]["month_total"] == 450.0


class TestGetFaultTrend:
    def test_fault_trend_7d(self, db_session):
        device = Device(name="sw-01", ip="10.0.0.1", status="online")
        db_session.add(device)
        db_session.commit()

        now = datetime.utcnow()
        for i in range(3):
            db_session.add(FaultRecord(
                device_id=device.id, device_name="sw-01", fault_no=f"F-00{i}",
                severity="minor", created_at=now - timedelta(days=i),
            ))
        db_session.commit()

        result = get_fault_trend(db_session, time_range="7d")
        assert "labels" in result
        assert "values" in result
        assert result["total"] == 3
        assert "by_severity" in result

    def test_fault_trend_30d(self, db_session):
        device = Device(name="sw-01", ip="10.0.0.1", status="online")
        db_session.add(device)
        db_session.commit()

        now = datetime.utcnow()
        for i in range(10):
            db_session.add(FaultRecord(
                device_id=device.id, device_name="sw-01", fault_no=f"F-0{i:02d}",
                severity="major" if i % 2 == 0 else "minor",
                created_at=now - timedelta(days=i * 2),
            ))
        db_session.commit()

        result = get_fault_trend(db_session, time_range="30d")
        assert result["total"] == 10
        assert len(result["labels"]) == 31  # 30 天 + 今天（含当日）

    def test_fault_trend_includes_today(self, db_session):
        device = Device(name="sw-today", ip="10.0.0.9", status="online")
        db_session.add(device)
        db_session.commit()

        now = datetime.utcnow()
        for i in range(2):
            db_session.add(FaultRecord(
                device_id=device.id, device_name="sw-today", fault_no=f"F-TODAY-{i}",
                severity="major", created_at=now,
            ))
        db_session.commit()

        result = get_fault_trend(db_session, time_range="30d")
        today_label = now.strftime("%m-%d")
        assert today_label in result["labels"]
        idx = result["labels"].index(today_label)
        assert result["values"][idx] == 2

    def test_fault_trend_custom_range(self, db_session):
        device = Device(name="sw-01", ip="10.0.0.1", status="online")
        db_session.add(device)
        db_session.commit()

        now = datetime.utcnow()
        for i in range(1, 5):
            db_session.add(FaultRecord(
                device_id=device.id, device_name="sw-01", fault_no=f"F-00{i}",
                severity="warning", created_at=now - timedelta(days=i),
            ))
        db_session.commit()

        end = now.strftime("%Y-%m-%d")
        start = (now - timedelta(days=5)).strftime("%Y-%m-%d")
        result = get_fault_trend(db_session, time_range="custom", start_date=start, end_date=end)
        assert result["total"] == 4  # day-by-day loop excludes end date boundary

    def test_fault_trend_invalid_date(self, db_session):
        result = get_fault_trend(db_session, time_range="custom", start_date="invalid", end_date="bad")
        assert "error" in result
        assert "日期格式错误" in result["error"]

    def test_fault_trend_empty(self, db_session):
        result = get_fault_trend(db_session, time_range="7d")
        assert result["total"] == 0
        assert len(result["labels"]) == 8  # 7 天 + 今天

    def test_fault_trend_by_severity(self, db_session):
        device = Device(name="sw-01", ip="10.0.0.1", status="online")
        db_session.add(device)
        db_session.commit()

        now = datetime.utcnow()
        # Spread faults across days that fall within the 7d query window (now-7d < created_at < now)
        severities = ["critical", "major", "minor", "warning"]
        for i, sev in enumerate(severities):
            db_session.add(FaultRecord(
                device_id=device.id, device_name="sw-01", fault_no=f"F-00{i}",
                severity=sev, created_at=now - timedelta(days=i + 1),  # day 1-4 before now
            ))
        db_session.commit()

        result = get_fault_trend(db_session, time_range="7d")
        assert "by_severity" in result
        total_critical = sum(
            v.get("critical", 0) for v in result["by_severity"].values()
        )
        assert total_critical == 1

    def test_fault_trend_default_range(self, db_session):
        result = get_fault_trend(db_session)
        assert "labels" in result
        # Default is 30d（含今天）
        assert len(result["labels"]) == 31
