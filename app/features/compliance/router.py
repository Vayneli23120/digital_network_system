"""
配置合规检查 API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.features.compliance.compliance_service import ComplianceService, ComplianceReport

router = APIRouter(prefix="/api/compliance", tags=["配置合规"])

compliance_service = ComplianceService()


class ComplianceCheckRequest(BaseModel):
    device_name: str
    device_ip: Optional[str] = None
    config_text: str  # 设备配置文本


class CheckResultResponse(BaseModel):
    check_id: str
    check_name: str
    category: str
    severity: str
    passed: bool
    detail: str
    recommendation: str


class ComplianceReportResponse(BaseModel):
    device_name: str
    device_ip: str
    total_checks: int
    passed: int
    failed: int
    compliance_score: float
    results: List[CheckResultResponse]


@router.post("/check", response_model=ComplianceReportResponse)
async def run_compliance_check(request: ComplianceCheckRequest):
    """
    运行配置合规检查

    传入设备配置文本，自动执行所有合规检查项。
    """
    if not request.config_text.strip():
        raise HTTPException(status_code=400, detail="配置文本不能为空")

    report = compliance_service.run_all_checks(
        config_text=request.config_text,
        device_name=request.device_name,
        device_ip=request.device_ip or ""
    )

    return ComplianceReportResponse(
        device_name=report.device_name,
        device_ip=report.device_ip,
        total_checks=report.total_checks,
        passed=report.passed,
        failed=report.failed,
        compliance_score=report.compliance_score,
        results=[
            CheckResultResponse(**vars(r)) for r in report.results
        ]
    )


@router.get("/checks")
async def list_checks():
    """获取所有可用合规检查项"""
    checks = [
        {"id": "SEC-001", "name": "Enable Secret 密码", "category": "security", "severity": "critical"},
        {"id": "SEC-002", "name": "SSH 版本", "category": "security", "severity": "high"},
        {"id": "SEC-003", "name": "密码加密服务", "category": "security", "severity": "high"},
        {"id": "SEC-004", "name": "管理平面 ACL", "category": "security", "severity": "high"},
        {"id": "SEC-005", "name": "未使用端口处理", "category": "security", "severity": "medium"},
        {"id": "SEC-006", "name": "Native VLAN 配置", "category": "security", "severity": "medium"},
        {"id": "SEC-007", "name": "日志服务器配置", "category": "security", "severity": "medium"},
        {"id": "SEC-008", "name": "NTP 时间同步", "category": "availability", "severity": "medium"},
        {"id": "SEC-009", "name": "登录警告横幅", "category": "compliance", "severity": "low"},
        {"id": "SEC-010", "name": "SNMP Community 安全", "category": "security", "severity": "critical"},
    ]
    return checks


@router.post("/check-device/{device_id}")
async def check_device_config(device_id: int):
    """
    对指定设备运行合规检查

    从设备获取当前配置并执行检查。
    """
    # TODO: 从设备获取配置，使用 app.features.devices.router
    # 需要整合设备路由获取配置
    raise HTTPException(status_code=501, detail="设备合规检查需要连接真实设备，待实现")
