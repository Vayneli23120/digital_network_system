"""ADK Runner 封装

统一执行入口，管理 Session、审计记录、成本计算。
"""

import json
import time
import asyncio
from typing import Dict, Optional, Any
from loguru import logger

try:
    from google.genai import types
    ADK_AVAILABLE = True
except Exception:
    ADK_AVAILABLE = False
    types = None
    logger.warning("google.genai 未安装，ADK 功能不可用。如需 AI 功能请安装 requirements-ai.txt")

from app.services.adk.config import adk_config
from app.services.adk.audit import AIAuditTracker
from app.services.adk.pricing import AIPricing


class ADKRunner:
    """统一的 ADK 执行入口"""

    def __init__(self):
        self.audit = AIAuditTracker()
        self.pricing = AIPricing()

    async def chat(
        self,
        message: str,
        system_prompt: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 120,
    ) -> Dict:
        """
        简单的 AI 聊天模式 - 直接发送消息给 LLM

        Args:
            message: 用户消息（配置文本 + 检查要求）
            system_prompt: 系统提示词（可选）
            temperature: 温度参数
            max_tokens: 最大 token 数
            timeout: 超时时间（秒）

        Returns:
            {"success": True, "response": "AI回复内容"} 或 {"success": False, "error": "错误信息"}
        """
        start_time = time.time()

        try:
            # 获取模型配置
            model_config = adk_config.get_model_config()
            if not model_config:
                return {"success": False, "error": "未配置 AI 服务"}

            # 构建消息
            # 将 system_prompt 合并到 user message 中以确保兼容所有 provider
            messages = []
            if system_prompt:
                messages.append({"role": "user", "content": f"{system_prompt}\n\n{message}"})
            else:
                messages.append({"role": "user", "content": message})

            # 直接调用 LiteLLM（ADK 底层使用的也是 LiteLLM）
            from litellm import acompletion

            response = await acompletion(
                model=model_config["model"],
                api_base=model_config.get("api_base"),
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout
            )

            response_text = response.choices[0].message.content or ""
            processing_time_ms = int((time.time() - start_time) * 1000)

            logger.info(f"AI Chat 成功，耗时 {processing_time_ms}ms，响应长度 {len(response_text)}")

            return {
                "success": True,
                "response": response_text,
                "processing_time_ms": processing_time_ms
            }

        except asyncio.TimeoutError:
            logger.error(f"AI Chat 超时 ({timeout}s)")
            return {"success": False, "error": f"AI 响应超时 ({timeout}秒)"}
        except Exception as e:
            logger.error(f"AI Chat 失败: {e}")
            return {"success": False, "error": str(e)}

    def _create_runner(self, agent):
        """创建 Runner 实例"""
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService

        session_service = InMemorySessionService()
        return Runner(
            agent=agent,
            app_name="nas",
            session_service=session_service,
        ), session_service

    async def run_agent(
        self,
        agent,
        message: str,
        user_id: str = "system",
        save_audit: bool = True,
        analysis_type: str = None,
        target_type: str = None,
        target_id: int = None,
        db = None,
        timeout: int = 120,  # 添加超时参数
    ) -> Dict:
        """执行 Agent 并返回结果"""
        start_time = time.time()

        # 动态注入模型配置
        model = adk_config.create_litellm_model()
        if model:
            agent.model = model
        else:
            return {
                "success": False,
                "error": "未配置 AI 服务，请先在设置中配置 API Key",
                "analysis_type": analysis_type
            }

        runner, session_service = self._create_runner(agent)

        # 创建 Session
        session = await session_service.create_session(
            app_name="nas",
            user_id=user_id
        )

        # 构建用户消息
        user_content = types.Content(
            role='user',
            parts=[types.Part(text=message)]
        )

        # 执行 Agent（流式收集结果）
        final_response = ""
        tool_calls = []

        try:
            # 使用 asyncio.wait_for 添加超时控制
            async def run_with_timeout():
                response_text = ""
                async for event in runner.run_async(
                    session_id=session.id,
                    user_id=user_id,
                    new_message=user_content
                ):
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if part.text:
                                response_text += part.text

                    if event.is_final_response():
                        break
                return response_text

            final_response = await asyncio.wait_for(run_with_timeout(), timeout=timeout)

        except asyncio.TimeoutError:
            logger.error(f"ADK Agent 执行超时 (timeout={timeout}s)")
            return {
                "success": False,
                "error": f"AI 响应超时 ({timeout}秒)，请稍后重试",
                "analysis_type": analysis_type
            }
        except Exception as e:
            logger.error(f"ADK Agent 执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis_type": analysis_type
            }

        processing_time_ms = int((time.time() - start_time) * 1000)

        # 审计记录
        if save_audit and db:
            self.audit.record(
                analysis_type=analysis_type,
                target_type=target_type,
                target_id=target_id,
                result=final_response,
                processing_time_ms=processing_time_ms,
                tool_calls=tool_calls,
                db=db
            )

        return {
            "success": True,
            "response": final_response,
            "processing_time_ms": processing_time_ms,
            "tool_calls": tool_calls,
            "analysis_type": analysis_type
        }

    def parse_json_response(self, response: str) -> Optional[Dict]:
        """解析 Agent 返回的 JSON"""
        try:
            # 移除可能的 Markdown 代码块标记
            content = response.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]

            # 尝试找到 JSON 数组或对象的开始位置
            json_start = content.find('[')
            if json_start == -1:
                json_start = content.find('{')

            if json_start != -1:
                content = content[json_start:]

                # 尾部截取
                json_end = content.rfind(']')
                if json_end == -1:
                    json_end = content.rfind('}')
                if json_end != -1:
                    content = content[:json_end + 1]

            return json.loads(content.strip())
        except json.JSONDecodeError as e:
            logger.warning(f"Agent 返回内容无法解析为 JSON: {e}")
            logger.debug(f"原始内容前500字符: {response[:500]}")
            return None


# 单例
adk_runner = ADKRunner()