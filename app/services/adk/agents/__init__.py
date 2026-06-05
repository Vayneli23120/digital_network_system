"""ADK Agent 定义

Note: google.adk 是实验性 SDK，可能未安装。
如未安装，Agent 导入将返回 None，相关功能禁用。
"""

try:
    from google.adk.agents import LlmAgent
    GOOGLE_ADK_AVAILABLE = True
except ImportError:
    GOOGLE_ADK_AVAILABLE = False
    LlmAgent = None

# 条件导入 Agent
if GOOGLE_ADK_AVAILABLE:
    from app.services.adk.agents.fault_agent import fault_analysis_agent, root_cause_agent
    from app.services.adk.agents.compliance_agent import compliance_agent, rule_generator_agent
    from app.services.adk.agents.health_agent import health_agent
    from app.services.adk.agents.maintenance_agent import maintenance_agent
    from app.services.adk.agents.predictive_agent import predictive_agent
else:
    # google.adk 未安装时，所有 Agent 为 None
    fault_analysis_agent = None
    root_cause_agent = None
    compliance_agent = None
    rule_generator_agent = None
    health_agent = None
    maintenance_agent = None
    predictive_agent = None

__all__ = [
    'GOOGLE_ADK_AVAILABLE',
    'fault_analysis_agent',
    'root_cause_agent',
    'compliance_agent',
    'rule_generator_agent',
    'health_agent',
    'maintenance_agent',
    'predictive_agent',
]