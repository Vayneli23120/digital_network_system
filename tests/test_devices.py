"""
Tests for device management router
"""

import pytest
from datetime import datetime
from app.models import Device


class TestDeviceList:
    """Test device listing and filtering"""

    def test_list_devices_empty(self, db_session):
        """Test listing devices when database is empty"""
        from app.services.device_service import list_devices

        result = list_devices(db=db_session, status=None, role=None)
        assert result["total"] == 0
        assert result["items"] == []

    def test_list_devices_with_data(self, db_session, sample_device_data):
        """Test listing devices with sample data"""
        device = Device(**sample_device_data)
        db_session.add(device)
        db_session.commit()

        from app.services.device_service import list_devices
        result = list_devices(db=db_session, status=None, role=None)

        assert result["total"] == 1
        assert result["items"][0]["name"] == "SW-Core-01"
        assert result["items"][0]["ip"] == "192.168.1.1"

    def test_list_devices_filter_by_status(self, db_session, sample_device_data):
        """Test filtering devices by status"""
        device = Device(**sample_device_data)
        db_session.add(device)
        db_session.commit()

        from app.services.device_service import list_devices
        result = list_devices(db=db_session, status="online", role=None)

        assert result["total"] == 1
        assert result["items"][0]["status"] == "online"

        result_offline = list_devices(db=db_session, status="offline", role=None)
        assert result_offline["total"] == 0

    def test_list_devices_filter_by_role(self, db_session, sample_device_data):
        """Test filtering devices by role"""
        device = Device(**sample_device_data)
        db_session.add(device)
        db_session.commit()

        from app.services.device_service import list_devices
        result = list_devices(db=db_session, status=None, role="core")

        assert result["total"] == 1
        assert result["items"][0]["role"] == "core"

        result_access = list_devices(db=db_session, status=None, role="access")
        assert result_access["total"] == 0


class TestDeviceCreate:
    """Test device creation"""

    def test_create_device(self, db_session, sample_device_data):
        """Test creating a new device"""
        from app.services.device_service import create_device

        # Remove id if present
        data = {k: v for k, v in sample_device_data.items() if k != "id"}
        result = create_device(db=db_session, device_data=data)

        assert result["name"] == "SW-Core-01"
        assert result["ip"] == "192.168.1.1"
        assert "id" in result

    def test_create_device_duplicate_name(self, db_session, sample_device_data):
        """Test creating device with duplicate name raises error"""
        from app.services.device_service import create_device
        from app.exceptions import ConflictException

        device = Device(**sample_device_data)
        db_session.add(device)
        db_session.commit()

        data = {k: v for k, v in sample_device_data.items() if k != "id"}

        with pytest.raises(ConflictException) as exc_info:
            create_device(db=db_session, device_data=data)

        assert "already exists" in str(exc_info.value.message)


class TestDeviceGet:
    """Test getting a single device"""

    def test_get_device(self, db_session, sample_device_data):
        """Test getting a device by ID"""
        from app.services.device_service import get_device

        device = Device(**sample_device_data)
        db_session.add(device)
        db_session.commit()

        result = get_device(db=db_session, device_id=device.id)

        assert result["name"] == "SW-Core-01"

    def test_get_device_not_found(self, db_session):
        """Test getting non-existent device raises error"""
        from app.services.device_service import get_device
        from app.exceptions import ResourceNotFoundException

        with pytest.raises(ResourceNotFoundException):
            get_device(db=db_session, device_id=99999)


class TestDeviceUpdate:
    """Test device updates"""

    def test_update_device(self, db_session, sample_device_data):
        """Test updating device fields"""
        from app.services.device_service import update_device

        device = Device(**sample_device_data)
        db_session.add(device)
        db_session.commit()

        update_data = {"location": "Building B, Floor 2", "status": "offline"}
        result = update_device(db=db_session, device_id=device.id, update_data=update_data)

        assert result["location"] == "Building B, Floor 2"
        assert result["status"] == "offline"

    def test_update_device_not_found(self, db_session):
        """Test updating non-existent device raises error"""
        from app.services.device_service import update_device
        from app.exceptions import ResourceNotFoundException

        with pytest.raises(ResourceNotFoundException):
            update_device(db=db_session, device_id=99999, update_data={"status": "offline"})


class TestDeviceDelete:
    """Test device deletion"""

    def test_delete_device(self, db_session, sample_device_data):
        """Test deleting a device"""
        from app.services.device_service import delete_device

        device = Device(**sample_device_data)
        db_session.add(device)
        db_session.commit()
        device_id = device.id

        result = delete_device(db=db_session, device_id=device_id)

        assert result["success"] is True
        assert db_session.query(Device).filter(Device.id == device_id).first() is None

    def test_delete_device_not_found(self, db_session):
        """Test deleting non-existent device raises error"""
        from app.services.device_service import delete_device
        from app.exceptions import ResourceNotFoundException

        with pytest.raises(ResourceNotFoundException):
            delete_device(db=db_session, device_id=99999)


class TestDeviceBatchOperations:
    """Test batch operations on devices"""

    def test_batch_update_status(self, db_session, sample_device_data):
        """Test batch updating device status"""
        from app.services.device_service import batch_update_devices

        # Create multiple devices
        devices = []
        for i in range(3):
            data = sample_device_data.copy()
            data["name"] = f"SW-0{i+1}"
            devices.append(Device(**data))

        for d in devices:
            db_session.add(d)
        db_session.commit()

        device_ids = [d.id for d in devices]
        result = batch_update_devices(
            db=db_session,
            device_ids=device_ids,
            update_data={"status": "offline"}
        )

        assert result["updated"] == 3
        for device in db_session.query(Device).all():
            assert device.status == "offline"
