"""DeepSeek AI Provider

DeepSeek API封装，支持 deepseek-chat 和 deepseek-reasoner 模型。
"""

import time
import httpx
from typing import Dict, List, Optional, Any
from loguru import logger

from .base import AIProvider, AIResponse


class DeepSeekProvider(AIProvider):
    """DeepSeek API Provider"""

    DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
    DEFAULT_MODEL = "deepseek-chat"

    SUPPORTED_MODELS = [
        'deepseek-chat',       # 通用对话模型
        'deepseek-reasoner',   # 推理增强模型
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        base_url: Optional[str] = None,
        timeout: int = 60
    ):
        super().__init__(api_key, model, base_url, timeout)
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.provider_name = 'deepseek'

        if model not in self.SUPPORTED_MODELS:
            logger.warning(f"Unknown model {model}, using default {self.DEFAULT_MODEL}")
            self.model = self.DEFAULT_MODEL

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> AIResponse:
        """
        发送聊天请求到DeepSeek API

        Args:
            messages: OpenAI格式消息列表
            temperature: 温度参数
            max_tokens: 最大生成token数
            **kwargs: 支持 top_p, frequency_penalty, presence_penalty 等

        Returns:
            AIResponse 对象
        """
        if not self.is_available():
            raise ValueError("DeepSeek API Key not configured")

        start_time = time.time()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # 添加额外参数
        for key in ['top_p', 'frequency_penalty', 'presence_penalty', 'stream']:
            if key in kwargs:
                payload[key] = kwargs[key]

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )

                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"DeepSeek API error: {response.status_code} - {error_text}")
                    raise Exception(f"DeepSeek API error: {response.status_code}")

                data = response.json()

                # 提取响应内容
                content = data['choices'][0]['message']['content']

                # 提取使用量
                usage = {
                    'prompt_tokens': data.get('usage', {}).get('prompt_tokens', 0),
                    'completion_tokens': data.get('usage', {}).get('completion_tokens', 0),
                    'total_tokens': data.get('usage', {}).get('total_tokens', 0)
                }

                # 计算成本
                cost = self.calculate_cost(usage)

                # 处理时间
                processing_time_ms = int((time.time() - start_time) * 1000)

                # 构建响应
                return AIResponse(
                    content=content,
                    provider='deepseek',
                    model=self.model,
                    usage=usage,
                    cost=cost,
                    processing_time_ms=processing_time_ms,
                    metadata={
                        'id': data.get('id'),
                        'finish_reason': data['choices'][0].get('finish_reason')
                    }
                )

        except httpx.TimeoutException:
            logger.error("DeepSeek API timeout")
            raise Exception("DeepSeek API request timed out")
        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            raise

    async def analyze(
        self,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.3,  # 分析任务用较低温度
        max_tokens: int = 2000,
        **kwargs
    ) -> AIResponse:
        """
        分析请求（简化的单轮对话）

        Args:
            prompt: 分析提示词
            context: 上下文信息（会作为system消息）
            **kwargs: 其他参数

        Returns:
            AIResponse 对象
        """
        messages = []

        # 添加系统上下文
        if context:
            messages.append({
                "role": "system",
                "content": context
            })

        # 添加用户提示
        messages.append({
            "role": "user",
            "content": prompt
        })

        return await self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ):
        """
        流式聊天（返回生成器）

        Args:
            messages: 消息列表
            temperature: 温度
            max_tokens: 最大token数

        Yields:
            str: 逐块返回的内容
        """
        if not self.is_available():
            raise ValueError("DeepSeek API Key not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        raise Exception(f"DeepSeek API error: {response.status_code}")

                    async for line in response.aiter_lines():
                        if line.startswith("data: ") and line != "data: [DONE]":
                            import json
                            data = json.loads(line[6:])
                            if 'choices' in data and len(data['choices']) > 0:
                                delta = data['choices'][0].get('delta', {})
                                content = delta.get('content', '')
                                if content:
                                    yield content

        except Exception as e:
            logger.error(f"DeepSeek stream error: {e}")
            raise

    def get_supported_models(self) -> List[str]:
        """获取支持的模型列表"""
        return self.SUPPORTED_MODELS