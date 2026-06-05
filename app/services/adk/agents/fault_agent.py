"""故障分析 Agent

分析网络设备故障，给出根因分析和处理建议。
"""

from google.adk.agents import LlmAgent

from app.services.adk.tools.fault_tools import get_fault_detail, get_fault_history
from app.services.adk.tools.device_tools import get_device_info


fault_analysis_agent = LlmAgent(
    name="fault_analysis_agent",
    description="分析网络设备故障，给出根因分析和处理建议",
    instruction="""你是网络设备故障分析专家。

当收到故障分析请求时：
1. 使用 get_fault_detail 工具获取故障详细信息
2. 使用 get_device_info 工具获取关联设备信息  
3. 使用 get_fault_history 工具获取该设备的故障历史
4. 综合以上信息进行根因分析

输出格式（JSON）：
{
  "fault_type": "硬件/软件/配置/网络",
  "root_cause": "根本原因分析",
  "severity": "critical/major/minor",
  "need_repair": true/false,
  "urgency": "high/medium/low",
  "recommendations": ["建议1", "建议2"],
  "confidence": 0.0-1.0
}""",
    tools=[get_fault_detail, get_device_info, get_fault_history],
)


root_cause_agent = LlmAgent(
    name="root_cause_agent",
    description="深入分析故障根因，提供专家级诊断",
    instruction="""你是网络故障根因分析专家。

分析步骤：
1. 使用 get_fault_detail 获取故障详情
2. 使用 get_device_info 获取设备配置和状态
3. 使用 get_fault_history 获取历史故障模式
4. 分析可能的根本原因（硬件、软件、配置、网络、环境等）
5. 提供详细的诊断推理过程

输出格式（JSON）：
{
  "primary_cause": {
    "category": "hardware/software/config/network/environment",
    "description": "主要根因描述",
    "evidence": ["证据1", "证据2"]
  },
  "secondary_causes": [
    {"category": "...", "description": "..."}
  ],
  "diagnosis_process": "诊断推理过程",
  "verification_steps": ["验证步骤1", "验证步骤2"],
  "confidence": 0.0-1.0
}""",
    tools=[get_fault_detail, get_device_info, get_fault_history],
)
