"""
Tests for GitConfigService
"""

import pytest
import tempfile
import os
from pathlib import Path
from app.shared.git_config_service import GitConfigService


class TestGitConfigService:
    @pytest.fixture
    def tmp_backup_dir(self):
        """Create a temporary backup directory with a file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_dir = Path(tmpdir) / "backups"
            backup_dir.mkdir()
            # Create a sample backup file
            device_dir = backup_dir / "SW-Test"
            device_dir.mkdir()
            config_file = device_dir / "config.cfg"
            config_file.write_text("!\nhostname SW-Test\n!\n")
            yield str(backup_dir)

    def test_init_creates_repo(self, tmp_backup_dir):
        """Test that initialization creates a git repo"""
        service = GitConfigService(backup_dir=tmp_backup_dir)
        assert service.available is True
        assert (Path(tmp_backup_dir) / ".git").exists()

    def test_commit_backup(self, tmp_backup_dir):
        """Test committing a backup file"""
        service = GitConfigService(backup_dir=tmp_backup_dir)
        backup_file = os.path.join(tmp_backup_dir, "SW-Test", "config.cfg")

        commit_hash = service.commit_backup("SW-Test", backup_file, operator="admin")
        assert commit_hash is not None
        assert len(commit_hash) == 40

    def test_commit_backup_with_change(self, tmp_backup_dir):
        """Test commit message includes change flag"""
        service = GitConfigService(backup_dir=tmp_backup_dir)
        backup_file = os.path.join(tmp_backup_dir, "SW-Test", "config.cfg")

        service.commit_backup("SW-Test", backup_file, has_change=True, operator="admin")
        history = service.get_history()
        assert len(history) >= 1
        assert "配置变更" in history[0]["message"]

    def test_get_history(self, tmp_backup_dir):
        """Test retrieving commit history"""
        service = GitConfigService(backup_dir=tmp_backup_dir)
        backup_file = os.path.join(tmp_backup_dir, "SW-Test", "config.cfg")

        service.commit_backup("SW-Test", backup_file, operator="admin")
        service.commit_backup("SW-Test", backup_file, operator="system")

        history = service.get_history()
        assert len(history) >= 2

    def test_get_history_filter_by_device(self, tmp_backup_dir):
        """Test filtering history by device name"""
        service = GitConfigService(backup_dir=tmp_backup_dir)
        backup_file = os.path.join(tmp_backup_dir, "SW-Test", "config.cfg")

        service.commit_backup("SW-Test", backup_file, operator="admin")
        service.commit_backup("Other-Device", backup_file, operator="admin")

        history = service.get_history(device_name="SW-Test")
        for entry in history:
            assert "SW-Test" in entry["message"]

    def test_get_history_limit(self, tmp_backup_dir):
        """Test history limit"""
        service = GitConfigService(backup_dir=tmp_backup_dir)
        backup_file = os.path.join(tmp_backup_dir, "SW-Test", "config.cfg")

        for i in range(10):
            service.commit_backup("SW-Test", backup_file, operator="admin")

        history = service.get_history(limit=3)
        assert len(history) <= 3

    def test_get_diff(self, tmp_backup_dir):
        """Test getting diff between commits"""
        service = GitConfigService(backup_dir=tmp_backup_dir)
        backup_file = os.path.join(tmp_backup_dir, "SW-Test", "config.cfg")

        service.commit_backup("SW-Test", backup_file, operator="admin")

        # Modify the file
        Path(backup_file).write_text("!\nhostname SW-Test-New\n!\n")
        commit2 = service.commit_backup("SW-Test", backup_file, has_change=True)

        diff = service.get_diff(commit2)
        assert diff["commit_hash"] == commit2[:8]
        assert "SW-Test-New" in diff.get("diff", "")

    def test_get_file_at_commit(self, tmp_backup_dir):
        """Test retrieving file content at a specific commit"""
        service = GitConfigService(backup_dir=tmp_backup_dir)
        backup_file = os.path.join(tmp_backup_dir, "SW-Test", "config.cfg")

        commit1 = service.commit_backup("SW-Test", backup_file)

        # Modify file
        Path(backup_file).write_text("modified content")
        commit2 = service.commit_backup("SW-Test", backup_file, has_change=True)

        content1 = service.get_file_at_commit("SW-Test/config.cfg", commit1)
        assert "hostname SW-Test" in content1

        content2 = service.get_file_at_commit("SW-Test/config.cfg", commit2)
        assert "modified content" in content2

    def test_rollback(self, tmp_backup_dir):
        """Test rolling back to a previous commit"""
        service = GitConfigService(backup_dir=tmp_backup_dir)
        backup_file = os.path.join(tmp_backup_dir, "SW-Test", "config.cfg")

        commit1 = service.commit_backup("SW-Test", backup_file)

        # Modify file
        Path(backup_file).write_text("modified content")
        service.commit_backup("SW-Test", backup_file, has_change=True)

        # Verify current content
        current = Path(backup_file).read_text()
        assert "modified content" in current

        # Rollback
        result = service.rollback(commit1)
        assert result is True

    def test_commit_nonexistent_file(self, tmp_backup_dir):
        """Test committing a file that doesn't exist"""
        service = GitConfigService(backup_dir=tmp_backup_dir)
        result = service.commit_backup("SW-Test", "/nonexistent/path/file.cfg")
        assert result is None

    def test_unavailable_service(self):
        """Test service with invalid directory"""
        service = GitConfigService(backup_dir="/nonexistent/path")
        # Should handle gracefully
        assert service.get_history() == []
