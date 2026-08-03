"""ADK 配置管理

从数据库加载 AIConfig，转换为 ADK LiteLlm 模型配置。
"""

from typing import TYPE_CHECKING, Optional, Dict
from loguru import logger

from app.shared.database import get_db
from app.shared.models import AIConfig

if TYPE_CHECKING:  # 仅用于类型标注，运行时不导入 google-adk（可选依赖）
    from google.adk.models import LiteLlm


class ADKConfig:
    """从数据库获取 AI 配置，创建 LiteLlm 模型 - 支持所有常见 LLM 提供商"""

    # 所有支持的提供商
    SUPPORTED_PROVIDERS = [
        'openai',           # OpenAI (GPT-4, GPT-3.5 等)
        'anthropic',        # Anthropic (Claude 等) - Kimi 兼容
        'deepseek',         # DeepSeek
        'ollama',           # Ollama 本地模型
        'llmstudio',        # LM Studio 本地模型
        'lmstudio',         # LM Studio 别名
        'groq',             # Groq API
        'azure',            # Azure OpenAI
        'together',         # Together AI
        'replicate',        # Replicate
        'cohere',           # Cohere
        'local',            # 通用本地 OpenAI 兼容端点
    ]
    
    # litellm 模型前缀映射（某些提供商需要前缀）
    PROVIDER_MAP = {
        'openai': 'openai',
        'anthropic': 'anthropic',
        'deepseek': 'deepseek',
        'ollama': 'ollama',
        'llmstudio': 'openai',      # LM Studio 使用 OpenAI 兼容接口
        'lmstudio': 'openai',       # 别名
        'groq': 'groq',
        'azure': 'azure',
        'together': 'together',
        'replicate': 'replicate',
        'cohere': 'cohere',
        'local': 'openai',          # 本地 OpenAI 兼容服务（如 vLLM、text-generation-webui）
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
        """获取 LiteLLM 模型配置字典 - 支持所有提供商的通用逻辑"""
        config = self.get_active_config()
        if not config:
            logger.warning("未配置 AI 服务")
            return None

        provider = config.provider.lower()
        if provider not in self.PROVIDER_MAP:
            logger.warning(f"未知提供商: {provider}，使用 openai 兼容模式")
            provider = 'local'  # 默认使用本地 OpenAI 兼容

        litellm_provider = self.PROVIDER_MAP[provider]

        # 构建模型字符串
        # 对于本地/自定义 base_url，使用 "provider/model" 格式
        # 对于官方 API，直接使用模型名
        if config.base_url:
            # 自定义 API 端点（本地 Ollama、LM Studio 等）
            model_str = f"{litellm_provider}/{config.model_name}"
        else:
            # 官方 API（OpenAI、Anthropic、Groq 等）
            model_str = config.model_name

        result = {
            "model": model_str,
            "provider": provider,
            "temperature": config.temperature or 0.7,
            "max_tokens": config.max_tokens or 4096,
            "timeout": config.timeout or 120,
        }

        # 自定义 base_url 处理
        if config.base_url:
            result["api_base"] = config.base_url

        # 解密 API Key 随配置返回（不再写进程级 os.environ，避免跨请求污染）。
        # 历史明文 key 非 Fernet 密文 → 原样透传（decrypt_or_passthrough）。
        if config.api_key_encrypted:
            from app.shared.crypto import decrypt_or_passthrough
            result["api_key"] = decrypt_or_passthrough(config.api_key_encrypted)

        logger.info(
            f"LLM 配置: provider={provider}, model={model_str}, "
            f"base_url={config.base_url or '官方API'}"
        )

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
            api_key=config_dict.get("api_key"),
            temperature=config_dict["temperature"],
            max_tokens=config_dict["max_tokens"],
            timeout=config_dict.get("timeout", 120),  # 添加超时参数
        )

    def is_configured(self) -> bool:
        """检查 AI 服务是否已配置"""
        return self.get_active_config() is not None


# 单例
adk_config = ADKConfig()