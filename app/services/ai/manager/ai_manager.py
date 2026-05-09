"""AI管理器

负责：
- AI Provider实例管理
- AI任务调度与执行
- 结果缓存
- 使用审计记录
"""

import os
import json
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from loguru import logger

from sqlalchemy.orm import Session

from app.shared.database import get_db
from app.shared.models import AIAnalysisRecord
from ..providers.base import AIProvider, AIResponse
from ..providers.deepseek import DeepSeekProvider
from ..prompts.manager import prompt_manager


class AIManager:
    """AI任务管理器"""

    def __init__(
        self,
        default_provider: str = 'deepseek',
        default_model: str = 'deepseek-chat'
    ):
        self.default_provider = default_provider
        self.default_model = default_model
        self.providers: Dict[str, AIProvider] = {}

        # 初始化Provider
        self._init_providers()

    def _init_providers(self):
        """初始化AI Provider实例"""
        # DeepSeek
        deepseek_key = os.environ.get('DEEPSEEK_API_KEY', '')
        if deepseek_key:
            self.providers['deepseek'] = DeepSeekProvider(
                api_key=deepseek_key,
                model=self.default_model
            )
            logger.info("DeepSeek Provider initialized")
        else:
            logger.warning("DeepSeek API Key not configured")

        # Claude (可选)
        claude_key = os.environ.get('ANTHROPIC_API_KEY', '')
        if claude_key:
            from ..providers.claude import ClaudeProvider
            self.providers['claude'] = ClaudeProvider(
                api_key=claude_key,
                model='claude-3-haiku-20240307'
            )
            logger.info("Claude Provider initialized")

    def get_provider(self, provider_name: Optional[str] = None) -> AIProvider:
        """获取AI Provider"""
        name = provider_name or self.default_provider

        if name not in self.providers:
            raise ValueError(f"Provider '{name}' not available")

        provider = self.providers[name]
        if not provider.is_available():
            raise ValueError(f"Provider '{name}' API key not configured")

        return provider

    def list_providers(self) -> List[Dict]:
        """列出所有可用的Provider"""
        result = []
        for name, provider in self.providers.items():
            result.append(provider.get_model_info())
        return result

    async def analyze(
        self,
        analysis_type: str,
        target_type: str,
        target_id: int,
        variables: Dict[str, Any],
        provider_name: Optional[str] = None,
        template_name: Optional[str] = None,
        custom_prompt: Optional[str] = None,
        custom_system: Optional[str] = None,
        db: Optional[Session] = None,
        save_record: bool = True
    ) -> Dict:
        """
        执行AI分析任务

        Args:
            analysis_type: 分析类型 (fault/root_cause/health/pm_recommend/summary)
            target_type: 目标类型 (device/fault/maintenance)
            target_id: 目标ID
            variables: Prompt变量值
            provider_name: 指定Provider（可选）
            template_name: 指定Prompt模板（可选）
            custom_prompt: 自定义用户提示词（可选）
            custom_system: 自定义系统提示词（可选）
            db: 数据库会话
            save_record: 是否保存分析记录

        Returns:
            分析结果字典
        """
        start_time = time.time()
        provider = self.get_provider(provider_name)

        # 构建Prompt
        if custom_prompt:
            system_prompt = custom_system or "你是专业的网络设备运维分析专家。"
            user_prompt = custom_prompt
        elif template_name:
            system_prompt, user_prompt = prompt_manager.build_prompt(
                template_name, variables
            )
        else:
            # 根据分析类型选择默认模板
            default_templates = {
                'fault': 'fault_analysis',
                'health': 'health_score',
                'summary': 'maintenance_summary',
                'pm_recommend': 'predictive_maintenance',
                'root_cause': 'root_cause'
            }
            template_name = default_templates.get(analysis_type, 'fault_analysis')
            system_prompt, user_prompt = prompt_manager.build_prompt(
                template_name, variables
            )

        # 记录输入数据
        input_data = json.dumps({
            'template': template_name,
            'variables': variables,
            'system_prompt': system_prompt[:500]  # 只记录部分
        })

        try:
            # 调用AI
            response = await provider.analyze(
                prompt=user_prompt,
                context=system_prompt,
                temperature=0.3
            )

            # 解析结果
            result = self._parse_response(response, analysis_type)

            # 处理时间
            processing_time_ms = int((time.time() - start_time) * 1000)

            # 保存记录
            if save_record and db:
                record = AIAnalysisRecord(
                    analysis_type=analysis_type,
                    target_type=target_type,
                    target_id=target_id,
                    input_data=input_data,
                    ai_provider=provider.provider_name,
                    model_name=response.model,
                    output_result=json.dumps(result),
                    confidence_score=result.get('confidence'),
                    processing_time_ms=processing_time_ms,
                    tokens_used=response.usage.get('total_tokens', 0),
                    cost=response.cost,
                    status='completed'
                )
                db.add(record)
                db.commit()

            return {
                'success': True,
                'analysis_type': analysis_type,
                'target_type': target_type,
                'target_id': target_id,
                'provider': provider.provider_name,
                'model': response.model,
                'result': result,
                'confidence': result.get('confidence'),
                'processing_time_ms': processing_time_ms,
                'tokens_used': response.usage.get('total_tokens', 0),
                'cost': response.cost
            }

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")

            # 记录失败
            if save_record and db:
                record = AIAnalysisRecord(
                    analysis_type=analysis_type,
                    target_type=target_type,
                    target_id=target_id,
                    input_data=input_data,
                    ai_provider=provider.provider_name,
                    model_name=provider.model,
                    status='failed',
                    error_message=str(e)
                )
                db.add(record)
                db.commit()

            return {
                'success': False,
                'error': str(e),
                'analysis_type': analysis_type
            }

    def _parse_response(self, response: AIResponse, analysis_type: str) -> Dict:
        """
        解析AI响应内容

        Args:
            response: AI响应对象
            analysis_type: 分析类型

        Returns:
            解析后的结果字典
        """
        content = response.content.strip()

        # 尝试解析JSON
        try:
            # 移除可能的Markdown代码块标记
            if content.startswith('```json'):
                content = content[7:]
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]

            result = json.loads(content.strip())

            # 添加置信度（如果有）
            if response.confidence:
                result['confidence'] = response.confidence

            return result

        except json.JSONDecodeError:
            # 如果不是JSON，返回原始文本
            return {
                'raw_text': content,
                'analysis_type': analysis_type,
                'confidence': None
            }

    async def analyze_fault(
        self,
        fault_id: int,
        db: Optional[Session] = None
    ) -> Dict:
        """
        分析故障记录

        Args:
            fault_id: 故障ID
            db: 数据库会话

        Returns:
            分析结果
        """
        from app.shared.models import FaultRecord, Device

        # 获取故障和设备信息
        fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
        if not fault:
            return {'success': False, 'error': 'Fault not found'}

        device = db.query(Device).filter(Device.id == fault.device_id).first()

        variables = {
            'device_name': device.name if device else 'Unknown',
            'device_type': device.device_type if device else 'Unknown',
            'device_ip': device.ip if device else 'Unknown',
            'device_status': device.status if device else 'Unknown',
            'fault_title': fault.title,
            'fault_description': fault.description or '无详细描述',
            'fault_time': fault.created_at.isoformat(),
            'fault_symptoms': fault.description or '无',
            'fault_impact': '待分析'
        }

        return await self.analyze(
            analysis_type='fault',
            target_type='fault',
            target_id=fault_id,
            variables=variables,
            db=db
        )

    async def analyze_device_health(
        self,
        device_id: int,
        db: Optional[Session] = None
    ) -> Dict:
        """
        AI辅助健康评分分析

        Args:
            device_id: 设备ID
            db: 数据库会话

        Returns:
            分析结果
        """
        from app.shared.models import Device, FaultRecord, MaintenanceRecord
        from datetime import datetime, timedelta

        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return {'success': False, 'error': 'Device not found'}

        # 获取故障历史
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        faults = db.query(FaultRecord).filter(
            FaultRecord.device_id == device_id,
            FaultRecord.created_at >= thirty_days_ago
        ).all()

        fault_history = f"共 {len(faults)} 次故障"
        if faults:
            fault_history += "\n- ".join([
                f"{f.created_at.strftime('%Y-%m-%d')}: {f.title} ({f.severity})"
                for f in faults[:5]
            ])

        # 获取维修历史
        ninety_days_ago = datetime.utcnow() - timedelta(days=90)
        repairs = db.query(MaintenanceRecord).filter(
            MaintenanceRecord.device_id == device_id,
            MaintenanceRecord.created_at >= ninety_days_ago
        ).all()

        repair_history = f"共 {len(repairs)} 次维修"
        if repairs:
            repair_history += "\n- ".join([
                f"{r.created_at.strftime('%Y-%m-%d')}: {r.maint_type}"
                for r in repairs[:5]
            ])

        variables = {
            'device_name': device.name,
            'device_model': device.device_type,
            'uptime_days': device.uptime_days or 0,
            'lifecycle_stage': device.lifecycle_stage or 'new',
            'device_status': device.status,
            'fault_history': fault_history,
            'repair_history': repair_history,
            'current_alerts': '无活跃告警'
        }

        return await self.analyze(
            analysis_type='health',
            target_type='device',
            target_id=device_id,
            variables=variables,
            db=db
        )

    async def generate_maintenance_summary(
        self,
        maintenance_id: int,
        db: Optional[Session] = None
    ) -> Dict:
        """
        生成维修总结报告

        Args:
            maintenance_id: 维修ID
            db: 数据库会话

        Returns:
            分析结果
        """
        from app.shared.models import MaintenanceRecord, Device

        maintenance = db.query(MaintenanceRecord).filter(
            MaintenanceRecord.id == maintenance_id
        ).first()
        if not maintenance:
            return {'success': False, 'error': 'Maintenance not found'}

        device = db.query(Device).filter(Device.id == maintenance.device_id).first()

        variables = {
            'maintenance_id': maintenance.id,
            'device_name': device.name if device else 'Unknown',
            'maint_type': maintenance.maint_type,
            'start_time': maintenance.created_at.isoformat(),
            'end_time': maintenance.updated_at.isoformat() if maintenance.updated_at else '进行中',
            'technician': maintenance.technician or '未知',
            'problem_description': maintenance.problem_description or maintenance.title,
            'repair_process': maintenance.solution or '待填写',
            'parts_replaced': '无更换部件'  # TODO: 从备件关系表获取
        }

        return await self.analyze(
            analysis_type='summary',
            target_type='maintenance',
            target_id=maintenance_id,
            variables=variables,
            db=db
        )


# 单例实例
ai_manager = AIManager()