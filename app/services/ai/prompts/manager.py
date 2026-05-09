"""Prompt模板管理器

管理各类AI分析任务的Prompt模板：
- 故障分析
- 健康评分分析
- 维修总结
- 预测性维护
- 根因分析
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json


@dataclass
class PromptTemplate:
    """Prompt模板结构"""
    name: str                              # 模板名称
    description: str                       # 模板描述
    system_prompt: str                     # 系统提示词
    user_prompt_template: str              # 用户提示词模板
    variables: List[str]                   # 需要填充的变量列表
    output_format: str                     # 期望的输出格式描述
    examples: Optional[List[Dict]] = None  # 示例输入输出


class PromptManager:
    """Prompt模板管理器"""

    # ===== 故障分析模板 =====
    FAULT_ANALYSIS = PromptTemplate(
        name="fault_analysis",
        description="分析设备故障并给出处理建议",
        system_prompt="""你是一个专业的网络设备运维专家，负责分析设备故障并给出处理建议。

你的分析应该：
1. 确定故障类型（硬件/软件/配置/网络）
2. 分析可能的根因
3. 评估严重程度和对业务的影响
4. 给出处理建议（是否需要维修、紧急程度）
5. 提供预防措施建议

输出格式要求：
- 使用JSON格式输出
- 包含 fault_type, root_cause, severity, need_repair, urgency, recommendations 字段
""",
        user_prompt_template="""请分析以下设备故障：

## 设备信息
- 设备名称：{device_name}
- 设备类型：{device_type}
- IP地址：{device_ip}
- 设备状态：{device_status}

## 故障信息
- 故障标题：{fault_title}
- 故障描述：{fault_description}
- 发现时间：{fault_time}
- 故障现象：{fault_symptoms}
- 影响范围：{fault_impact}

请给出专业的故障分析结果。
""",
        variables=[
            'device_name', 'device_type', 'device_ip', 'device_status',
            'fault_title', 'fault_description', 'fault_time',
            'fault_symptoms', 'fault_impact'
        ],
        output_format="JSON",
        examples=[
            {
                "input": {
                    "device_name": "SW-Core-01",
                    "fault_title": "端口频繁断开"
                },
                "output": {
                    "fault_type": "hardware",
                    "root_cause": "端口模块老化导致连接不稳定",
                    "severity": "major",
                    "need_repair": True,
                    "urgency": "high"
                }
            }
        ]
    )

    # ===== 健康评分分析模板 =====
    HEALTH_SCORE_ANALYSIS = PromptTemplate(
        name="health_score_analysis",
        description="AI辅助设备健康评分分析",
        system_prompt="""你是一个设备健康状态评估专家，负责综合分析设备健康状况。

你的分析应该基于：
1. 设备基本信息（型号、运行时间、状态）
2. 故障历史记录
3. 维修历史记录
4. 当前运行状态

输出要求：
- 给出健康评分（0-100分）
- 给出风险等级（low/medium/high/critical）
- 分析主要风险因素
- 提供改进建议

输出格式：JSON，包含 health_score, risk_level, risk_factors, recommendations
""",
        user_prompt_template="""请分析以下设备的健康状况：

## 设备基本信息
- 设备名称：{device_name}
- 设备型号：{device_model}
- 运行天数：{uptime_days}
- 生命周期阶段：{lifecycle_stage}
- 当前状态：{device_status}

## 故障历史（近30天）
{fault_history}

## 维修历史（近90天）
{repair_history}

## 当前告警
{current_alerts}

请给出健康评分分析结果。
""",
        variables=[
            'device_name', 'device_model', 'uptime_days', 'lifecycle_stage',
            'device_status', 'fault_history', 'repair_history', 'current_alerts'
        ],
        output_format="JSON"
    )

    # ===== 维修总结模板 =====
    MAINTENANCE_SUMMARY = PromptTemplate(
        name="maintenance_summary",
        description="生成维修工作总结报告",
        system_prompt="""你是维修报告撰写专家，负责将维修过程总结为专业报告。

报告应包含：
1. 维修概述（问题、原因、解决方案）
2. 维修过程关键步骤
3. 更换部件清单
4. 维修效果评估
5. 后续建议

输出格式：专业文本报告，使用Markdown格式
""",
        user_prompt_template="""请为以下维修工作生成总结报告：

## 维修基本信息
- 维修单号：{maintenance_id}
- 设备名称：{device_name}
- 维修类型：{maint_type}
- 开始时间：{start_time}
- 完成时间：{end_time}
- 维修人员：{technician}

## 问题描述
{problem_description}

## 维修过程
{repair_process}

## 更换部件
{parts_replaced}

请生成维修总结报告。
""",
        variables=[
            'maintenance_id', 'device_name', 'maint_type', 'start_time',
            'end_time', 'technician', 'problem_description',
            'repair_process', 'parts_replaced'
        ],
        output_format="Markdown"
    )

    # ===== 预测性维护模板 =====
    PREDICTIVE_MAINTENANCE = PromptTemplate(
        name="predictive_maintenance",
        description="基于历史数据预测设备维护需求",
        system_prompt="""你是预测性维护专家，负责基于设备历史数据预测未来维护需求。

分析维度：
1. 设备老化趋势
2. 故障发生规律
3. 部件更换周期
4. 性能下降趋势

输出建议：
- 预计下次维护时间
- 建议维护类型
- 需要关注的部件
- 预防措施建议

输出格式：JSON
""",
        user_prompt_template="""请分析以下设备的预测性维护需求：

## 设备信息
- 设备名称：{device_name}
- 设备型号：{device_model}
- 运行天数：{uptime_days}
- 健康评分：{health_score}

## 历史故障统计
{fault_statistics}

## 历史维修统计
{repair_statistics}

## 部件更换记录
{parts_replacement_history}

请给出预测性维护建议。
""",
        variables=[
            'device_name', 'device_model', 'uptime_days', 'health_score',
            'fault_statistics', 'repair_statistics', 'parts_replacement_history'
        ],
        output_format="JSON"
    )

    # ===== 根因分析模板 =====
    ROOT_CAUSE_ANALYSIS = PromptTemplate(
        name="root_cause_analysis",
        description="深度分析故障根本原因",
        system_prompt="""你是根因分析专家，使用系统性方法分析故障根本原因。

分析方法：
1. 收集所有相关事件和数据
2. 建立时间线
3. 识别因果关系链
4. 找到最深层根本原因
5. 提供系统性解决方案

输出：
- 直接原因
- 根本原因
- 因果链分析
- 系统性解决方案
- 预防措施

输出格式：结构化文本报告
""",
        user_prompt_template="""请进行根因分析：

## 故障事件
{fault_event}

## 相关事件时间线
{event_timeline}

## 设备和环境信息
{context_info}

## 历史类似问题
{similar_issues}

请给出根因分析结果。
""",
        variables=[
            'fault_event', 'event_timeline', 'context_info', 'similar_issues'
        ],
        output_format="Text"
    )

    # 所有模板集合
    TEMPLATES = {
        'fault_analysis': FAULT_ANALYSIS,
        'health_score': HEALTH_SCORE_ANALYSIS,
        'maintenance_summary': MAINTENANCE_SUMMARY,
        'predictive_maintenance': PREDICTIVE_MAINTENANCE,
        'root_cause': ROOT_CAUSE_ANALYSIS
    }

    def __init__(self):
        self.templates = self.TEMPLATES.copy()

    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """获取指定模板"""
        return self.templates.get(name)

    def list_templates(self) -> List[str]:
        """列出所有可用模板"""
        return list(self.templates.keys())

    def build_prompt(
        self,
        template_name: str,
        variables: Dict[str, Any]
    ) -> tuple[str, str]:
        """
        构建完整的Prompt

        Args:
            template_name: 模板名称
            variables: 变量值字典

        Returns:
            (system_prompt, user_prompt) 元组
        """
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")

        # 检查必需变量
        missing_vars = [v for v in template.variables if v not in variables]
        if missing_vars:
            raise ValueError(f"Missing required variables: {missing_vars}")

        # 填充用户提示词
        user_prompt = template.user_prompt_template
        for key, value in variables.items():
            if value is None:
                value = "无"
            user_prompt = user_prompt.replace(f"{{{key}}}", str(value))

        return template.system_prompt, user_prompt

    def add_template(self, template: PromptTemplate):
        """添加自定义模板"""
        self.templates[template.name] = template

    def get_template_info(self, name: str) -> Dict:
        """获取模板详细信息"""
        template = self.get_template(name)
        if not template:
            return None

        return {
            'name': template.name,
            'description': template.description,
            'variables': template.variables,
            'output_format': template.output_format
        }


# 单例实例
prompt_manager = PromptManager()