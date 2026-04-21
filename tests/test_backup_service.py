"""
Tests for backup_service.py
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models import Device, BackupRecord
from app.services.backup_service import list_backups, delete_backup
from app.exceptions import ResourceNotFoundException


class TestListBackups:
    def test_list_backups_empty(self, db_session):
        result = list_backups(db_session)
        assert result["total"] == 0
        assert result["items"] == []

    def test_list_backups_with_data(self, db_session):
        device = Device(name="sw-01", ip="10.0.0.1", status="online")
        db_session.add(device)
        db_session.commit()

        db_session.add(BackupRecord(
            device_id=device.id,
            device_name="sw-01",
            backup_file="/backups/sw-01.cfg",
            file_size=2048,
            md5_hash="abc123",
            has_change=False,
            operator="admin",
        ))
        db_session.commit()

        result = list_backups(db_session)
        assert result["total"] == 1
        item = result["items"][0]
        assert item["device_name"] == "sw-01"
        assert item["file_size"] == 2048
        assert item["md5_hash"] == "abc123"
        assert item["operator"] == "admin"

    def test_list_backups_filter_by_device(self, db_session):
        d1 = Device(name="sw-01", ip="10.0.0.1", status="online")
        d2 = Device(name="sw-02", ip="10.0.0.2", status="online")
        db_session.add_all([d1, d2])
        db_session.commit()

        db_session.add_all([
            BackupRecord(device_id=d1.id, device_name="sw-01", backup_file="/b/sw1.cfg", file_size=100),
            BackupRecord(device_id=d2.id, device_name="sw-02", backup_file="/b/sw2.cfg", file_size=200),
        ])
        db_session.commit()

        result = list_backups(db_session, device_id=d1.id)
        assert result["total"] == 1
        assert result["items"][0]["device_name"] == "sw-01"

    def test_list_backups_limit(self, db_session):
        device = Device(name="sw-01", ip="10.0.0.1", status="online")
        db_session.add(device)
        db_session.commit()

        for i in range(10):
            db_session.add(BackupRecord(
                device_id=device.id, device_name="sw-01",
                backup_file=f"/b/sw1-{i}.cfg", file_size=100,
            ))
        db_session.commit()

        result = list_backups(db_session, limit=3)
        assert result["total"] == 10  # total is full count
        assert len(result["items"]) == 3  # items are limited to 3

    def test_list_backups_sorted_by_time(self, db_session):
        device = Device(name="sw-01", ip="10.0.0.1", status="online")
        db_session.add(device)
        db_session.commit()

        now = datetime.utcnow()
        db_session.add_all([
            BackupRecord(device_id=device.id, device_name="sw-01", backup_file="/b/old.cfg", file_size=100,
                         backup_time=now - timedelta(days=5)),
            BackupRecord(device_id=device.id, device_name="sw-01", backup_file="/b/new.cfg", file_size=200,
                         backup_time=now),
        ])
        db_session.commit()

        result = list_backups(db_session)
        # Most recent first
        assert result["items"][0]["backup_file"] == "/b/new.cfg"

    def test_list_backups_with_null_fields(self, db_session):
        device = Device(name="sw-01", ip="10.0.0.1", status="online")
        db_session.add(device)
        db_session.commit()

        db_session.add(BackupRecord(
            device_id=device.id,
            device_name="sw-01",
            backup_file="/b/sw1.cfg",
            file_size=100,
        ))
        db_session.commit()

        result = list_backups(db_session)
        assert result["total"] == 1
        item = result["items"][0]
        assert item["md5_hash"] is None
        assert item["operator"] is None


class TestDeleteBackup:
    def test_delete_backup(self, db_session):
        device = Device(name="sw-01", ip="10.0.0.1", status="online")
        db_session.add(device)
        db_session.commit()

        record = BackupRecord(device_id=device.id, device_name="sw-01", backup_file="/b/sw1.cfg", file_size=100)
        db_session.add(record)
        db_session.commit()

        result = delete_backup(db_session, record.id)
        assert result["success"] is True

        with pytest.raises(ResourceNotFoundException):
            delete_backup(db_session, record.id)

    def test_delete_backup_not_found(self, db_session):
        with pytest.raises(ResourceNotFoundException):
            delete_backup(db_session, 999)
