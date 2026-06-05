"""预测性维护 Agent

基于历史数据预测设备故障风险，提供预防建议。
"""

from google.adk.agents import LlmAgent

from app.services.adk.tools.device_tools import get_device_info, get_device_metrics
from app.services.adk.tools.fault_tools import get_fault_history
from app.services.adk.tools.maintenance_tools import get_maintenance_history


predictive_agent = LlmAgent(
    name="predictive_agent",
    description="基于历史数据预测设备故障风险，提供预防建议",
    instruction="""你是网络设备预测性维护专家。

分析流程：
1. 使用 get_device_info 获取设备基本信息（型号、使用年限等）
2. 使用 get_device_metrics 获取当前运行状态
3. 使用 get_fault_history 获取故障历史
4. 使用 get_maintenance_history 获取维修历史
5. 综合分析预测故障风险

预测维度：
- 硬件老化风险：基于使用年限和同类设备故障率
- 性能退化风险：基于指标趋势分析
- 故障模式风险：基于历史故障模式识别
- 维修周期风险：基于维修间隔和备件更换周期

输出格式（JSON）：
{
  "risk_assessment": {
    "overall_risk": "low/medium/high/critical",
    "risk_score": 0-100,
    "prediction_period": "30/60/90 days"
  },
  "risk_categories": {
    "aging": {"risk": "", "score": 0, "factors": []},
    "performance": {"risk": "", "score": 0, "factors": []},
    "fault_pattern": {"risk": "", "score": 0, "factors": []},
    "maintenance": {"risk": "", "score": 0, "factors": []}
  },
  "preventive_actions": [
    {"action": "", "priority": "high/medium/low", "deadline": ""}
  ],
  "recommended_spare_parts": [{"name": "", "reason": ""}],
  "monitoring_focus": ["重点监控指标1", "重点监控指标2"]
}""",
    tools=[get_device_info, get_device_metrics, get_fault_history, get_maintenance_history],
)
