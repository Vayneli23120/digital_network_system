"""维修总结 Agent

生成维修报告总结，分析维修效果。
"""

from google.adk.agents import LlmAgent

from app.services.adk.tools.maintenance_tools import (
    get_maintenance_detail,
    get_maintenance_history,
    get_repair_parts
)
from app.services.adk.tools.device_tools import get_device_info


maintenance_agent = LlmAgent(
    name="maintenance_agent",
    description="生成维修报告总结，分析维修效果",
    instruction="""你是网络设备维修分析专家。

分析流程：
1. 使用 get_maintenance_detail 获取维修详情
2. 使用 get_device_info 获取设备信息
3. 使用 get_repair_parts 获取更换备件信息
4. 使用 get_maintenance_history 获取历史维修记录
5. 分析维修效果和设备稳定性

输出格式（JSON）：
{
  "summary": "维修总结",
  "repair_type": "hardware/software/config/preventive",
  "parts_used": [{"name": "", "quantity": 0}],
  "effectiveness": {
    "issue_resolved": true/false,
    "device_stable": true/false,
    "performance_improved": true/false
  },
  "cost_analysis": {
    "parts_cost": 0,
    "labor_hours": 0,
    "total_estimate": 0
  },
  "follow_up": ["后续建议1", "后续建议2"],
  "lessons_learned": "经验教训总结"
}""",
    tools=[get_maintenance_detail, get_device_info, get_repair_parts, get_maintenance_history],
)
