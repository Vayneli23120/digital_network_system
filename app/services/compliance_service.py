"""
配置合规检查服务

基于策略的配置自动审计，检查项包括：
- 密码策略（enable secret, username 密码）
- ACL 配置（是否有 ACL 保护管理平面）
- 端口安全（未使用端口是否 shutdown）
- VLAN 规范（Native VLAN 是否修改）
- SSH 配置（SSH v2, timeout）
- 日志配置（logging 是否启用）
- NTP 配置（时间同步）
"""
import re
from typing import List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class ComplianceCheckResult:
    """单条合规检查结果"""
    check_id: str
    check_name: str
    category: str  # security, availability, compliance
    severity: str  # critical, high, medium, low, info
    passed: bool
    detail: str
    recommendation: str = ""


@dataclass
class ComplianceReport:
    """合规检查报告"""
    device_name: str
    device_ip: str
    total_checks: int = 0
    passed: int = 0
    failed: int = 0
    results: List[ComplianceCheckResult] = field(default_factory=list)

    @property
    def compliance_score(self) -> float:
        if self.total_checks == 0:
            return 100.0
        return round((self.passed / self.total_checks) * 100, 1)


class ComplianceService:
    """配置合规检查服务"""

    def __init__(self):
        self.checks = {
            "SEC-001": self._check_enable_secret,
            "SEC-002": self._check_ssh_version,
            "SEC-003": self._check_password_encryption,
            "SEC-004": self._check_acl_management,
            "SEC-005": self._check_unused_ports,
            "SEC-006": self._check_native_vlan,
            "SEC-007": self._check_logging_enabled,
            "SEC-008": self._check_ntp_config,
            "SEC-009": self._check_banner,
            "SEC-010": self._check_snmp_community,
        }

    def run_all_checks(self, config_text: str, device_name: str = "", device_ip: str = "") -> ComplianceReport:
        """运行所有合规检查"""
        report = ComplianceReport(device_name=device_name, device_ip=device_ip)
        lines = config_text.split("\n")

        for check_id, check_fn in self.checks.items():
            try:
                result = check_fn(lines, config_text)
                report.results.append(result)
                report.total_checks += 1
                if result.passed:
                    report.passed += 1
                else:
                    report.failed += 1
            except Exception as e:
                report.results.append(ComplianceCheckResult(
                    check_id=check_id,
                    check_name=f"Check {check_id}",
                    category="compliance",
                    severity="info",
                    passed=False,
                    detail=f"检查执行出错: {str(e)}",
                    recommendation="联系管理员"
                ))
                report.total_checks += 1
                report.failed += 1

        return report

    def _check_enable_secret(self, lines: List[str], config: str) -> ComplianceCheckResult:
        """SEC-001: 检查是否配置了 enable secret"""
        has_secret = any(re.match(r'^enable secret\s+\S', line) for line in lines)
        return ComplianceCheckResult(
            check_id="SEC-001",
            check_name="Enable Secret 密码",
            category="security",
            severity="critical",
            passed=has_secret,
            detail="已配置 enable secret" if has_secret else "未配置 enable secret，特权模式无密码保护",
            recommendation="配置: enable secret <strong-password>"
        )

    def _check_ssh_version(self, lines: List[str], config: str) -> ComplianceCheckResult:
        """SEC-002: 检查 SSH 版本"""
        has_ssh_v2 = any(line.strip() == 'ip ssh version 2' for line in lines)
        return ComplianceCheckResult(
            check_id="SEC-002",
            check_name="SSH 版本",
            category="security",
            severity="high",
            passed=has_ssh_v2,
            detail="SSH v2 已启用" if has_ssh_v2 else "未强制使用 SSH v2",
            recommendation="配置: ip ssh version 2"
        )

    def _check_password_encryption(self, lines: List[str], config: str) -> ComplianceCheckResult:
        """SEC-003: 检查密码加密"""
        has_encryption = any('service password-encryption' in line for line in lines)
        return ComplianceCheckResult(
            check_id="SEC-003",
            check_name="密码加密服务",
            category="security",
            severity="high",
            passed=has_encryption,
            detail="密码加密已启用" if has_encryption else "明文密码可能暴露在配置中",
            recommendation="配置: service password-encryption"
        )

    def _check_acl_management(self, lines: List[str], config: str) -> ComplianceCheckResult:
        """SEC-004: 检查管理平面 ACL"""
        has_acl = any(re.match(r'^access-list\s+\d+\s+permit\s+tcp', line) for line in lines) or \
                  any('ip access-list' in line for line in lines)
        return ComplianceCheckResult(
            check_id="SEC-004",
            check_name="管理平面 ACL",
            category="security",
            severity="high",
            passed=has_acl,
            detail="ACL 已配置" if has_acl else "未发现管理平面访问控制",
            recommendation="配置 ACL 限制管理平面访问来源 IP"
        )

    def _check_unused_ports(self, lines: List[str], config: str) -> ComplianceCheckResult:
        """SEC-005: 检查未使用端口"""
        shutdown_count = sum(1 for line in lines if 'shutdown' in line.lower())
        total_interfaces = sum(1 for line in lines if re.match(r'^interface\s+', line))
        if total_interfaces == 0:
            return ComplianceCheckResult(
                check_id="SEC-005",
                check_name="端口安全",
                category="security",
                severity="medium",
                passed=True,
                detail="未检测到接口"
            )
        shutdown_ratio = shutdown_count / total_interfaces
        passed = shutdown_ratio > 0.1  # 至少 10% 端口被 shutdown 算合理
        return ComplianceCheckResult(
            check_id="SEC-005",
            check_name="未使用端口处理",
            category="security",
            severity="medium",
            passed=passed,
            detail=f"{total_interfaces} 个接口中 {shutdown_count} 个已 shutdown" if not passed else "未使用端口已合理处理",
            recommendation="未使用的端口应执行 shutdown"
        )

    def _check_native_vlan(self, lines: List[str], config: str) -> ComplianceCheckResult:
        """SEC-006: 检查 Native VLAN"""
        has_native_vlan = any('switchport trunk native vlan' in line for line in lines)
        uses_default = any('switchport trunk native vlan 1' in line for line in lines)
        passed = has_native_vlan and not uses_default
        return ComplianceCheckResult(
            check_id="SEC-006",
            check_name="Native VLAN 配置",
            category="security",
            severity="medium",
            passed=passed,
            detail="Native VLAN 已修改为非默认值" if passed else "Native VLAN 使用默认值 1，存在 VLAN Hopping 风险",
            recommendation="配置: switchport trunk native vlan <非1的VLAN-ID>"
        )

    def _check_logging_enabled(self, lines: List[str], config: str) -> ComplianceCheckResult:
        """SEC-007: 检查日志配置"""
        has_logging = any(re.match(r'^logging\s+\d+\.\d+\.\d+\.\d+', line) for line in lines)
        return ComplianceCheckResult(
            check_id="SEC-007",
            check_name="日志服务器配置",
            category="security",
            severity="medium",
            passed=has_logging,
            detail="远程日志服务器已配置" if has_logging else "未配置远程日志服务器",
            recommendation="配置: logging <syslog-server-ip>"
        )

    def _check_ntp_config(self, lines: List[str], config: str) -> ComplianceCheckResult:
        """SEC-008: 检查 NTP 配置"""
        has_ntp = any(re.match(r'^ntp\s+server\s+', line) for line in lines)
        return ComplianceCheckResult(
            check_id="SEC-008",
            check_name="NTP 时间同步",
            category="availability",
            severity="medium",
            passed=has_ntp,
            detail="NTP 已配置" if has_ntp else "未配置 NTP 服务器",
            recommendation="配置: ntp server <ntp-server-ip>"
        )

    def _check_banner(self, lines: List[str], config: str) -> ComplianceCheckResult:
        """SEC-009: 检查登录警告横幅"""
        has_banner = any('banner motd' in line for line in lines)
        return ComplianceCheckResult(
            check_id="SEC-009",
            check_name="登录警告横幅",
            category="compliance",
            severity="low",
            passed=has_banner,
            detail="MOTD Banner 已配置" if has_banner else "未配置登录警告横幅",
            recommendation="配置: banner motd # <警告信息> #"
        )

    def _check_snmp_community(self, lines: List[str], config: str) -> ComplianceCheckResult:
        """SEC-010: 检查 SNMP Community"""
        has_default = any(line.strip().startswith('snmp-server community public') or
                         line.strip().startswith('snmp-server community private')
                         for line in lines)
        return ComplianceCheckResult(
            check_id="SEC-010",
            check_name="SNMP Community 安全",
            category="security",
            severity="critical",
            passed=not has_default,
            detail="未发现默认 SNMP Community" if not has_default else "使用默认 SNMP Community (public/private)",
            recommendation="修改默认 SNMP Community 字符串"
        )
