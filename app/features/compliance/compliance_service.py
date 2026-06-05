"""
配置合规检查服务（ADK 版本）

流程：
1. 获取所有激活的规则（内置 + AI生成）
2. 将规则组合成提示词
3. 使用 ADK chat 发送给 LLM，获取检查结果
4. 结果包含配置行号，用于前端高亮显示
"""
import re
import json
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger

from app.shared.database import get_db
from app.shared.models import ComplianceRule, ComplianceAuditLog, AIConfig
from app.features.compliance.builtin_rules import get_all_rules_for_audit, init_builtin_rules

# 使用 ADK runner
from app.services.adk.runner import adk_runner


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
    pattern: str = ""  # 匹配模式
    # 新增：配置行位置标注
    line_numbers: List[int] = field(default_factory=list)  # 问题所在行号
    line_content: str = ""  # 问题行内容
    ai_analysis: Optional[str] = None  # AI 深度分析


@dataclass
class ComplianceReport:
    """合规检查报告"""
    device_name: str
    device_ip: str = ""
    total_checks: int = 0
    passed: int = 0
    failed: int = 0
    results: List[ComplianceCheckResult] = field(default_factory=list)
    ai_score: Optional[float] = None  # AI 评估分数
    ai_insights: Optional[str] = None  # AI 整体洞察
    audit_mode: str = "full"  # full, basic, ai_only
    # 新增：带行号标注的配置分析
    config_analysis: List[Dict] = field(default_factory=list)  # 每行配置的分析结果

    @property
    def compliance_score(self) -> float:
        if self.total_checks == 0:
            return 100.0
        return round((self.passed / self.total_checks) * 100, 1)


class ComplianceService:
    """配置合规检查服务（优化版）"""

    def __init__(self):
        # 初始化内置规则
        try:
            init_builtin_rules()
        except Exception as e:
            logger.warning(f"内置规则初始化检查: {e}")

    async def audit_config(
        self,
        config_text: str,
        device_name: str = "",
        device_ip: str = "",
        audit_mode: str = "full",
        use_ai: bool = True
    ) -> ComplianceReport:
        """
        执行配置审核（优化版）

        Args:
            config_text: 配置文本
            device_name: 设备名称
            device_ip: 设备 IP
            audit_mode: 审核模式 (full, basic, ai_only)
            use_ai: 是否使用 AI 审核

        Returns:
            ComplianceReport 审核报告
        """
        report = ComplianceReport(
            device_name=device_name,
            device_ip=device_ip,
            audit_mode=audit_mode
        )

        # Step 1: 获取所有激活的规则（作为 AI 提示词）
        active_rules = get_all_rules_for_audit()

        if not active_rules:
            logger.warning("没有激活的检查规则")
            report.ai_insights = "没有配置检查规则，请先激活规则或上传标准文档生成规则"
            return report

        logger.info(f"获取到 {len(active_rules)} 条激活规则用于检查")

        # Step 2: 使用 AI 根据规则提示词检查配置
        if use_ai:
            ai_result = await self._run_ai_rule_based_audit(config_text, active_rules, device_name)

            if ai_result:
                # 解析 AI 返回结果
                self._parse_ai_result(report, ai_result, active_rules)
            else:
                # AI 调用失败，回退到基础检查
                report.ai_insights = "AI 服务不可用，请检查 AI 配置"
                self._run_basic_audit(report, config_text, active_rules)
        else:
            # 不使用 AI，执行基础正则检查
            self._run_basic_audit(report, config_text, active_rules)

        # Step 3: 生成配置行分析（用于前端高亮）
        self._generate_config_analysis(report, config_text)

        # Step 4: 保存审核记录
        self._save_audit_log(report, config_text)

        return report

    async def _run_ai_rule_based_audit(self, config_text: str, rules: List[Dict], device_name: str) -> Optional[Dict]:
        """使用 ADK chat 模式进行 AI 规则检查"""

        # 构建规则提示词
        rules_prompt = self._build_simple_rules_prompt(rules)

        # 系统提示词 - 定义 AI 的角色
        system_prompt = """你是网络设备配置合规审核专家。
根据提供的规则检查设备配置，输出 JSON 格式的检查结果。
只输出 JSON，不要包含其他文字说明。"""

        # 用户消息 - 配置 + 规则
        message = f"""请检查以下网络设备配置：

设备名称: {device_name}

检查规则（共 {len(rules)} 条）:
{rules_prompt}

设备配置:
{config_text}

输出格式（JSON）:
{{"overall_score": 0-100, "ai_insights": "整体评估", "results": [{{"rule_id": "ID", "rule_name": "名称", "passed": true/false, "detail": "详情", "line_numbers": [行号]}}]}}"""

        logger.info(f"开始 AI 规则检查，共 {len(rules)} 条规则")

        # 使用 ADK chat 模式
        result = await adk_runner.chat(
            message=message,
            system_prompt=system_prompt,
            timeout=180  # 给更长的超时时间
        )

        if result.get("success"):
            response_text = result.get("response", "")
            logger.info(f"AI 响应成功，长度: {len(response_text)}")

            # 解析 JSON 结果
            parsed = adk_runner.parse_json_response(response_text)
            if parsed:
                return parsed
            else:
                logger.warning("AI 返回内容无法解析为 JSON")
                return None
        else:
            logger.warning(f"AI 调用失败: {result.get('error')}")
            return None
            return None

    def _build_simple_rules_prompt(self, rules: List[Dict]) -> str:
        """构建简化版规则提示词"""
        prompt_lines = []
        for rule in rules:
            prompt_lines.append(f"{rule['rule_id']}: {rule['name']} - 检查 {rule['pattern']}")
        return "\n".join(prompt_lines)

    def _build_rules_prompt(self, rules: List[Dict]) -> str:
        """构建规则提示词（详细版）"""
        prompt_lines = []

        for rule in rules:
            prompt_lines.append(f"""
### {rule['rule_id']}: {rule['name']}
- **类别**: {rule['category']}
- **严重程度**: {rule['severity']}
- **检查要求**: {rule['check_logic']}
- **匹配特征**: {rule['pattern']}
- **修复建议**: {rule['recommendation']}
""")

        return "\n".join(prompt_lines)

    def _parse_ai_result(self, report: ComplianceReport, ai_result, rules: List[Dict]):
        """解析 AI 返回结果（支持字典或列表）"""
        # 如果返回的是列表，转换为字典格式
        if isinstance(ai_result, list):
            # AI 返回了结果列表，需要处理
            report.ai_score = 50
            report.ai_insights = "AI 返回了检查结果列表"
            results_data = ai_result
        else:
            # 字典格式
            report.ai_score = ai_result.get("overall_score", 50)
            report.ai_insights = ai_result.get("ai_insights", "")
            results_data = ai_result.get("results", [])

        # 解析检查结果，补充规则库中的信息
        rules_map = {r["rule_id"]: r for r in rules}

        for result_data in results_data:
            if isinstance(result_data, dict):
                rule_id = result_data.get("rule_id", result_data.get("id", ""))
                # 从规则库获取补充信息
                rule_info = rules_map.get(rule_id, {})

                result = ComplianceCheckResult(
                    check_id=rule_id,
                    check_name=result_data.get("rule_name", result_data.get("name", rule_info.get("name", ""))),
                    category=result_data.get("category", rule_info.get("category", "compliance")),
                    severity=result_data.get("severity", rule_info.get("severity", "medium")),
                    passed=result_data.get("passed", False),
                    detail=result_data.get("detail", ""),
                    recommendation=result_data.get("recommendation", "") or rule_info.get("recommendation", ""),
                    line_numbers=result_data.get("line_numbers", []),
                    line_content=result_data.get("line_content", "")
                )
                report.results.append(result)

        # 统计
        report.total_checks = len(report.results)
        report.passed = sum(1 for r in report.results if r.passed)
        report.failed = report.total_checks - report.passed

        # 解析配置行分析
        if isinstance(ai_result, dict):
            report.config_analysis = ai_result.get("config_lines", [])
        else:
            report.config_analysis = []

        logger.info(f"AI 检查完成: {report.passed} 通过, {report.failed} 失败, 分数 {report.compliance_score}")

    def _run_basic_audit(self, report: ComplianceReport, config_text: str, rules: List[Dict]):
        """基础正则检查（AI 不可用时的备用方案）"""
        lines = config_text.split("\n")

        for rule in rules:
            passed = False
            detail = ""
            line_numbers = []
            pattern = rule.get("pattern", "")

            if pattern:
                # 正则匹配
                try:
                    regex = re.compile(pattern, re.IGNORECASE)
                    for i, line in enumerate(lines):
                        if regex.search(line):
                            passed = True
                            line_numbers.append(i + 1)

                    if passed:
                        detail = f"配置符合要求，匹配行: {line_numbers}"
                    else:
                        detail = f"未发现匹配配置: {pattern}"
                except:
                    # 正则无效，使用关键词匹配
                    pattern_lower = pattern.lower()
                    for i, line in enumerate(lines):
                        if pattern_lower in line.lower():
                            passed = True
                            line_numbers.append(i + 1)

                    if passed:
                        detail = f"发现关键词匹配，行: {line_numbers}"
                    else:
                        detail = f"未发现关键词: {pattern}"

            result = ComplianceCheckResult(
                check_id=rule["rule_id"],
                check_name=rule["name"],
                category=rule.get("category", "compliance"),
                severity=rule.get("severity", "medium"),
                passed=passed,
                detail=detail,
                recommendation=rule.get("recommendation", ""),
                pattern=pattern,
                line_numbers=line_numbers
            )
            report.results.append(result)

        report.total_checks = len(report.results)
        report.passed = sum(1 for r in report.results if r.passed)
        report.failed = report.total_checks - report.passed

    def _generate_config_analysis(self, report: ComplianceReport, config_text: str):
        """生成配置行分析（用于前端高亮）"""
        if report.config_analysis:
            # AI 已返回配置行分析
            return

        # 如果 AI 没有返回，根据检查结果生成
        lines = config_text.split("\n")
        analysis = []

        # 收集每个规则的问题行
        issue_lines = {}  # {行号: [rule_ids]}

        for result in report.results:
            if not result.passed and result.line_numbers:
                for line_num in result.line_numbers:
                    if line_num not in issue_lines:
                        issue_lines[line_num] = []
                    issue_lines[line_num].append({
                        "rule_id": result.check_id,
                        "severity": result.severity
                    })

        # 生成分析
        for i, line in enumerate(lines):
            line_num = i + 1
            issues = issue_lines.get(line_num, [])

            analysis.append({
                "line_number": line_num,
                "content": line,
                "issues": issues,
                "severity": max([i["severity"] for i in issues], default="ok")
            })

        report.config_analysis = analysis

    def _save_audit_log(self, report: ComplianceReport, config_text: str):
        """保存审核记录"""
        db = next(get_db())
        try:
            ai_config = db.query(AIConfig).filter(AIConfig.is_active == True).first()

            log = ComplianceAuditLog(
                device_name=report.device_name,
                config_source="audit",
                config_text=config_text[:5000],
                compliance_score=report.compliance_score,
                total_checks=report.total_checks,
                passed=report.passed,
                failed=report.failed,
                audit_mode=report.audit_mode,
                ai_provider=ai_config.provider if ai_config else None,
                ai_model=ai_config.model_name if ai_config else None,
                result_detail=json.dumps({
                    "ai_score": report.ai_score,
                    "ai_insights": report.ai_insights,
                    "results": [
                        {
                            "check_id": r.check_id,
                            "check_name": r.check_name,
                            "passed": r.passed,
                            "detail": r.detail,
                            "recommendation": r.recommendation,
                            "line_numbers": r.line_numbers
                        }
                        for r in report.results
                    ],
                    "config_analysis": report.config_analysis[:200]  # 只保存前200行
                }),
                created_at=datetime.utcnow(),
                created_by="Web"
            )
            db.add(log)
            db.commit()
            logger.info(f"保存审核记录: id={log.id}, score={report.compliance_score}")
        except Exception as e:
            logger.error(f"保存审核记录失败: {e}")
            db.rollback()
        finally:
            db.close()

    async def quick_audit(self, config_text: str) -> Dict:
        """快速审核（使用 ADK chat 模式）"""

        system_prompt = "你是网络设备配置安全审核专家。快速识别安全问题并输出 JSON 结果。"

        message = f"""请快速审核以下网络设备配置：

配置内容：
{config_text[:2000]}

识别：
1. 安全问题（明文密码、默认配置、弱认证等）
2. 合规问题（缺少必要配置、配置不规范等）

输出 JSON 格式：
{{"score": 0-100, "issues": [{{"rule": "问题", "line": 行号, "severity": "级别"}}]}}"""

        # 使用 ADK chat
        result = await adk_runner.chat(
            message=message,
            system_prompt=system_prompt,
            timeout=60
        )

        if result.get("success"):
            parsed = adk_runner.parse_json_response(result.get("response", ""))
            if parsed:
                return {
                    "success": True,
                    "score": parsed.get("score", 50),
                    "results": parsed.get("issues", []),
                }
        return {"success": False, "error": result.get("error", "AI 服务不可用")}