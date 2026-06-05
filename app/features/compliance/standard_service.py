"""
配置标准文档管理服务

功能：
- 标准文档的 CRUD 操作
- AI 规则生成（使用 ADK Agent）
- 规则同步更新
"""
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger

from app.shared.database import get_db
from app.shared.models import ComplianceStandard, ComplianceRule, AIConfig

# ADK 导入
from app.services.adk.runner import adk_runner
from app.services.adk.agents import rule_generator_agent


class StandardService:
    """配置标准文档管理服务"""

    def __init__(self):
        pass

    # ==================== 标准文档管理 ====================

    def list_standards(self, include_inactive: bool = False) -> List[Dict]:
        """
        获取标准文档列表

        Args:
            include_inactive: 是否包含已禁用的文档

        Returns:
            标准文档列表
        """
        db = next(get_db())
        try:
            query = db.query(ComplianceStandard)
            if not include_inactive:
                query = query.filter(ComplianceStandard.is_active == True)

            standards = query.order_by(ComplianceStandard.updated_at.desc()).all()

            return [
                {
                    "id": s.id,
                    "name": s.name,
                    "version": s.version,
                    "description": s.description,
                    "is_active": s.is_active,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                    "created_by": s.created_by,
                    "rule_count": db.query(ComplianceRule).filter(
                        ComplianceRule.standard_id == s.id,
                        ComplianceRule.is_active == True
                    ).count()
                }
                for s in standards
            ]
        finally:
            db.close()

    def get_standard(self, standard_id: int) -> Optional[Dict]:
        """
        获取单个标准文档详情

        Args:
            standard_id: 标准文档 ID

        Returns:
            标准文档详情
        """
        db = next(get_db())
        try:
            standard = db.query(ComplianceStandard).filter(
                ComplianceStandard.id == standard_id
            ).first()

            if not standard:
                return None

            # 获取关联的规则
            rules = db.query(ComplianceRule).filter(
                ComplianceRule.standard_id == standard_id,
                ComplianceRule.is_active == True
            ).all()

            return {
                "id": standard.id,
                "name": standard.name,
                "version": standard.version,
                "description": standard.description,
                "content": standard.content,
                "file_path": standard.file_path,
                "is_active": standard.is_active,
                "created_at": standard.created_at.isoformat() if standard.created_at else None,
                "updated_at": standard.updated_at.isoformat() if standard.updated_at else None,
                "created_by": standard.created_by,
                "rules": [
                    {
                        "id": r.id,
                        "rule_id": r.rule_id,
                        "name": r.name,
                        "category": r.category,
                        "severity": r.severity,
                        "pattern": r.pattern,
                        "check_logic": r.check_logic,
                        "recommendation": r.recommendation,
                        "source_type": r.source_type
                    }
                    for r in rules
                ]
            }
        finally:
            db.close()

    def create_standard(
        self,
        name: str,
        version: str,
        content: str,
        description: Optional[str] = None,
        file_path: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Dict:
        """
        创建新的标准文档

        Args:
            name: 标准名称
            version: 版本号
            content: 标准文档内容
            description: 描述
            file_path: 上传文件路径
            created_by: 创建者

        Returns:
            创建的标准文档
        """
        db = next(get_db())
        try:
            standard = ComplianceStandard(
                name=name,
                version=version,
                content=content,
                description=description,
                file_path=file_path,
                is_active=True,
                created_by=created_by,
                created_at=datetime.utcnow()
            )
            db.add(standard)
            db.commit()
            db.refresh(standard)

            logger.info(f"创建标准文档: id={standard.id}, name={name}, version={version}")

            return {
                "id": standard.id,
                "name": standard.name,
                "version": standard.version,
                "description": standard.description,
                "content": standard.content,
                "is_active": standard.is_active,
                "created_at": standard.created_at.isoformat()
            }
        except Exception as e:
            db.rollback()
            logger.error(f"创建标准文档失败: {e}")
            raise
        finally:
            db.close()

    def update_standard(
        self,
        standard_id: int,
        name: Optional[str] = None,
        version: Optional[str] = None,
        content: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Optional[Dict]:
        """
        更新标准文档

        Args:
            standard_id: 标准文档 ID
            name: 标准名称
            version: 版本号
            content: 标准文档内容
            description: 描述
            is_active: 是否启用

        Returns:
            更新后的标准文档
        """
        db = next(get_db())
        try:
            standard = db.query(ComplianceStandard).filter(
                ComplianceStandard.id == standard_id
            ).first()

            if not standard:
                return None

            if name:
                standard.name = name
            if version:
                standard.version = version
            if content:
                standard.content = content
            if description:
                standard.description = description
            if is_active is not None:
                standard.is_active = is_active

            standard.updated_at = datetime.utcnow()

            db.commit()
            db.refresh(standard)

            logger.info(f"更新标准文档: id={standard_id}")

            return {
                "id": standard.id,
                "name": standard.name,
                "version": standard.version,
                "description": standard.description,
                "content": standard.content,
                "is_active": standard.is_active,
                "updated_at": standard.updated_at.isoformat()
            }
        except Exception as e:
            db.rollback()
            logger.error(f"更新标准文档失败: {e}")
            raise
        finally:
            db.close()

    def delete_standard(self, standard_id: int) -> bool:
        """
        删除标准文档（及其关联的规则）

        Args:
            standard_id: 标准文档 ID

        Returns:
            是否成功
        """
        db = next(get_db())
        try:
            standard = db.query(ComplianceStandard).filter(
                ComplianceStandard.id == standard_id
            ).first()

            if not standard:
                return False

            # 关联的规则会通过 cascade 自动删除
            db.delete(standard)
            db.commit()

            logger.info(f"删除标准文档: id={standard_id}")

            return True
        except Exception as e:
            db.rollback()
            logger.error(f"删除标准文档失败: {e}")
            raise
        finally:
            db.close()

    # ==================== AI 规则生成 ====================

    def is_ai_configured(self) -> bool:
        """检查 AI 是否已配置"""
        db = next(get_db())
        try:
            config = db.query(AIConfig).filter(AIConfig.is_active == True).first()
            return config is not None
        finally:
            db.close()

    async def generate_rules_for_standard(self, standard_id: int) -> Dict:
        """
        为标准文档生成检查规则（通过 ADK Agent）

        Args:
            standard_id: 标准文档 ID

        Returns:
            生成结果
        """
        # 获取标准文档
        standard = self.get_standard(standard_id)
        if not standard:
            return {"success": False, "error": "标准文档不存在"}

        # 检查 AI 是否配置
        if not self.is_ai_configured():
            return {"success": False, "error": "未配置 AI 服务，请先在 AI 配置中设置 API Key"}

        # 构建 Agent 消息
        message = f"""请从以下网络设备配置标准文档中提取合规检查规则：

标准文档名称：{standard['name']}
版本：{standard['version']}
内容：
{standard['content'][:5000]}

请分析文档中的配置要求，为每个要求生成一条可验证的检查规则。
规则应包含：
- rule_id: 规则编号（如 SEC-001, COM-001）
- name: 规则名称
- category: 类别（security/availability/compliance）
- severity: 严重程度（critical/high/medium/low）
- pattern: 正则表达式或关键词用于检查
- check_logic: 检查逻辑描述
- recommendation: 推荐配置

输出 JSON 数组格式。"""

        logger.info(f"开始为标准文档 {standard_id} 生成规则...")

        try:
            # 使用 ADK Agent 生成规则 - 异步调用
            result = await adk_runner.run_agent(
                agent=rule_generator_agent,
                user_id="standard_service",
                message=message,
                analysis_type="rule_generation",
                target_type="standard",
                target_id=standard_id,
                save_audit=False,
                db=None
            )

            logger.info(f"ADK Agent 返回结果: success={result.get('success')}, error={result.get('error')}")

            if not result.get("success"):
                error_msg = result.get("error", "AI 生成失败")
                logger.error(f"AI 规则生成失败: {error_msg}")
                return {"success": False, "error": error_msg}

            response_text = result.get("response", "")
            logger.info(f"AI 返回内容长度: {len(response_text)} 字符")

            # 解析生成的规则
            generated_rules = adk_runner.parse_json_response(result.get("response", ""))
            if not generated_rules:
                return {"success": False, "error": "AI 未生成有效规则，请检查标准文档内容"}

            # 如果返回的是单个对象，转为数组
            if isinstance(generated_rules, dict):
                generated_rules = [generated_rules]

            # 保存规则到数据库
            db = next(get_db())
            try:
                # 先禁用该标准文档的旧规则
                db.query(ComplianceRule).filter(
                    ComplianceRule.standard_id == standard_id
                ).update({"is_active": False})

                # 添加新规则
                new_rules = []
                for rule_data in generated_rules:
                    if isinstance(rule_data, dict):
                        rule = ComplianceRule(
                            standard_id=standard_id,
                            rule_id=rule_data.get("rule_id", f"AI-{len(new_rules)+1:03d}"),
                            name=rule_data.get("name", "未命名规则"),
                            category=rule_data.get("category", "compliance"),
                            severity=rule_data.get("severity", "medium"),
                            pattern=rule_data.get("pattern", ""),
                            check_logic=rule_data.get("check_logic", ""),
                            recommendation=rule_data.get("recommendation", ""),
                            source_type="auto",
                            is_active=True,
                            created_at=datetime.utcnow()
                        )
                        db.add(rule)
                        new_rules.append(rule)

                db.commit()

                logger.info(f"为标准文档 {standard_id} 生成了 {len(new_rules)} 条规则")

                return {
                    "success": True,
                    "generated_count": len(new_rules),
                    "rules": [
                        {
                            "rule_id": r.rule_id,
                            "name": r.name,
                            "category": r.category,
                            "severity": r.severity
                        }
                        for r in new_rules
                    ]
                }
            except Exception as e:
                db.rollback()
                logger.error(f"保存规则失败: {e}")
                return {"success": False, "error": str(e)}
            finally:
                db.close()

        except Exception as e:
            logger.error(f"规则生成失败: {e}")
            return {"success": False, "error": str(e)}

    async def update_rules_for_standard(self, standard_id: int) -> Dict:
        """
        更新标准文档的规则（检测变化后更新）

        Args:
            standard_id: 标准文档 ID

        Returns:
            更新结果
        """
        # 直接调用生成规则方法（会自动禁用旧规则）
        return await self.generate_rules_for_standard(standard_id)

    # ==================== 规则管理 ====================

    def get_active_rules(self) -> List[Dict]:
        """
        获取所有激活的检查规则

        Returns:
            规则列表
        """
        db = next(get_db())
        try:
            rules = db.query(ComplianceRule).filter(
                ComplianceRule.is_active == True
            ).order_by(ComplianceRule.severity, ComplianceRule.rule_id).all()

            return [
                {
                    "id": r.id,
                    "rule_id": r.rule_id,
                    "name": r.name,
                    "category": r.category,
                    "severity": r.severity,
                    "pattern": r.pattern,
                    "check_logic": r.check_logic,
                    "recommendation": r.recommendation,
                    "source_type": r.source_type,
                    "standard_id": r.standard_id,
                    "is_active": r.is_active
                }
                for r in rules
            ]
        finally:
            db.close()

    def get_rules_by_standard(self, standard_id: int) -> List[Dict]:
        """
        获取指定标准文档的规则（包含所有状态）

        Args:
            standard_id: 标准文档 ID

        Returns:
            规则列表
        """
        db = next(get_db())
        try:
            # 返回所有规则，不过滤 is_active
            rules = db.query(ComplianceRule).filter(
                ComplianceRule.standard_id == standard_id
            ).order_by(ComplianceRule.rule_id).all()

            return [
                {
                    "id": r.id,
                    "rule_id": r.rule_id,
                    "name": r.name,
                    "category": r.category,
                    "severity": r.severity,
                    "pattern": r.pattern,
                    "check_logic": r.check_logic,
                    "recommendation": r.recommendation,
                    "source_type": r.source_type,
                    "is_active": r.is_active
                }
                for r in rules
            ]
        finally:
            db.close()

    def update_rule_status(self, rule_id: int, is_active: bool) -> bool:
        """
        更新规则状态（启用/禁用）

        Args:
            rule_id: 规则 ID（数据库 ID）
            is_active: 是否启用

        Returns:
            是否成功
        """
        db = next(get_db())
        try:
            rule = db.query(ComplianceRule).filter(ComplianceRule.id == rule_id).first()
            if not rule:
                return False

            rule.is_active = is_active
            rule.updated_at = datetime.utcnow()
            db.commit()

            return True
        except Exception as e:
            db.rollback()
            logger.error(f"更新规则状态失败: {e}")
            raise
        finally:
            db.close()

    def get_rule(self, rule_id: int) -> Optional[Dict]:
        """
        获取单个规则详情

        Args:
            rule_id: 规则 ID（数据库 ID）

        Returns:
            规则详情
        """
        db = next(get_db())
        try:
            rule = db.query(ComplianceRule).filter(ComplianceRule.id == rule_id).first()
            if not rule:
                return None

            return {
                "id": rule.id,
                "rule_id": rule.rule_id,
                "name": rule.name,
                "category": rule.category,
                "severity": rule.severity,
                "pattern": rule.pattern,
                "check_logic": rule.check_logic,
                "recommendation": rule.recommendation,
                "source_type": rule.source_type,
                "standard_id": rule.standard_id,
                "is_active": rule.is_active,
                "created_at": rule.created_at.isoformat() if rule.created_at else None,
                "updated_at": rule.updated_at.isoformat() if rule.updated_at else None
            }
        finally:
            db.close()

    def update_rule(self, rule_id: int, update_data: Dict) -> Dict:
        """
        更新规则内容

        Args:
            rule_id: 规则 ID（数据库 ID）
            update_data: 更新数据字典

        Returns:
            更新结果
        """
        db = next(get_db())
        try:
            rule = db.query(ComplianceRule).filter(ComplianceRule.id == rule_id).first()
            if not rule:
                return {"success": False, "error": "规则不存在"}

            # 更新字段
            if "name" in update_data:
                rule.name = update_data["name"]
            if "category" in update_data:
                rule.category = update_data["category"]
            if "severity" in update_data:
                rule.severity = update_data["severity"]
            if "pattern" in update_data:
                rule.pattern = update_data["pattern"]
            if "check_logic" in update_data:
                rule.check_logic = update_data["check_logic"]
            if "recommendation" in update_data:
                rule.recommendation = update_data["recommendation"]
            if "is_active" in update_data:
                rule.is_active = update_data["is_active"]

            rule.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(rule)

            logger.info(f"更新规则: id={rule_id}, fields={list(update_data.keys())}")

            return {
                "success": True,
                "rule": {
                    "id": rule.id,
                    "rule_id": rule.rule_id,
                    "name": rule.name,
                    "category": rule.category,
                    "severity": rule.severity,
                    "pattern": rule.pattern,
                    "check_logic": rule.check_logic,
                    "recommendation": rule.recommendation,
                    "is_active": rule.is_active
                }
            }
        except Exception as e:
            db.rollback()
            logger.error(f"更新规则失败: {e}")
            return {"success": False, "error": str(e)}
        finally:
            db.close()


class RuleGeneratorService:
    """规则生成服务（独立服务，使用 ADK Agent）"""

    def __init__(self):
        self.standard_service = StandardService()

    def generate_from_text(self, content: str) -> List[Dict]:
        """
        从文本内容直接生成规则（不保存到数据库）

        Args:
            content: 标准文档内容

        Returns:
            生成的规则列表
        """
        if not self.standard_service.is_ai_configured():
            return []

        message = f"""请从以下网络设备配置标准文档中提取合规检查规则：

内容：
{content[:5000]}

请分析文档中的配置要求，生成可验证的检查规则。
输出 JSON 数组格式。"""

        try:
            result = asyncio.run(adk_runner.run_agent(
                agent=rule_generator_agent,
                user_id="rule_generator",
                message=message,
                analysis_type="rule_generation",
                target_type="text",
                target_id=0,
                save_audit=False,
                db=None
            ))

            if result.get("success"):
                rules = adk_runner.parse_json_response(result.get("response", ""))
                if isinstance(rules, dict):
                    return [rules]
                return rules or []
            return []
        except Exception as e:
            logger.error(f"规则生成失败: {e}")
            return []