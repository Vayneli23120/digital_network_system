"""AI 成本计算

保留自建的 Provider 定价表，ADK 不提供成本计算。
"""

from typing import Dict


class AIPricing:
    """Provider 定价表（元/千tokens）"""

    PRICING = {
        'deepseek': {
            'deepseek-chat': {'input': 0.001, 'output': 0.002},
            'deepseek-reasoner': {'input': 0.004, 'output': 0.016},
        },
        'openai': {
            'gpt-4o': {'input': 0.35, 'output': 1.4},
            'gpt-4o-mini': {'input': 0.105, 'output': 0.42},
            'gpt-4': {'input': 0.42, 'output': 1.26},
        },
        'anthropic': {
            'claude-3-haiku': {'input': 0.018, 'output': 0.09},
            'claude-3-sonnet': {'input': 0.225, 'output': 1.125},
            'claude-3-opus': {'input': 1.5, 'output': 7.5},
            'claude-3.5-sonnet': {'input': 0.225, 'output': 1.125},
        },
    }

    def calculate_cost(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """计算 API 调用成本"""
        pricing = self.PRICING.get(provider, {})
        model_pricing = pricing.get(model, {'input': 0.01, 'output': 0.02})

        cost = (prompt_tokens * model_pricing['input'] + completion_tokens * model_pricing['output']) / 1000
        return round(cost, 4)

    def get_model_pricing(self, provider: str, model: str) -> Dict:
        """获取模型定价信息"""
        pricing = self.PRICING.get(provider, {})
        return pricing.get(model, {'input': 0.01, 'output': 0.02})


# 单例
ai_pricing = AIPricing()