"""
Tests for device_service.py
"""

import pytest
from sqlalchemy.orm import Session

from app.models import Device
from app.services.device_service import (
    list_devices, create_device, get_device,
    update_device, delete_device, batch_update_devices,
)
from app.exceptions import ResourceNotFoundException, ConflictException


class TestListDevices:
    def test_list_devices_empty(self, db_session):
        result = list_devices(db_session)
        assert result["total"] == 0
        assert result["items"] == []

    def test_list_devices_with_data(self, db_session, sample_device_data):
        create_device(db_session, sample_device_data)
        result = list_devices(db_session)
        assert result["total"] == 1
        assert result["items"][0]["name"] == "SW-Core-01"
        assert result["items"][0]["status"] == "online"

    def test_list_devices_filter_by_status(self, db_session):
        create_device(db_session, {"name": "online-01", "ip": "10.0.0.1", "status": "online"})
        create_device(db_session, {"name": "offline-01", "ip": "10.0.0.2", "status": "offline"})
        create_device(db_session, {"name": "online-02", "ip": "10.0.0.3", "status": "online"})

        result = list_devices(db_session, status="online")
        assert result["total"] == 2

    def test_list_devices_filter_by_role(self, db_session):
        create_device(db_session, {"name": "core-01", "ip": "10.0.0.1", "role": "core"})
        create_device(db_session, {"name": "access-01", "ip": "10.0.0.2", "role": "access"})

        result = list_devices(db_session, role="core")
        assert result["total"] == 1
        assert result["items"][0]["name"] == "core-01"

    def test_list_devices_with_null_last_backup(self, db_session, sample_device_data):
        create_device(db_session, sample_device_data)
        result = list_devices(db_session)
        assert result["items"][0]["last_backup_time"] is None


class TestCreateDevice:
    def test_create_device(self, db_session, sample_device_data):
        result = create_device(db_session, sample_device_data)
        assert "id" in result
        assert result["name"] == "SW-Core-01"
        assert result["ip"] == "192.168.1.1"
        assert result["vendor"] == "Cisco"

    def test_create_device_duplicate_name(self, db_session, sample_device_data):
        create_device(db_session, sample_device_data)
        with pytest.raises(ConflictException) as exc_info:
            create_device(db_session, sample_device_data)
        assert "already exists" in str(exc_info.value)

    def test_create_device_all_fields(self, db_session):
        data = {
            "name": "full-device",
            "ip": "10.0.0.1",
            "model": "C9300",
            "serial_number": "SN123",
            "location": "Room 101",
            "role": "core",
            "status": "online",
            "vendor": "Cisco",
            "purchase_cost": 5000.00,
            "credential_group": "admin",
        }
        result = create_device(db_session, data)
        assert result["model"] == "C9300"
        assert result["serial_number"] == "SN123"
        assert result["location"] == "Room 101"


class TestGetDevice:
    def test_get_device_success(self, db_session, sample_device_data):
        create_result = create_device(db_session, sample_device_data)
        result = get_device(db_session, create_result["id"])
        assert result["name"] == "SW-Core-01"
        assert result["ip"] == "192.168.1.1"
        assert result["status"] == "online"
        assert result["credential_group"] == "default"

    def test_get_device_not_found(self, db_session):
        with pytest.raises(ResourceNotFoundException):
            get_device(db_session, 999)

    def test_get_device_with_purchase_info(self, db_session):
        create_device(db_session, {
            "name": "costly-switch",
            "ip": "10.0.0.1",
            "purchase_cost": 12345.67,
        })
        result = get_device(db_session, 1)
        assert result["purchase_cost"] == 12345.67


class TestUpdateDevice:
    def test_update_device(self, db_session, sample_device_data):
        create_result = create_device(db_session, sample_device_data)
        result = update_device(db_session, create_result["id"], {"status": "offline"})
        assert result["message"] == "更新成功"

        updated = get_device(db_session, create_result["id"])
        assert updated["status"] == "offline"

    def test_update_device_not_found(self, db_session):
        with pytest.raises(ResourceNotFoundException):
            update_device(db_session, 999, {"status": "offline"})

    def test_update_multiple_fields(self, db_session, sample_device_data):
        create_result = create_device(db_session, sample_device_data)
        update_device(db_session, create_result["id"], {
            "status": "maintenance",
            "location": "Building B",
            "role": "distribution",
        })
        updated = get_device(db_session, create_result["id"])
        assert updated["status"] == "maintenance"
        assert updated["location"] == "Building B"
        assert updated["role"] == "distribution"

    def test_update_name(self, db_session, sample_device_data):
        create_result = create_device(db_session, sample_device_data)
        update_device(db_session, create_result["id"], {"name": "renamed-sw"})
        updated = get_device(db_session, create_result["id"])
        assert updated["name"] == "renamed-sw"


class TestDeleteDevice:
    def test_delete_device(self, db_session, sample_device_data):
        create_result = create_device(db_session, sample_device_data)
        result = delete_device(db_session, create_result["id"])
        assert result["success"] is True

        with pytest.raises(ResourceNotFoundException):
            get_device(db_session, create_result["id"])

    def test_delete_device_not_found(self, db_session):
        with pytest.raises(ResourceNotFoundException):
            delete_device(db_session, 999)


class TestBatchUpdateDevices:
    def test_batch_update_status(self, db_session):
        create_device(db_session, {"name": "sw-01", "ip": "10.0.0.1", "status": "online"})
        create_device(db_session, {"name": "sw-02", "ip": "10.0.0.2", "status": "online"})
        create_device(db_session, {"name": "sw-03", "ip": "10.0.0.3", "status": "online"})

        result = batch_update_devices(db_session, [1, 2], {"status": "offline"})
        assert result["updated"] == 2

        assert get_device(db_session, 1)["status"] == "offline"
        assert get_device(db_session, 2)["status"] == "offline"
        assert get_device(db_session, 3)["status"] == "online"

    def test_batch_update_empty_list(self, db_session):
        result = batch_update_devices(db_session, [], {"status": "offline"})
        assert result["updated"] == 0
