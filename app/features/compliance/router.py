"""
配置合规检查 API

支持：
- 配置审核（规则 + AI）
- 文件上传审核
- 标准文档管理
- AI 规则生成
- AI 配置管理
"""
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from pydantic import BaseModel
from datetime import datetime
from io import BytesIO
from loguru import logger

from app.features.compliance.compliance_service import ComplianceService, ComplianceReport
from app.features.compliance.config_parser_service import ConfigParserService
from app.features.compliance.standard_service import StandardService

router = APIRouter(prefix="/api/compliance", tags=["配置合规"])

compliance_service = ComplianceService()
config_parser_service = ConfigParserService()
standard_service = StandardService()


# ==================== 请求/响应模型 ====================

class ComplianceCheckRequest(BaseModel):
    """配置审核请求"""
    config_text: str  # 设备配置文本
    device_name: Optional[str] = ""
    device_ip: Optional[str] = None
    audit_mode: Optional[str] = "full"  # full, basic, ai_only
    use_ai: Optional[bool] = True


class CheckResultResponse(BaseModel):
    """单条检查结果"""
    check_id: str
    check_name: str
    category: str
    severity: str
    passed: bool
    detail: str
    recommendation: str
    pattern: Optional[str] = ""
    ai_analysis: Optional[str] = None
    # 新增：行号标注
    line_numbers: List[int] = []
    line_content: Optional[str] = ""


class ConfigLineAnalysis(BaseModel):
    """配置行分析结果"""
    line_number: int
    content: str
    issues: List[Dict] = []  # [{rule_id, severity}]
    severity: str = "ok"  # ok, low, medium, high, critical


class ComplianceReportResponse(BaseModel):
    """审核报告响应"""
    device_name: str
    device_ip: str
    total_checks: int
    passed: int
    failed: int
    compliance_score: float
    audit_mode: str
    ai_score: Optional[float] = None
    ai_insights: Optional[str] = None
    results: List[CheckResultResponse]
    # 新增：配置行分析
    config_analysis: List[ConfigLineAnalysis] = []


class StandardCreateRequest(BaseModel):
    """创建标准文档请求"""
    name: str
    version: str
    content: str
    description: Optional[str] = None
    created_by: Optional[str] = None


class StandardUpdateRequest(BaseModel):
    """更新标准文档请求"""
    name: Optional[str] = None
    version: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class AIConfigRequest(BaseModel):
    """AI 配置请求"""
    provider: str  # openai / anthropic
    api_key: str
    base_url: Optional[str] = None
    model_name: Optional[str] = "gpt-4"
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 4096
    timeout: Optional[int] = 60
    is_default: Optional[bool] = True


# ==================== 配置审核 API ====================

@router.post("/check", response_model=ComplianceReportResponse)
async def run_compliance_check(request: ComplianceCheckRequest):
    """
    运行配置合规检查

    流程：
    1. 规则定位（基本面检查）
    2. AI 深度审核

    Args:
        request: 审核请求，包含配置文本和审核模式
    """
    if not request.config_text.strip():
        raise HTTPException(status_code=400, detail="配置文本不能为空")

    report = await compliance_service.audit_config(
        config_text=request.config_text,
        device_name=request.device_name or "",
        device_ip=request.device_ip or "",
        audit_mode=request.audit_mode,
        use_ai=request.use_ai
    )

    return ComplianceReportResponse(
        device_name=report.device_name,
        device_ip=report.device_ip,
        total_checks=report.total_checks,
        passed=report.passed,
        failed=report.failed,
        compliance_score=report.compliance_score,
        audit_mode=report.audit_mode,
        ai_score=report.ai_score,
        ai_insights=report.ai_insights,
        results=[
            CheckResultResponse(
                check_id=r.check_id,
                check_name=r.check_name,
                category=r.category,
                severity=r.severity,
                passed=r.passed,
                detail=r.detail,
                recommendation=r.recommendation,
                pattern=r.pattern,
                ai_analysis=r.ai_analysis,
                line_numbers=r.line_numbers,
                line_content=r.line_content
            )
            for r in report.results
        ],
        config_analysis=[
            ConfigLineAnalysis(
                line_number=line.get("line_number", 0),
                content=line.get("content", ""),
                issues=line.get("issues", []),
                severity=line.get("severity", "ok")
            )
            for line in report.config_analysis
        ]
    )


@router.post("/upload")
async def upload_config_file(file: UploadFile = File(...)):
    """
    上传配置文件进行审核

    支持格式：
    - .txt, .cfg, .log, .conf - 文本配置文件
    - .xlsx, .xls - Excel 批量设备配置

    Args:
        file: 上传的配置文件
    """
    # 读取文件内容
    content = await file.read()
    filename = file.filename or "config.txt"

    # 解析文件
    parse_result = config_parser_service.parse_file(content, filename)

    if not parse_result.get("success"):
        raise HTTPException(status_code=400, detail=parse_result.get("error", "文件解析失败"))

    # 如果是多设备配置，批量审核
    if parse_result.get("format") == "multi_device":
        devices = parse_result.get("devices", [])
        audit_results = []

        for device in devices:
            report = await compliance_service.audit_config(
                config_text=device["config_text"],
                device_name=device["device_name"],
                device_ip=device.get("ip", "")
            )
            audit_results.append({
                "device_name": device["device_name"],
                "device_ip": device.get("ip"),
                "compliance_score": report.compliance_score,
                "passed": report.passed,
                "failed": report.failed
            })

        return {
            "success": True,
            "format": "multi_device",
            "device_count": len(devices),
            "parse_result": {
                "total_lines": parse_result.get("total_lines"),
                "device_count": parse_result.get("device_count")
            },
            "audit_results": audit_results
        }

    # 单设备配置，直接审核
    config_text = parse_result.get("config_text", "")

    report = await compliance_service.audit_config(
        config_text=config_text,
        device_name=parse_result.get("hostname", ""),
        audit_mode="full"
    )

    return {
        "success": True,
        "format": "single_device",
        "parse_result": {
            "device_type": parse_result.get("device_type"),
            "hostname": parse_result.get("hostname"),
            "total_lines": parse_result.get("total_lines"),
            "config_lines": parse_result.get("config_lines"),
            "encoding": parse_result.get("encoding")
        },
        "audit_result": ComplianceReportResponse(
            device_name=report.device_name,
            device_ip=report.device_ip,
            total_checks=report.total_checks,
            passed=report.passed,
            failed=report.failed,
            compliance_score=report.compliance_score,
            audit_mode=report.audit_mode,
            ai_score=report.ai_score,
            ai_insights=report.ai_insights,
            results=[
                CheckResultResponse(
                    check_id=r.check_id,
                    check_name=r.check_name,
                    category=r.category,
                    severity=r.severity,
                    passed=r.passed,
                    detail=r.detail,
                    recommendation=r.recommendation
                )
                for r in report.results
            ]
        )
    }


@router.post("/quick-check")
async def quick_compliance_check(request: ComplianceCheckRequest):
    """
    快速审核（仅 AI 审核，不依赖规则库）
    """
    result = await compliance_service.quick_audit(request.config_text)

    if not result.get("success"):
        return {"success": False, "error": result.get("error", "AI 服务不可用")}

    return {
        "success": True,
        "score": result.get("score", 50),
        "security_issues": result.get("security_issues", []),
        "compliance_issues": result.get("compliance_issues", []),
        "config_errors": result.get("config_errors", []),
        "recommendations": result.get("recommendations", [])
    }


# ==================== 标准文档管理 API ====================

@router.get("/standards")
async def list_standards(include_inactive: bool = False):
    """获取标准文档列表"""
    standards = standard_service.list_standards(include_inactive)
    return {"standards": standards}


@router.get("/standards/{standard_id}")
async def get_standard(standard_id: int):
    """获取标准文档详情"""
    standard = standard_service.get_standard(standard_id)
    if not standard:
        raise HTTPException(status_code=404, detail="标准文档不存在")
    return standard


@router.post("/standards")
async def create_standard(request: StandardCreateRequest):
    """创建标准文档"""
    standard = standard_service.create_standard(
        name=request.name,
        version=request.version,
        content=request.content,
        description=request.description,
        created_by=request.created_by
    )
    return {"success": True, "standard": standard}


@router.put("/standards/{standard_id}")
async def update_standard(standard_id: int, request: StandardUpdateRequest):
    """更新标准文档"""
    standard = standard_service.update_standard(
        standard_id=standard_id,
        name=request.name,
        version=request.version,
        content=request.content,
        description=request.description,
        is_active=request.is_active
    )
    if not standard:
        raise HTTPException(status_code=404, detail="标准文档不存在")
    return {"success": True, "standard": standard}


@router.delete("/standards/{standard_id}")
async def delete_standard(standard_id: int):
    """删除标准文档"""
    success = standard_service.delete_standard(standard_id)
    if not success:
        raise HTTPException(status_code=404, detail="标准文档不存在")
    return {"success": True}


@router.post("/standards/{standard_id}/generate-rules")
async def generate_rules_for_standard(standard_id: int):
    """
    为标准文档生成检查规则（通过 AI）

    AI 会分析标准文档内容，自动生成检查规则
    """
    result = await standard_service.generate_rules_for_standard(standard_id)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "规则生成失败"))

    return result


@router.post("/standards/{standard_id}/update-rules")
async def update_rules_for_standard(standard_id: int):
    """
    更新标准文档的规则

    AI 会对比新旧内容，识别变化后更新规则
    """
    result = await standard_service.update_rules_for_standard(standard_id)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "规则更新失败"))

    return result


@router.post("/standards/upload")
async def upload_standard_document(file: UploadFile = File(...)):
    """
    上传标准文档（支持 txt, pdf 等）

    Args:
        file: 标准文档文件
    """
    content = await file.read()
    filename = file.filename or "standard.txt"

    # 尝试解码为文本
    try:
        text_content = content.decode('utf-8')
    except UnicodeDecodeError:
        try:
            text_content = content.decode('gbk')
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="无法解码文件内容")

    # 创建标准文档（版本号从文件名提取或默认）
    version = "1.0"
    name = filename.rsplit('.', 1)[0] if '.' in filename else filename

    standard = standard_service.create_standard(
        name=name,
        version=version,
        content=text_content,
        created_by="Web"
    )

    return {
        "success": True,
        "standard": standard,
        "filename": filename,
        "content_length": len(text_content)
    }


# ==================== 规则管理 API ====================

@router.get("/rules")
async def list_rules(standard_id: Optional[int] = None):
    """
    获取检查规则列表

    Args:
        standard_id: 可选，筛选指定标准文档的规则
    """
    if standard_id:
        rules = standard_service.get_rules_by_standard(standard_id)
    else:
        rules = standard_service.get_active_rules()

    return {"rules": rules}


@router.put("/rules/{rule_id}/status")
async def update_rule_status(rule_id: int, is_active: bool = Query(...)):
    """更新规则状态（启用/禁用）"""
    success = standard_service.update_rule_status(rule_id, is_active)
    if not success:
        raise HTTPException(status_code=404, detail="规则不存在")
    return {"success": True}


class RuleUpdateRequest(BaseModel):
    """更新规则请求"""
    name: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    pattern: Optional[str] = None
    check_logic: Optional[str] = None
    recommendation: Optional[str] = None
    is_active: Optional[bool] = None


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: int, request: RuleUpdateRequest):
    """更新规则内容"""
    result = standard_service.update_rule(rule_id, request.dict(exclude_unset=True))
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "规则不存在"))
    return result


@router.get("/rules/{rule_id}")
async def get_rule_detail(rule_id: int):
    """获取规则详情"""
    rule = standard_service.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    return rule


# ==================== AI 配置管理 API ====================

@router.get("/ai-config")
async def get_ai_config():
    """获取当前 AI 配置"""
    from app.shared.database import get_db
    from app.shared.models import AIConfig

    db = next(get_db())
    try:
        config = db.query(AIConfig).filter(AIConfig.is_active == True).first()

        if not config:
            return {
                "configured": False,
                "message": "未配置 AI 服务"
            }

        return {
            "configured": True,
            "id": config.id,
            "name": config.name,
            "provider": config.provider,
            "base_url": config.base_url,
            "model_name": config.model_name,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "timeout": config.timeout,
            "is_default": config.is_default
            # 不返回 api_key（安全考虑）
        }
    finally:
        db.close()


@router.post("/ai-config")
async def create_ai_config(request: AIConfigRequest):
    """创建 AI 配置"""
    from app.shared.database import get_db
    from app.shared.models import AIConfig

    db = next(get_db())
    try:
        # 如果设置为默认，先取消其他默认配置
        if request.is_default:
            db.query(AIConfig).update({"is_default": False})

        config = AIConfig(
            name=f"{request.provider}-{request.model_name}",
            provider=request.provider,
            api_key_encrypted=request.api_key,  # 暂不加密，后续可添加加密逻辑
            base_url=request.base_url,
            model_name=request.model_name,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            timeout=request.timeout,
            is_active=True,
            is_default=request.is_default,
            created_at=datetime.utcnow()
        )
        db.add(config)
        db.commit()
        db.refresh(config)

        logger.info(f"创建 AI 配置: provider={request.provider}, model={request.model_name}")

        return {
            "success": True,
            "id": config.id,
            "provider": config.provider,
            "model_name": config.model_name
        }
    except Exception as e:
        db.rollback()
        logger.error(f"创建 AI 配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.put("/ai-config/{config_id}")
async def update_ai_config(config_id: int, request: AIConfigRequest):
    """更新 AI 配置"""
    from app.shared.database import get_db
    from app.shared.models import AIConfig

    db = next(get_db())
    try:
        config = db.query(AIConfig).filter(AIConfig.id == config_id).first()
        if not config:
            raise HTTPException(status_code=404, detail="AI 配置不存在")

        config.provider = request.provider
        config.api_key_encrypted = request.api_key
        config.base_url = request.base_url
        config.model_name = request.model_name
        config.temperature = request.temperature
        config.max_tokens = request.max_tokens
        config.timeout = request.timeout

        if request.is_default:
            db.query(AIConfig).update({"is_default": False})
            config.is_default = True

        config.updated_at = datetime.utcnow()
        db.commit()

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/ai-config/test")
async def test_ai_config(request: AIConfigRequest):
    """测试 AI 配置是否有效"""
    try:
        # 使用 ADK config 进行测试
        from app.services.adk.config import adk_config

        # 临时设置环境变量进行测试
        import os
        provider_map = {
            'openai': 'OPENAI_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY',
            'deepseek': 'DEEPSEEK_API_KEY'
        }
        env_key = provider_map.get(request.provider, f"{request.provider.upper()}_API_KEY")
        os.environ[env_key] = request.api_key

        # 尝试创建 LiteLlm 模型
        from google.adk.models import LiteLlm

        model_str = f"{request.provider}/{request.model_name}"

        # 简单验证配置格式
        test_model = LiteLlm(
            model=model_str,
            api_base=request.base_url if request.base_url else None,
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens or 4096
        )

        return {
            "success": True,
            "message": "AI 配置格式有效",
            "provider": request.provider,
            "model": request.model_name
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ==================== 旧版 API 兼容 ====================

@router.get("/checks")
async def list_checks():
    """获取所有可用合规检查项（旧版兼容）"""
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