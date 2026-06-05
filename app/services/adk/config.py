"""ADK 配置管理

从数据库加载 AIConfig，转换为 ADK LiteLlm 模型配置。
"""

import os
from typing import Optional, Dict
from loguru import logger

from app.shared.database import get_db
from app.shared.models import AIConfig


class ADKConfig:
    """从数据库获取 AI 配置，创建 LiteLlm 模型"""

    PROVIDER_MAP = {
        'openai': 'openai',
        'anthropic': 'anthropic',
        'deepseek': 'deepseek',
    }

    def get_active_config(self) -> Optional[AIConfig]:
        """获取当前激活的 AI 配置"""
        db = next(get_db())
        try:
            config = db.query(AIConfig).filter(
                AIConfig.is_active == True,
                AIConfig.is_default == True
            ).first()

            if not config:
                config = db.query(AIConfig).filter(AIConfig.is_active == True).first()

            return config
        finally:
            db.close()

    def get_model_config(self) -> Optional[Dict]:
        """获取 LiteLLM 模型配置字典"""
        config = self.get_active_config()
        if not config:
            logger.warning("未配置 AI 服务")
            return None

        provider = self.PROVIDER_MAP.get(config.provider, config.provider)

        # 对于自定义 base_url，使用 provider 前缀格式
        if config.base_url:
            # 使用 provider/model 格式让 LiteLLM 正确处理
            model_str = f"{provider}/{config.model_name}"
        else:
            # 使用官方 API 时，直接用模型名
            model_str = config.model_name

        result = {
            "model": model_str,
            "temperature": config.temperature or 0.7,
            "max_tokens": config.max_tokens or 4096,
            "timeout": config.timeout or 120,
        }

        # 自定义 base_url
        if config.base_url:
            result["api_base"] = config.base_url

        # API Key 通过环境变量传递给 litellm
        api_key = config.api_key_encrypted or ""
        env_key_map = {
            'openai': 'OPENAI_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY',
            'deepseek': 'DEEPSEEK_API_KEY',
        }
        env_key = env_key_map.get(config.provider, f"{config.provider.upper()}_API_KEY")
        os.environ[env_key] = api_key

        logger.info(f"ADK 配置: provider={config.provider}, model={model_str}, api_base={config.base_url}")

        return result

    def create_litellm_model(self) -> Optional['LiteLlm']:
        """创建 LiteLlm 模型实例"""
        from google.adk.models import LiteLlm

        config_dict = self.get_model_config()
        if not config_dict:
            return None

        return LiteLlm(
            model=config_dict["model"],
            api_base=config_dict.get("api_base"),
            temperature=config_dict["temperature"],
            max_tokens=config_dict["max_tokens"],
            timeout=config_dict.get("timeout", 120),  # 添加超时参数
        )

    def is_configured(self) -> bool:
        """检查 AI 服务是否已配置"""
        return self.get_active_config() is not None


# 单例
adk_config = ADKConfig()