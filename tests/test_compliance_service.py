"""
Tests for the configuration compliance service

批次四把 compliance 重写为「规则库 + ADK AI」架构：`ComplianceService` 不再有
`run_all_checks` / `_check_*` / `service.checks`，统一走 `audit_config(...)`。
本文件覆盖新架构的确定性部分——基础审核（`use_ai=False`，对内置规则做关键词
匹配）、AI 结果解析、配置行分析、报告打分——不调用真实 AI/ADK。
"""

import pytest
from app.features.compliance.compliance_service import (
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


@pytest.fixture
def seeded_db(monkeypatch, db_manager):
    """把 database._db_manager 单例指向测试库。

    构造 ComplianceService 时 `__init__` 经 `init_builtin_rules()` 用 get_db()
    把 10 条内置规则种子进测试库；`audit_config` 内部同样用 get_db() 读取同一库。
    （沿用 tests/test_batch1_regressions.py 的既有模式。）
    """
    import app.shared.database as database_module

    monkeypatch.setattr(database_module, "_db_manager", db_manager)
    return db_manager


def _result_by_id(report: ComplianceReport, check_id: str) -> ComplianceCheckResult:
    return next(r for r in report.results if r.check_id == check_id)


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


class TestBasicAudit:
    """基础审核（use_ai=False，对内置规则做关键词匹配）"""

    @pytest.mark.asyncio
    async def test_good_config_all_checks(self, seeded_db):
        service = ComplianceService()
        report = await service.audit_config(
            GOOD_CONFIG, device_name="SW-Core-01", device_ip="192.168.1.1", use_ai=False
        )

        assert report.device_name == "SW-Core-01"
        assert report.device_ip == "192.168.1.1"
        assert report.total_checks == 10
        # GOOD_CONFIG 缺 SEC-004（access-class 管理平面访问控制），其余 9 条通过
        assert report.passed == 9
        assert report.compliance_score == 90.0

    @pytest.mark.asyncio
    async def test_good_config_per_rule(self, seeded_db):
        service = ComplianceService()
        report = await service.audit_config(GOOD_CONFIG, use_ai=False)

        passed_ids = {
            "SEC-001", "SEC-002", "SEC-003", "SEC-005",
            "SEC-006", "SEC-007", "SEC-008", "SEC-009", "SEC-010",
        }
        for check_id in passed_ids:
            assert _result_by_id(report, check_id).passed is True, check_id

        assert _result_by_id(report, "SEC-004").passed is False
        assert _result_by_id(report, "SEC-004").severity == "high"

    @pytest.mark.asyncio
    async def test_bad_config_all_checks(self, seeded_db):
        service = ComplianceService()
        report = await service.audit_config(
            BAD_CONFIG, device_name="SW-Access-01", device_ip="192.168.1.2", use_ai=False
        )

        # 基础审核为关键词子串匹配：BAD_CONFIG 的 "no ip ssh version 2" 含
        # "ip ssh version 2"、"snmp-server community public" 含 "snmp-server
        # community"，SEC-002 / SEC-010 因此误判为通过（真实 AI 路径不受影响）。
        assert report.total_checks == 10
        assert report.failed == 8
        assert report.compliance_score == 20.0

    @pytest.mark.asyncio
    async def test_bad_config_per_rule(self, seeded_db):
        service = ComplianceService()
        report = await service.audit_config(BAD_CONFIG, use_ai=False)

        failed_ids = {
            "SEC-001", "SEC-003", "SEC-004", "SEC-005",
            "SEC-006", "SEC-007", "SEC-008", "SEC-009",
        }
        for check_id in failed_ids:
            assert _result_by_id(report, check_id).passed is False, check_id

        assert _result_by_id(report, "SEC-001").severity == "critical"

    @pytest.mark.asyncio
    async def test_empty_config(self, seeded_db):
        service = ComplianceService()
        report = await service.audit_config(
            "", device_name="SW-01", device_ip="192.168.1.1", use_ai=False
        )
        assert report.total_checks == 10
        assert report.passed == 0
        assert report.compliance_score == 0.0

    @pytest.mark.asyncio
    async def test_report_has_correct_device_info(self, seeded_db):
        service = ComplianceService()
        report = await service.audit_config(
            "hostname MyDevice\n", device_name="TestDevice", device_ip="10.0.0.1", use_ai=False
        )
        assert report.device_name == "TestDevice"
        assert report.device_ip == "10.0.0.1"

    def test_checks_are_registered(self, seeded_db):
        """构造 ComplianceService 触发 init_builtin_rules() 种子后，get_all_rules_for_audit() 返回 10 条 SEC-001..SEC-010"""
        from app.features.compliance.builtin_rules import get_all_rules_for_audit

        ComplianceService()  # __init__ 里 init_builtin_rules() 把内置规则种子进测试库
        rules = get_all_rules_for_audit()
        assert len(rules) == 10
        rule_ids = {r["rule_id"] for r in rules}
        assert "SEC-001" in rule_ids
        assert "SEC-010" in rule_ids

    def test_config_without_shutdown_fails_sec005(self, seeded_db):
        """基础审核无法区分「无接口」与「未 shutdown 的接口」：SEC-005 只做
        shutdown 关键词匹配，无 shutdown 即失败（新架构语义，原 _check_unused_ports
        的「无接口=通过」不再成立）。"""
        service = ComplianceService()
        report = ComplianceReport(device_name="SW-01")
        rules = [{
            "rule_id": "SEC-005", "name": "未使用端口管理", "category": "security",
            "severity": "medium", "pattern": "shutdown", "recommendation": "",
        }]

        service._run_basic_audit(report, "hostname Test-Switch\nenable secret test123\n", rules)

        assert report.total_checks == 1
        assert report.results[0].passed is False
        assert report.passed == 0


class TestAiResultParsing:
    """AI 结果解析与配置行分析（不调用真实 ADK）"""

    def test_parse_ai_result_dict(self, seeded_db):
        service = ComplianceService()
        report = ComplianceReport(device_name="SW-01")
        rules = [{
            "rule_id": "SEC-001", "name": "特权模式密码保护", "category": "security",
            "severity": "critical", "pattern": "enable secret",
            "recommendation": "enable secret <strong-password>",
        }]
        ai_result = {
            "overall_score": 88,
            "ai_insights": "整体良好",
            "results": [{
                "rule_id": "SEC-001", "rule_name": "特权模式密码保护", "passed": True,
                "detail": "已配置", "line_numbers": [3], "severity": "critical",
            }],
        }

        service._parse_ai_result(report, ai_result, rules)

        assert report.ai_score == 88
        assert report.total_checks == 1
        assert report.passed == 1
        assert report.failed == 0
        assert report.compliance_score == 100.0
        assert report.results[0].line_numbers == [3]
        assert report.results[0].detail == "已配置"

    def test_generate_config_analysis_flags_issue_lines(self, seeded_db):
        service = ComplianceService()
        report = ComplianceReport(device_name="SW-01")
        report.results.append(ComplianceCheckResult(
            check_id="SEC-001", check_name="x", category="security",
            severity="critical", passed=False, detail="未发现", line_numbers=[2],
        ))

        service._generate_config_analysis(report, "hostname A\nenable password weak\n")

        assert report.config_analysis[1]["line_number"] == 2
        assert any(i["rule_id"] == "SEC-001" for i in report.config_analysis[1]["issues"])
        assert report.config_analysis[1]["severity"] == "critical"
