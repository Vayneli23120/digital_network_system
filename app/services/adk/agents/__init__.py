"""ADK Agent 定义"""

from app.services.adk.agents.fault_agent import fault_analysis_agent, root_cause_agent
from app.services.adk.agents.compliance_agent import compliance_agent, rule_generator_agent
from app.services.adk.agents.health_agent import health_agent
from app.services.adk.agents.maintenance_agent import maintenance_agent
from app.services.adk.agents.predictive_agent import predictive_agent

__all__ = [
    'fault_analysis_agent',
    'root_cause_agent',
    'compliance_agent',
    'rule_generator_agent',
    'health_agent',
    'maintenance_agent',
    'predictive_agent',
]
