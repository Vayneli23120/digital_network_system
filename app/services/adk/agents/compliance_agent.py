"""配置合规 Agent

审核网络设备配置的合规性，从标准文档生成检查规则。
"""

from google.adk.agents import LlmAgent

from app.services.adk.tools.config_tools import check_config_rule, get_compliance_rules
from app.services.adk.tools.standard_tools import get_standard_document


compliance_agent = LlmAgent(
    name="compliance_agent",
    description="审核网络设备配置的合规性",
    instruction="""你是网络设备配置合规审核专家。

审核流程：
1. 使用 get_compliance_rules 获取当前激活的合规规则
2. 对每条规则使用 check_config_rule 检查配置是否符合
3. 对未通过项进行深度分析
4. 如有标准文档，使用 get_standard_document 获取参考

输出格式（JSON）：
{
  "compliance_score": 0-100,
  "total_checks": 数量,
  "passed": 数量,
  "failed": 数量,
  "results": [
    {
      "check_id": "SEC-001",
      "check_name": "检查项名称",
      "category": "security/availability/compliance",
      "severity": "critical/high/medium/low",
      "passed": true/false,
      "detail": "详细说明",
      "recommendation": "建议"
    }
  ],
  "ai_insights": "AI额外洞察"
}""",
    tools=[check_config_rule, get_compliance_rules, get_standard_document],
)


rule_generator_agent = LlmAgent(
    name="rule_generator_agent",
    description="从标准文档生成合规检查规则",
    instruction="""你是合规规则生成专家。

从配置标准文档中提取检查规则：
1. 使用 get_standard_document 获取标准文档内容
2. 分析文档中的配置要求
3. 为每个要求生成可验证的检查规则

输出格式（JSON 数组）：
[
  {
    "rule_id": "AI-001",
    "name": "规则名称",
    "category": "security/availability/compliance",
    "severity": "critical/high/medium/low",
    "pattern": "正则表达式或关键词",
    "check_logic": "检查逻辑描述",
    "recommendation": "推荐配置"
  }
]""",
    tools=[get_standard_document],
)
