"""
Tests for the configuration compliance service

These tests verify the compliance check logic against sample configurations.
"""

import pytest
from app.services.compliance_service import (
    ComplianceService,
    ComplianceCheckResult,
    ComplianceReport,
)


# Sample configurations for testing
GOOD_CONFIG = """
! Cisco IOS Configuration
hostname SW-Core-01
!
enable secret MyStr0ngP@ss!
!
ip ssh version 2
service password-encryption
!
ip access-list extended MGMT-ACL
 permit tcp 10.0.0.0 0.0.0.255 any eq 22
!
interface GigabitEthernet0/1
 description Uplink to Router
 switchport mode trunk
 switchport trunk native vlan 999
!
interface GigabitEthernet0/2
 description User Port
 shutdown
!
interface GigabitEthernet0/3
 description Unused
 shutdown
!
logging 10.0.0.100
ntp server 10.0.0.200
!
banner motd # WARNING: Authorized access only! #
!
snmp-server community MySnmpComm RO
!
"""

BAD_CONFIG = """
! Cisco IOS Configuration - Bad
hostname SW-Access-01
!
enable password weak123
!
no ip ssh version 2
!
interface GigabitEthernet0/1
 description Uplink
 switchport mode trunk
!
interface GigabitEthernet0/2
 description Access
!
interface GigabitEthernet0/3
 description Another Port
!
snmp-server community public RO
snmp-server community private RW
!
"""


class TestComplianceCheckResult:
    """Test the ComplianceCheckResult dataclass"""

    def test_result_creation(self):
        result = ComplianceCheckResult(
            check_id="SEC-001",
            check_name="Test Check",
            category="security",
            severity="high",
            passed=True,
            detail="Test passed",
            recommendation="N/A"
        )
        assert result.check_id == "SEC-001"
        assert result.passed is True


class TestComplianceReport:
    """Test the ComplianceReport dataclass"""

    def test_compliance_score_all_passed(self):
        report = ComplianceReport(
            device_name="SW-01",
            device_ip="192.168.1.1",
            total_checks=10,
            passed=10,
            failed=0,
        )
        assert report.compliance_score == 100.0

    def test_compliance_score_partial(self):
        report = ComplianceReport(
            device_name="SW-01",
            device_ip="192.168.1.1",
            total_checks=10,
            passed=7,
            failed=3,
        )
        assert report.compliance_score == 70.0

    def test_compliance_score_zero_checks(self):
        report = ComplianceReport(
            device_name="SW-01",
            device_ip="192.168.1.1",
        )
        assert report.compliance_score == 100.0

    def test_compliance_score_rounding(self):
        report = ComplianceReport(
            device_name="SW-01",
            device_ip="192.168.1.1",
            total_checks=3,
            passed=2,
            failed=1,
        )
        assert report.compliance_score == 66.7


class TestComplianceServiceGoodConfig:
    """Test compliance checks against a well-configured device"""

    def test_good_config_all_checks(self):
        service = ComplianceService()
        report = service.run_all_checks(
            config_text=GOOD_CONFIG,
            device_name="SW-Core-01",
            device_ip="192.168.1.1"
        )

        assert report.device_name == "SW-Core-01"
        assert report.total_checks == 10
        # Good config should pass most checks
        assert report.passed >= 8
        assert report.compliance_score >= 80.0

    def test_good_config_enable_secret(self):
        service = ComplianceService()
        result = service._check_enable_secret(GOOD_CONFIG.split("\n"), GOOD_CONFIG)
        assert result.passed is True
        assert "已配置" in result.detail

    def test_good_config_ssh_version(self):
        service = ComplianceService()
        result = service._check_ssh_version(GOOD_CONFIG.split("\n"), GOOD_CONFIG)
        assert result.passed is True

    def test_good_config_password_encryption(self):
        service = ComplianceService()
        result = service._check_password_encryption(GOOD_CONFIG.split("\n"), GOOD_CONFIG)
        assert result.passed is True

    def test_good_config_acl(self):
        service = ComplianceService()
        result = service._check_acl_management(GOOD_CONFIG.split("\n"), GOOD_CONFIG)
        assert result.passed is True

    def test_good_config_native_vlan(self):
        service = ComplianceService()
        result = service._check_native_vlan(GOOD_CONFIG.split("\n"), GOOD_CONFIG)
        assert result.passed is True
        assert "非默认值" in result.detail

    def test_good_config_logging(self):
        service = ComplianceService()
        result = service._check_logging_enabled(GOOD_CONFIG.split("\n"), GOOD_CONFIG)
        assert result.passed is True

    def test_good_config_ntp(self):
        service = ComplianceService()
        result = service._check_ntp_config(GOOD_CONFIG.split("\n"), GOOD_CONFIG)
        assert result.passed is True

    def test_good_config_banner(self):
        service = ComplianceService()
        result = service._check_banner(GOOD_CONFIG.split("\n"), GOOD_CONFIG)
        assert result.passed is True

    def test_good_config_snmp(self):
        service = ComplianceService()
        result = service._check_snmp_community(GOOD_CONFIG.split("\n"), GOOD_CONFIG)
        assert result.passed is True  # No default community


class TestComplianceServiceBadConfig:
    """Test compliance checks against a poorly configured device"""

    def test_bad_config_enable_secret(self):
        service = ComplianceService()
        result = service._check_enable_secret(BAD_CONFIG.split("\n"), BAD_CONFIG)
        assert result.passed is False  # Uses 'enable password', not 'enable secret'
        assert result.severity == "critical"

    def test_bad_config_ssh_version(self):
        service = ComplianceService()
        result = service._check_ssh_version(BAD_CONFIG.split("\n"), BAD_CONFIG)
        assert result.passed is False

    def test_bad_config_password_encryption(self):
        service = ComplianceService()
        result = service._check_password_encryption(BAD_CONFIG.split("\n"), BAD_CONFIG)
        assert result.passed is False

    def test_bad_config_acl(self):
        service = ComplianceService()
        result = service._check_acl_management(BAD_CONFIG.split("\n"), BAD_CONFIG)
        assert result.passed is False

    def test_bad_config_native_vlan(self):
        service = ComplianceService()
        result = service._check_native_vlan(BAD_CONFIG.split("\n"), BAD_CONFIG)
        assert result.passed is False  # No native vlan config at all

    def test_bad_config_logging(self):
        service = ComplianceService()
        result = service._check_logging_enabled(BAD_CONFIG.split("\n"), BAD_CONFIG)
        assert result.passed is False

    def test_bad_config_ntp(self):
        service = ComplianceService()
        result = service._check_ntp_config(BAD_CONFIG.split("\n"), BAD_CONFIG)
        assert result.passed is False

    def test_bad_config_banner(self):
        service = ComplianceService()
        result = service._check_banner(BAD_CONFIG.split("\n"), BAD_CONFIG)
        assert result.passed is False

    def test_bad_config_snmp(self):
        service = ComplianceService()
        result = service._check_snmp_community(BAD_CONFIG.split("\n"), BAD_CONFIG)
        assert result.passed is False  # Uses default public/private
        assert result.severity == "critical"

    def test_bad_config_score_low(self):
        service = ComplianceService()
        report = service.run_all_checks(
            config_text=BAD_CONFIG,
            device_name="SW-Access-01",
            device_ip="192.168.1.2"
        )
        assert report.failed >= 7
        assert report.compliance_score < 50.0


class TestComplianceServiceEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_config(self):
        service = ComplianceService()
        report = service.run_all_checks(
            config_text="",
            device_name="SW-01",
            device_ip="192.168.1.1"
        )
        assert report.total_checks == 10
        # All checks should fail on empty config (except unused_ports)
        assert report.passed <= 2

    def test_config_with_no_interfaces(self):
        service = ComplianceService()
        config = "hostname Test-Switch\nenable secret test123\n"
        result = service._check_unused_ports(config.split("\n"), config)
        assert result.passed is True  # No interfaces = pass

    def test_report_has_correct_device_info(self):
        service = ComplianceService()
        report = service.run_all_checks(
            config_text="hostname MyDevice\n",
            device_name="TestDevice",
            device_ip="10.0.0.1"
        )
        assert report.device_name == "TestDevice"
        assert report.device_ip == "10.0.0.1"

    def test_checks_are_registered(self):
        service = ComplianceService()
        assert len(service.checks) == 10
        assert "SEC-001" in service.checks
        assert "SEC-010" in service.checks
