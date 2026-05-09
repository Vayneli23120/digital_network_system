"""AI Provider 抽象基类

定义所有AI服务提供商的统一接口。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class AIResponse:
    """AI响应结构"""
    content: str                          # AI返回的文本内容
    provider: str                         # 提供商名称
    model: str                            # 使用的模型
    usage: Dict[str, int] = field(default_factory=dict)  # token使用量
    cost: float = 0.0                     # 成本（元）
    processing_time_ms: int = 0           # 处理耗时
    confidence: Optional[float] = None    # 置信度（0-1）
    metadata: Dict[str, Any] = field(default_factory=dict)  # 其他元数据
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'content': self.content,
            'provider': self.provider,
            'model': self.model,
            'usage': self.usage,
            'cost': self.cost,
            'processing_time_ms': self.processing_time_ms,
            'confidence': self.confidence,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat()
        }


class AIProvider(ABC):
    """AI服务提供商抽象基类"""

    # 各提供商的定价（元/千tokens）
    PRICING = {
        'deepseek': {
            'deepseek-chat': {'input': 0.001, 'output': 0.002},
            'deepseek-reasoner': {'input': 0.004, 'output': 0.016}
        },
        'claude': {
            'claude-3-haiku': {'input': 0.018, 'output': 0.09},
            'claude-3-sonnet': {'input': 0.225, 'output': 1.125},
            'claude-3-opus': {'input': 1.5, 'output': 7.5}
        },
        'openai': {
            'gpt-4o': {'input': 0.35, 'output': 1.4},
            'gpt-4o-mini': {'input': 0.105, 'output': 0.42}
        }
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = None,
        base_url: Optional[str] = None,
        timeout: int = 60
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self.provider_name = self.__class__.__name__.replace('Provider', '').lower()

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> AIResponse:
        """
        发送聊天请求

        Args:
            messages: 消息列表 [{"role": "user/assistant/system", "content": "..."}]
            temperature: 温度参数（0-1），越低越确定性
            max_tokens: 最大生成token数
            **kwargs: 其他提供商特定参数

        Returns:
            AIResponse 对象
        """
        pass

    @abstractmethod
    async def analyze(
        self,
        prompt: str,
        context: Optional[str] = None,
        **kwargs
    ) -> AIResponse:
        """
        分析请求（简化的单轮对话）

        Args:
            prompt: 分析提示词
            context: 上下文信息
            **kwargs: 其他参数

        Returns:
            AIResponse 对象
        """
        pass

    def calculate_cost(self, usage: Dict[str, int]) -> float:
        """
        计算API调用成本

        Args:
            usage: {'prompt_tokens': x, 'completion_tokens': y}

        Returns:
            成本（元）
        """
        pricing = self.PRICING.get(self.provider_name, {})
        model_pricing = pricing.get(self.model, {'input': 0.01, 'output': 0.02})

        input_tokens = usage.get('prompt_tokens', 0)
        output_tokens = usage.get('completion_tokens', 0)

        cost = (input_tokens * model_pricing['input'] + output_tokens * model_pricing['output']) / 1000
        return round(cost, 4)

    def is_available(self) -> bool:
        """检查Provider是否可用（有API Key）"""
        return self.api_key is not None and len(self.api_key) > 0

    def get_model_info(self) -> Dict:
        """获取当前模型信息"""
        return {
            'provider': self.provider_name,
            'model': self.model,
            'available': self.is_available()
        }