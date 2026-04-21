"""
Tests for backup management router
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from app.shared.models import Device, BackupRecord, CredentialGroup


class TestBackupRecord:
    """Test backup record operations"""

    def test_create_backup_record(self, db_session, sample_device_data):
        """Test creating a backup record"""
        device = Device(**sample_device_data)
        db_session.add(device)
        db_session.commit()

        backup = BackupRecord(
            device_id=device.id,
            device_name=device.name,
            backup_file="./backups/test.cfg",
            file_size=1024,
            md5_hash="abc123",
            has_change=True,
            operator="test_user"
        )
        db_session.add(backup)
        db_session.commit()

        assert backup.id is not None
        assert backup.device_id == device.id
        assert backup.has_change is True

    def test_backup_record_timestamps(self, db_session, sample_device_data):
        """Test backup record has proper timestamps"""
        device = Device(**sample_device_data)
        db_session.add(device)
        db_session.commit()

        backup = BackupRecord(
            device_id=device.id,
            device_name=device.name,
            backup_file="./backups/test.cfg",
            file_size=512,
            md5_hash="def456",
        )
        db_session.add(backup)
        db_session.commit()

        assert backup.created_at is not None
        assert isinstance(backup.created_at, datetime)


class TestBackupDiff:
    """Test configuration diff functionality"""

    def test_detect_config_change(self, db_session, sample_device_data):
        """Test detecting configuration changes between backups"""
        device = Device(**sample_device_data)
        db_session.add(device)
        db_session.commit()

        old_config = """!
hostname SW-01
!
interface GigabitEthernet0/1
 description Old Description
!"""
        new_config = """!
hostname SW-01
!
interface GigabitEthernet0/1
 description New Description
!"""

        backup1 = BackupRecord(
            device_id=device.id,
            device_name=device.name,
            backup_file="./backups/old.cfg",
            file_size=len(old_config),
            md5_hash="old123",
            config_snapshot=old_config,
        )
        backup2 = BackupRecord(
            device_id=device.id,
            device_name=device.name,
            backup_file="./backups/new.cfg",
            file_size=len(new_config),
            md5_hash="new456",
            config_snapshot=new_config,
        )
        db_session.add_all([backup1, backup2])
        db_session.commit()

        # Old config should have old description
        assert "Old Description" in backup1.config_snapshot
        # New config should have new description
        assert "New Description" in backup2.config_snapshot


class TestBackupList:
    """Test listing backup records"""

    def test_list_backups_for_device(self, db_session, sample_device_data):
        """Test listing backups for a specific device"""
        device = Device(**sample_device_data)
        db_session.add(device)
        db_session.commit()

        for i in range(3):
            backup = BackupRecord(
                device_id=device.id,
                device_name=device.name,
                backup_file=f"./backups/backup_{i}.cfg",
                file_size=1000 + i * 100,
                md5_hash=f"hash{i}",
            )
            db_session.add(backup)
        db_session.commit()

        from app.features.backups.backup_service import list_backups
        result = list_backups(db=db_session, device_id=device.id)

        assert result["total"] == 3

    def test_list_backups_empty(self, db_session):
        """Test listing backups when none exist"""
        from app.features.backups.backup_service import list_backups
        result = list_backups(db=db_session, device_id=999)

        assert result["total"] == 0
        assert result["items"] == []


class TestBackupDelete:
    """Test deleting backup records"""

    def test_delete_backup_record(self, db_session, sample_device_data):
        """Test deleting a backup record"""
        device = Device(**sample_device_data)
        db_session.add(device)
        db_session.commit()

        backup = BackupRecord(
            device_id=device.id,
            device_name=device.name,
            backup_file="./backups/test.cfg",
            file_size=1024,
            md5_hash="abc123",
        )
        db_session.add(backup)
        db_session.commit()
        backup_id = backup.id

        from app.features.backups.backup_service import delete_backup
        result = delete_backup(db=db_session, backup_id=backup_id)

        assert result["success"] is True
        assert db_session.query(BackupRecord).filter(BackupRecord.id == backup_id).first() is None

    def test_delete_nonexistent_backup(self, db_session):
        """Test deleting a backup that doesn't exist"""
        from app.features.backups.backup_service import delete_backup
        from app.shared.exceptions import ResourceNotFoundException

        with pytest.raises(ResourceNotFoundException):
            delete_backup(db=db_session, backup_id=99999)
